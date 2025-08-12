import bpy
import bpy_extras
from bpy.types import Operator
from bpy.types import Panel
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, PointerProperty
import os

scene = bpy.context.scene
camera = scene.camera

def calculate_bounding_box(obj: bpy.types.Object, camera: bpy.types.Camera, threshold: float) -> tuple[float, float, float, float]:
    """
    Calculates the 2D bounding box of the object in the image.
    
    @param obj: object to calculate the bounding box for
    @param camera: camera object
    @return: (x_center, y_center, width, height) of the bounding box in normalized coordinates
    """
    
    # Uwzględnienie przesunięcia - przekształcenie przez macierz zawierającą przesunięcie, skalowanie i obrót...
    # ...wierzchołków ze współrzędnych lokalnych do współrzędnych świata
    vertices_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
  
    # Przekształcenie do przestrzeni 2D (kamery)
    coords_2d = [bpy_extras.object_utils.world_to_camera_view(scene, camera, v) for v in vertices_world]
    
    # Znalezienie minimalnych i maksymalnych współrzędnych 2D obiektu
    # x,y to współrzędne 2D w przestrzeni kamery, a z to głebia
    # y = 1 - y, bo normalized device coordinates (NDC) przestrzeni 2D Blendera mają (0, 0) w lewym dolnym rogu (a nie w lewym górnym tak jak standardowo)
    min_x = min([v.x for v in coords_2d])
    max_x = max([v.x for v in coords_2d])
    min_y = min([1 - v.y for v in coords_2d])
    max_y = max([1 - v.y for v in coords_2d])
    
    # Sprawdzenie czy chociaż część obiektu jest w zakresie kamery
    if not is_coord_in_camera_view([min_x,max_x,min_y,max_y]):
        return None
    
    # Przycięcie współrzędnych do zakresu [0, 1] (przypadek gdy obiekt częściowo wystaje poza kamerę)
    min_x, max_x, min_y, max_y = handle_outside(min_x,max_x,min_y,max_y)
    
    # Wyznaczenie współrzędnych środka i rozmiaru bounding boxa
    # Są znormalizowane do zakresu [0, 1]
    x_center = (min_x + max_x) / 2
    y_center = (min_y + max_y) / 2
    width = max_x - min_x
    height = max_y - min_y
    
    # Sprawdzenie, czy bounding box jest wystarczająco duży
    if width < threshold or height < threshold:
        return None
    
    return x_center, y_center, width, height

def is_coord_in_camera_view(coords: list) -> bool:
    return any(0 <= elem <= 1 for elem in coords)

def handle_outside(min_x: float, max_x: float, min_y: float, max_y: float) -> tuple[float, float, float, float]:
    if min_x < 0:
        min_x = 0
    if max_x > 1:
        max_x = 1
    if min_y < 0:
        min_y = 0
    if max_y > 1:
        max_y = 1
    return min_x, max_x, min_y, max_y

def render(image_set: str, collection: bpy.types.Collection, threshold: float):
    # Render images and save bounding boxes
    #image_set = "B"
    overwrite = scene.render.use_overwrite
    
    #output_dir = "/Users/mateu/Desktop/Blender-YOLO-Autolabel/{}".format(image_set)
    output_dir = scene.render.filepath
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels"), exist_ok=True)

    for i in range(scene.frame_start, scene.frame_end + 1):
        bpy.context.scene.frame_set(i)

        # Render image   
        image_path = os.path.join(output_dir, "images", f"{image_set}_{i:04d}" if image_set else f"{i:04d}")

        if not overwrite and os.path.exists(image_path):
            continue
        
        scene.render.filepath = image_path
        bpy.ops.render.render(write_still=True)
        
        # Save bounding box data
        with open(os.path.join(output_dir, "labels", f"{image_set}_{i:04d}.txt" if image_set else f"{i:04d}.txt"), 'w') as f:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and collection in obj.users_collection:
                    
                    if 'class_id' not in obj:
                        continue
                    
                    class_id = obj['class_id']
                    
                    bbox = calculate_bounding_box(obj, camera, threshold)
                    if bbox is None:
                        continue
                    
                    f.write(f"{class_id} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
                    
    scene.render.filepath = output_dir
                    
## classes

class YOLOAUTOLABEL_OT_run_render(Operator):
    """Run YOLO Autolabel"""
    bl_label = "Run YOLO Autolabel"
    bl_idname = "object.yolo_autolabel_run_render"

    # poll musi zwrócić True, aby wykonało się execute
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event, title="Are you sure?", message="Running Autolabel will make Blender unresponsive until render is completed.\n You can view progress in the system console.", icon='QUESTION')

    def execute(self, context):
        image_set = context.scene.yolo_autolabel_image_set
        collection = context.scene.yolo_autolabel_collection
        threshold = context.scene.yolo_autolabel_threshold
        if collection is None:
            self.report({'WARNING'}, "No collection selected.")
            return {'CANCELLED'}
        
        render(image_set, collection, threshold)
        return {'FINISHED'}

