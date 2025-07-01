import imagehash

import numpy as np 

from PIL import Image 

from skimage.metrics import structural_similarity

def calculate_image_proportions(file_name: str) -> tuple[int, int]:
    image_file   = Image.open(file_name)
    image_width  = image_file.width // 2
    image_height = image_file.height // 2

    return image_width, image_height

def preprocess_image(file_name: str, image_width: int, image_height: int, flip_yn: bool = False) -> Image:
    image_file = Image.open(file_name).convert("L")
    image_file = image_file.resize((image_width, image_height))
    image_file = image_file.transpose(Image.FLIP_LEFT_RIGHT) if (flip_yn) else image_file

    return image_file

def calculate_image_hash_similarity(base_image: Image, compared_image: Image) -> float:
    base_hash        = imagehash.phash(base_image)
    compared_hash    = imagehash.phash(compared_image)
    image_similarity = 1 - (base_hash - compared_hash) / base_hash.hash.size

    return image_similarity

def calculate_multi_results(base_image_object: Image, compared_image_object: Image, flipped_image_object: Image, algorithm_types: list[str]):
    output_results = []
    
    for algorithm_type in algorithm_types:
        match (algorithm_type):
            case "ssim":
                base_score    = structural_similarity(np.array(base_image_object), np.array(compared_image_object))
                flip_score    = structural_similarity(np.array(base_image_object), np.array(flipped_image_object))
                average_score = np.mean([base_score, flip_score])
                output_results.extend([base_score, flip_score, average_score])
            case "hash":
                base_score    = calculate_image_hash_similarity(base_image_object, compared_image_object)
                flip_score    = calculate_image_hash_similarity(base_image_object, flipped_image_object)
                average_score = np.mean([base_score, flip_score])
                output_results.extend([base_score, flip_score, average_score])
            case _: 
                output_results.extend([None, None, None])

    return output_results
