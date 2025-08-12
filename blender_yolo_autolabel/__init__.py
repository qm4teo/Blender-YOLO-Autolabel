 #TODO: License

bl_info = {
    "name": "Blender YOLO Autolabel",
    "author": "Mateusz Kuc",
    "description": "Automatically generates YOLO-compatible labels for objects in Blender.",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > YOLO Autolabel",
    "url": "https://github.com/qm4teo/Blender-YOLO-Autolabel",
    "wiki_url": "https://github.com/qm4teo/Blender-YOLO-Autolabel",
    "tracker_url": "https://github.com/qm4teo/Blender-YOLO-Autolabel/issues",
    "category": "Objects"
}

from . import addon

def register():
    addon.register()
    
def unregister():
    addon.unregister()
    
if __name__ == "__main__":
    register()