class YOLOAUTOLABEL_OT_assign_class_id(Operator):
    """Assign Class ID to selected objects"""
    bl_label = "Assign Classes"
    bl_idname = "object.yolo_autolabel_assign_class_id"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj['class_id'] = context.scene.yolo_autolabel_class_id
        return {'FINISHED'}

class YOLOAUTOLABEL_PT_main_panel(Panel):
    bl_label = "Blender YOLO Autolabel"
    bl_idname = "YOLOAUTOLABEL_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "YOLO Autolabel"

    def draw(self, context):
        layout = self.layout
        
        # Create a box for better organization
        box = layout.box()
        box.label(text="Object Settings", icon="MOD_WIREFRAME")
        
        # Draw the properties in the UI
        #box.prop(scene, "yolo_autolabel_image_set")
        box.prop(context.scene, "yolo_autolabel_class_id", text="Class ID")
        box.operator(YOLOAUTOLABEL_OT_assign_class_id.bl_idname, text="Assign Class ID to Selected Objects", icon="GROUP_UVS")
        
        box2 = layout.box()
        box2.label(text="Output Settings", icon="SETTINGS")
        
        box2.prop(context.scene, "yolo_autolabel_collection", text="Target Collection:")
        box2.prop(context.scene, "yolo_autolabel_image_set")
        box2.prop(context.scene, "yolo_autolabel_threshold", text="Threshold", slider=True)
        box2.label(text="Note: Make sure to set camera and render settings correctly.")
        box2.operator(YOLOAUTOLABEL_OT_run_render.bl_idname, text="Run YOLO Autolabel", icon="IMPORT")
        
classes = [
    YOLOAUTOLABEL_OT_run_render,
    YOLOAUTOLABEL_OT_assign_class_id,
    YOLOAUTOLABEL_PT_main_panel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.yolo_autolabel_image_set = StringProperty(
        name="Image Set",
        description="Prefix name for generated files (e.g., 'A', 'B', 'train')",
        default="A",
        maxlen=10
    )
    
    bpy.types.Scene.yolo_autolabel_class_id = IntProperty(
        name="Class ID",
        description="Class ID for the selected objects",
        default=0,
        soft_min=0
    )
    
    bpy.types.Scene.yolo_autolabel_threshold = FloatProperty(
        name="Threshold",
        description="Minimum width or height of object to be considered",
        default=0.01,
        min=0.0,
        max=0.1
    )

    bpy.types.Scene.yolo_autolabel_collection = PointerProperty( # Pointer bo wskazuje na istniejącą już kolekcję
        name="Target Collection",
        description="Only objects in this collection will be labeled",
        type=bpy.types.Collection
    )
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    # Unregister scene properties
    del bpy.types.Scene.yolo_autolabel_image_set
    del bpy.types.Scene.yolo_autolabel_class_id
    del bpy.types.Scene.yolo_autolabel_threshold
    del bpy.types.Scene.yolo_autolabel_collection

if __name__ == "__main__":
    register()
