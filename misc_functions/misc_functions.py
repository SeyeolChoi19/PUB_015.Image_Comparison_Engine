import numpy as np 

from PIL import Image 

def calculate_image_proportions(file_name: str) -> tuple[int, int]:
    image_file   = Image.open(file_name)
    image_width  = image_file.width // 2
    image_height = image_file.height // 2

    return image_width, image_height

def convert_image_to_array(file_name: str, image_width: int, image_height: int, flip_yn: bool = False) -> np.array: 
    image_file = Image.open(file_name).convert("L")
    image_file = image_file.resize((image_width, image_height))
    image_file = image_file.transpose(Image.FLIP_LEFT_RIGHT) if (flip_yn) else image_file
    image_file = np.array(image_file)

    return image_file
