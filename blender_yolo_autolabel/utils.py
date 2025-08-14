# Blender YOLO Autolabel
# Copyright (C) 2025 - Mateusz Kuc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import bpy_extras
import os

def calculate_bounding_box(obj: bpy.types.Object, scene: bpy.types.Scene, camera: bpy.types.Camera, threshold: float) -> tuple[float, float, float, float]:
    """
    Calculates the 2D bounding box of the object in the image.
    
    @param obj: object to calculate the bounding box for
    @param scene: scene object
    @param camera: camera object
    @param threshold: minimum size of the bounding box
    @return: (x_center, y_center, width, height) of the bounding box in normalized coordinates
    """
    
    # Transform vertices from local to global coordinates with obj.matrix_world (location, scale, rotation)
    vertices_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
  
    # Transform to 2D space (camera)
    coords_2d = [bpy_extras.object_utils.world_to_camera_view(scene, camera, v) for v in vertices_world]
    
    # Find min/max 2D coordinates
    # x,y is 2D coordinates in camera space, z is depth
    # y = 1 - y, because normalized device coordinates (NDC) in Blender's 2D space have (0, 0) at the bottom left corner (not the top left like standard)
    min_x = min([v.x for v in coords_2d])
    max_x = max([v.x for v in coords_2d])
    min_y = min([1 - v.y for v in coords_2d])
    max_y = max([1 - v.y for v in coords_2d])

    # Check if any part of the object is within the camera view
    if not is_coord_in_camera_view([min_x,max_x,min_y,max_y]):
        return None

    # Clip coordinates to the range [0, 1] (case when the object partially extends beyond the camera view)
    min_x, max_x, min_y, max_y = handle_outside(min_x,max_x,min_y,max_y)

    # Calculate the center and size of the bounding box
    # These are normalized to the range [0, 1]
    x_center = (min_x + max_x) / 2
    y_center = (min_y + max_y) / 2
    width = max_x - min_x
    height = max_y - min_y

    # Check if the bounding box is large enough
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

def render(image_set: str, collection: bpy.types.Collection, scene: bpy.types.Scene, camera: bpy.types.Camera, threshold: float) -> None:
    """
    Render images and save bounding boxes.
    
    @param image_set: Prefix for output image and label files
    @param collection: Collection of objects to render
    @param scene: Scene to render
    @param camera: Camera to use for rendering
    @param threshold: Minimum size of bounding box to consider
    """
    overwrite = scene.render.use_overwrite

    # Create output directories
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
                    
                    bbox = calculate_bounding_box(obj, scene, camera, threshold)
                    if bbox is None:
                        continue
                    
                    f.write(f"{class_id} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
    
    # After finished rendering set output path to original (so it stays the same)                
    scene.render.filepath = output_dir