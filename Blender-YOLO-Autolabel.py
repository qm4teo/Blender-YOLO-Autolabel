import bpy
import bpy_extras
import os
import random

# Set up the scene, objects, and camera
scene = bpy.context.scene
camera = scene.camera

# Function to calculate 2D bounding box in image coordinates
def calculate_bounding_box(obj, camera, render_size):
    #Trzeba uwzględniać przesunięcie!
    
    # Get object's vertices in camera view
    #mat_world = obj.matrix_world
    #vertices = [camera.matrix_world.inverted() @ mat_world @ v.co for v in obj.data.vertices]
    vertices_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    #print([v for v in vertices_world])
    #print(vertices)
    # Project to 2D
    coords_2d = [bpy_extras.object_utils.world_to_camera_view(scene, camera, v) for v in vertices_world]
    #coords_2d = [bpy_extras.object_utils.world_to_camera_view(scene, camera, v.co) for v in obj.data.vertices]
    #print(coords_2d)
    render_size = (scene.render.resolution_x, scene.render.resolution_y)
    coords_pixel = [(int(v.x * render_size[0]), int((1.0 - v.y) * render_size[1])) for v in coords_2d]
    #print(coords_pixel)
    
    # Find min/max 2D coordinates
    min_x = min([v.x for v in coords_2d])
    max_x = max([v.x for v in coords_2d])
    min_y = min([1 - v.y for v in coords_2d])
    max_y = max([1 - v.y for v in coords_2d])
    
    print("min_x for {}: {}".format(obj.name,min_x))
    print("max_x for {}: {}".format(obj.name,max_x))
    print("min_y for {}: {}".format(obj.name,min_y))
    print("max_y for {}: {}".format(obj.name,max_y))
    

    if not is_any_elements_in_range([min_x,max_x,min_y,max_y]):
        return None
    
    min_x, max_x, min_y, max_y = __handle_outside(min_x,max_x,min_y,max_y)
    # Calculate bbox center, width, height in normalized coordinates
    x_center = (min_x + max_x) / 2
    y_center = (min_y + max_y) / 2
    width = max_x - min_x
    height = max_y - min_y
    
    # warunki brzegowe
    if width < 0.005 or height < 0.005:
        return None
    
    #if x_center > 1 or x_center < 0:
    #    __handle_outside(min_x, max_x, min_y, max_y)
    #elif y_center > 1 or y_center < 0:
    #    __handle_outside(min_x, max_x, min_y, max_y)
    
    return x_center, y_center, width, height

def is_any_elements_in_range(lst):
    return any(0 <= elem <= 1 for elem in lst)

def __handle_outside(min_x, max_x, min_y, max_y):
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