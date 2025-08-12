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
from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import StringProperty, IntProperty, FloatProperty, PointerProperty
from .utils import render


# ---------------------------------------------------------------------------- #
#                                  Properties                                  #
# ---------------------------------------------------------------------------- #
# (Global variables necessary for UI panel interaction)

class YOLOAUTOLABEL_Properties(PropertyGroup):
    image_set: StringProperty(
        name="Image Set",
        description="Prefix name for generated files (e.g., 'A', 'B', 'train')",
        default="A",
        maxlen=10
    )
    
    class_id: IntProperty(
        name="Class ID",
        description="Class ID for the selected objects",
        default=0,
        soft_min=0
    )
    
    threshold: FloatProperty(
        name="Threshold",
        description="Minimum width or height of object to be considered",
        default=0.01,
        min=0.0,
        max=0.1
    )

    collection: PointerProperty(
        name="Target Collection",
        description="Only objects in this collection will be labeled",
        type=bpy.types.Collection
    )


# ---------------------------------------------------------------------------- #
#                                   Operators                                  #
# ---------------------------------------------------------------------------- #
# (Clickable buttons from UI)

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
                obj['class_id'] = context.scene.yolo_autolabel.class_id
                
        self.report({'INFO'}, f"Assigned class_id={context.scene.yolo_autolabel.class_id} to {len(context.selected_objects)} selected objects.")
        return {'FINISHED'}
    
class YOLOAUTOLABEL_OT_run_render(Operator):
    """Run YOLO Autolabel"""
    bl_label = "Run YOLO Autolabel"
    bl_idname = "object.yolo_autolabel_run_render"

    # poll musi zwrócić True, aby wykonało się execute
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event, title="Are you sure?", 
                                                     message="""Running Autolabel will make Blender unresponsive until render is completed.\n 
                                                     You can view progress in the system console.""", 
                                                     icon='QUESTION')

    def execute(self, context):
        props = context.scene.yolo_autolabel
        image_set = props.image_set
        collection = props.collection
        threshold = props.threshold
        scene = context.scene
        
        if collection is None:
            self.report({'WARNING'}, "No collection selected.")
            return {'CANCELLED'}

        render(image_set, collection, scene, scene.camera, threshold)
        self.report({'INFO'}, f"Finished rendering of {context.scene.frame_end - context.scene.frame_start + 1} frames with labels.")
        return {'FINISHED'}


# ---------------------------------------------------------------------------- #
#                                    Panels                                    #
# ---------------------------------------------------------------------------- #

class YOLOAUTOLABEL_PT_main_panel(Panel):
    bl_label = "Blender YOLO Autolabel"
    bl_idname = "YOLOAUTOLABEL_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "YOLO Autolabel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.yolo_autolabel  # Get property group
        
        # Create a box for better organization
        box = layout.box()
        box.label(text="Object Settings", icon="MOD_WIREFRAME")
        box.prop(props, "class_id", text="Class ID")
        box.operator(YOLOAUTOLABEL_OT_assign_class_id.bl_idname, text="Assign Class ID to Selected Objects", icon="GROUP_UVS")
        
        box2 = layout.box()
        box2.label(text="Output Settings", icon="SETTINGS")
        box2.prop(props, "collection", text="Target Collection:")
        box2.prop(props, "image_set")
        box2.prop(props, "threshold", text="Threshold", slider=True)
        box2.operator(YOLOAUTOLABEL_OT_run_render.bl_idname, text="Run YOLO Autolabel", icon="RENDER_STILL")

        
# ---------------------------------------------------------------------------- #
#                                 Registration                                 #
# ---------------------------------------------------------------------------- #

classes = [
    YOLOAUTOLABEL_Properties,
    YOLOAUTOLABEL_OT_run_render,
    YOLOAUTOLABEL_OT_assign_class_id,
    YOLOAUTOLABEL_PT_main_panel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.yolo_autolabel = PointerProperty(type=YOLOAUTOLABEL_Properties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.yolo_autolabel