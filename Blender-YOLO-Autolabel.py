import bpy
import bpy_extras
from bpy.types import Operator
from bpy.types import Panel
from bpy.props import StringProperty, BoolProperty, IntProperty
import os

scene = bpy.context.scene
camera = scene.camera

def calculate_bounding_box(obj: bpy.types.Object, camera: bpy.types.Camera) -> tuple[float, float, float, float]:
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
    if width < 0.005 or height < 0.005:
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

def render(image_set: str, collection: bpy.types.Collection):
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
        image_path = os.path.join(output_dir, "images", f"gen_{image_set}_{i:04d}")
        
        if not overwrite and os.path.exists(image_path):
            continue
        
        scene.render.filepath = image_path
        bpy.ops.render.render(write_still=True)
        
        # Save bounding box data
        with open(os.path.join(output_dir, "labels", f"gen_{image_set}_{i:04d}.txt"), 'w') as f:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and collection in obj.users_collection:
                    bbox = calculate_bounding_box(obj, camera)
                    if bbox is None:
                        continue
                    # TODO: Handle objects without class_id
                    class_id = obj['class_id']  # Assuming class_id is stored in object properties
                    f.write(f"{class_id} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
                    
    scene.render.filepath = output_dir
                    
## classes

class RunAutolabel(Operator):
    """Run YOLO Autolabel"""
    bl_label = "Run YOLO Autolabel"
    bl_idname = "object.blender_yolo_autolabel"

    # poll musi zwrócić True, aby wykonało się execute
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        image_set = context.scene.yolo_image_set
        collection = context.scene.my_collection
        if collection is None:
            self.report({'WARNING'}, "No collection selected.")
            return {'FINISHED'}
        
        render(image_set, collection)
        return {'FINISHED'}

class AssignClasses(Operator):
    """Assign class_id to selected objects"""
    bl_label = "Assign Classes"
    bl_idname = "object.assign_classes"
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj['class_id'] = context.scene.yolo_class_id
        return {'FINISHED'}

class AutolabelSidebar(Panel):
    bl_label = "Blender YOLO Autolabel"
    bl_idname = "OBJECT_PT_blender_yolo_autolabel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "YOLO Autolabel"

    def draw(self, context):
        layout = self.layout
        
        # Create a box for better organization
        #box = layout.box()
        #box.label(text="YOLO Auto-labeling Settings:", icon="SETTINGS")
        
        # Draw the properties in the UI
        #box.prop(scene, "yolo_image_set")
        
        # Add the operator button
        col = layout.column(align=True)
        col.operator(RunAutolabel.bl_idname, text="Run YOLO Autolabel", icon="IMPORT")
        col.label(text="Make sure to set camera and render settings correctly.")
        col.prop(context.scene, "yolo_image_set")
        col.prop(context.scene, "yolo_class_id", text="Class ID")
        col.prop(context.scene, "my_collection", text="Collection for Parts")
        col.operator(AssignClasses.bl_idname, text="Assign Classes to Selected Objects", icon="GROUP_UVS")
        col.operator(SimpleConfirmOperator.bl_idname, text="Confirm Action", icon="CHECKMARK")
        
class SimpleConfirmOperator(bpy.types.Operator):
    """Really?"""
    bl_idname = "my_category.custom_confirm_dialog"
    bl_label = "Do you really want to do that?"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        self.report({'INFO'}, "YES!")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
        
classes = [
    RunAutolabel,
    AssignClasses,
    AutolabelSidebar,
    SimpleConfirmOperator
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.yolo_image_set = StringProperty(
        name="Image Set",
        description="Prefix for generated files (e.g., 'A', 'B', 'train')",
        default="B",
        maxlen=10
    )
    
    bpy.types.Scene.yolo_class_id = IntProperty(
        name="Class ID",
        description="Class ID for the selected objects",
        default=0,
        soft_min=0
    )
    
    bpy.types.Scene.my_collection = bpy.props.PointerProperty(type=bpy.types.Collection)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    # Unregister scene properties
    del bpy.types.Scene.yolo_image_set
    del bpy.types.Scene.yolo_class_id
    del bpy.types.Scene.my_collection

if __name__ == "__main__":
    register()
