import bpy
import bpy_extras
import os
import random

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

# Render images and save bounding boxes
image_set = "B"
output_dir = "/Users/mateu/Desktop/Generated/{}".format(image_set)
os.makedirs(output_dir, exist_ok=True)

collection = bpy.data.collections["PartsTrain2"] #~!!!!!!!!!!!!!!!!!!!
    
for i in range(100):
    # Adjust object positions, lighting, etc.
    # ...
    bpy.context.scene.frame_set(i)
    for obj in bpy.data.objects:
            if obj.type == 'MESH' and collection in obj.users_collection:
                obj.rotation_euler.x = random.randrange(0,10)
                obj.rotation_euler.y = random.randrange(0,10)
                obj.rotation_euler.z = random.randrange(0,10)

    # Render image
    image_path = os.path.join(output_dir, f"gen_{image_set}_{i:04d}.jpg")
    scene.render.filepath = image_path
    bpy.ops.render.render(write_still=True)
    
    # Save bounding box data
    with open(os.path.join(output_dir, f"gen_{image_set}_{i:04d}.txt"), 'w') as f:
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and collection in obj.users_collection:
                bbox = calculate_bounding_box(obj, camera, scene.render.resolution_x)
                if bbox is None:
                    continue
                class_id = obj['class_id']  # Assuming class_id is stored in object properties
                f.write(f"{class_id} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")