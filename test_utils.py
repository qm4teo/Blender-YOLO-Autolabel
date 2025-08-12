import re
import cv2
import matplotlib.pyplot as plt

class BoundingBox:
    def __init__(self, class_id: int, x: float, y: float, w: float, h: float):
        """
        Creates a BoundingBox object from **YOLO** format. Values are relative and normalized to 0-1.
        Origin in top-left corner at (0,0). 
        
        :param class_id: class id of the bounding box
        :param x: x coordinate of the center of the bounding box
        :param y: y coordinate of the center of the bounding box
        :param w: width of the bounding box
        :param h: height of the bounding box
        """
        self.class_id = class_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
    def __str__(self):
        return f"class_id: {self.class_id} x: {self.x} y: {self.y} w: {self.w} h: {self.h}"
    
    def __repr__(self):
        return f"class_id: {self.class_id} x: {self.x} y: {self.y} w: {self.w} h: {self.h}"
    
    def get_coordinates(self, resolution: tuple[int, int] = (1920, 1080)) -> tuple[int, int, int, int]:
        """
        Returns the coordinates of the bounding box for given resolution.
        
        :param resolution: resolution of the image (width, height)
        :return (x1, y1, x2, y2): coordinates of the bounding box in pixels
        """
        x1 = self.x - self.w / 2
        y1 = self.y - self.h / 2
        x2 = self.x + self.w / 2
        y2 = self.y + self.h / 2
        return (int(x1*resolution[0]), int(y1*resolution[1]), int(x2*resolution[0]), int(y2*resolution[1]))
    
    def get_class_color(self) -> tuple[int, int, int]:
        """
        Returns the color of the bounding box based on the class_id.
        
        :return (r, g, b): color of the bounding box
        """
        if self.class_id == 0:
            return (98, 131, 149)
        elif self.class_id == 1:
            return (77, 139, 49)
        elif self.class_id == 2:
            return (255, 200, 0)
        elif self.class_id == 3:
            return (255, 132, 39)
        else:
            return (128, 128, 128)

def load_file(path: str) -> list[str]:
    file = open(path, "r")
    lines = [line.rstrip('\n') for line in file]
    file.close()
    
    return lines

def separate_line(line: str) -> list:
    return re.split(f' ', line)

def parse_lines(lines: list) -> list[BoundingBox]:
    bounding_boxes = []
    for line in lines:
        values = separate_line(line)
        bounding_box = BoundingBox(float(values[0]), float(values[1]), float(values[2]), float(values[3]), float(values[4]))
        bounding_boxes.append(bounding_box)
    
    return bounding_boxes

def parse_file(path: str) -> list[BoundingBox]:
    """
    Loads a file and parses it into a list of BoundingBoxes.
    
    :param path: path to the file
    :return: list of BoundingBoxes
    """
    return parse_lines(load_file(path))
    
def draw_bounding_boxes(image, bounding_boxes: list[BoundingBox], color: tuple[int, int, int] = None, thickness: int = 2) -> None:
    """
    Draws all bounding boxes on the image.
    
    :param image: image to draw the bounding boxes on
    :param bounding_boxes: bounding boxes to draw
    :param color: color of the bounding box
    :param thickness: thickness of the bounding box

    """
    auto_color = True if color is None else False
    
    for bounding_box in bounding_boxes:
        if auto_color:
            color = bounding_box.get_class_color()
        x1, y1, x2, y2 = bounding_box.get_coordinates(image.shape[-2::-1])
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    plt.imshow(image)
    plt.axis('off')
    plt.show()