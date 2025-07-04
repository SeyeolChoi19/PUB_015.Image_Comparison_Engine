import imagehash, openai, base64, json, os

import numpy as np 

from PIL import Image 

from skimage.metrics import structural_similarity

def lock_file_ops(operation_flag: str = "running"):
    if (operation_flag == "running"):
        with open("./config/job.lock", "w") as f:
            f.write("running")
    else:
        if (os.path.exists("./config/job.lock")):
            os.remove("./config/job.lock")

def json_processor(file_name: str, operation_type: str = "r", config_dict: dict = None):
    with open(file_name, operation_type, encoding = "utf-8") as f:
        if (operation_type.lower() == "r"):
             return json.load(f)
        elif (operation_type.lower() == "w"):
            json.dump(config_dict, f, indent = 4)            

def text_file_processor(file_name: str, operation_type: str = "r", output_string: str = None):
    with open(file_name, operation_type, encoding = "utf-8") as f:
        if (operation_type.lower() == "r"):
            return f.read()
        elif (operation_type.lower() == "w"):
            f.write(output_string)            

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

def encode_image(image_path: str) -> str: 
    with open(image_path, "rb") as f:
        image_file = base64.b64encode(f.read()).decode("utf-8")

    return image_file

def analyze_images(model_type: str, system_prompt: str, user_prompt: str, base_image: str, comparison_image: str, api_client: openai.OpenAI, depth_number: int = 0) -> list:
    try:
        base_image_64   = encode_image(base_image)
        comparison_64   = encode_image(comparison_image)
        response_object = api_client.responses.create(model = model_type, input = [{"role" : "system", "content" : system_prompt}, {"role" : "user", "content" : [{"type" : "input_text", "text" : user_prompt}, {"type" : "input_image", "image_url" : f"data:image/jpeg;base64,{base_image_64}"}, {"type" : "input_image", "image_url" : f"data:image/jpeg;base64,{comparison_64}"}]}])
        content         = response_object.output_text
        parsed_json     = json.loads(content[content.find("{") : content.rfind("}") + 1])
        verdict         = parsed_json["verdict"]
        reasoning       = parsed_json["reasoning"]

        return [verdict, reasoning] 
    
    except Exception as E:
        print(E)
        if (depth_number < 3):
            depth_number += 1
            return analyze_images(model_type, system_prompt, user_prompt, base_image, comparison_image, api_client, depth_number)
        else:
            return [None, None]

def calculate_multi_results(base_image_object: Image, compared_image_object: Image, flipped_image_object: Image, algorithm_types: list[str]) -> list:
    output_results = []
    
    for algorithm_type in algorithm_types:
        match (algorithm_type):
            case "ssim":
                base_score = structural_similarity(np.array(base_image_object), np.array(compared_image_object))
                flip_score = structural_similarity(np.array(base_image_object), np.array(flipped_image_object))
                max_score  = max(base_score, flip_score)
                output_results.extend([base_score, flip_score, max_score])
            case "hash":
                base_score = calculate_image_hash_similarity(base_image_object, compared_image_object)
                flip_score = calculate_image_hash_similarity(base_image_object, flipped_image_object)
                max_score  = max(base_score, flip_score)
                output_results.extend([base_score, flip_score, max_score])
            case _: 
                output_results.extend([None, None, None])

    return output_results


