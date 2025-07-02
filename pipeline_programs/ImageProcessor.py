import json, openai, os

import datetime as dt 
import polars   as pl

from PIL       import Image
from threading import Lock

from concurrent.futures            import ThreadPoolExecutor
from misc_functions.misc_functions import calculate_image_proportions
from misc_functions.misc_functions import preprocess_image
from misc_functions.misc_functions import calculate_multi_results
from misc_functions.misc_functions import text_file_processor
from misc_functions.misc_functions import analyze_images 

class ImageProcessor:
    def __init__(self):
        self.current_date = str(dt.datetime.now().date())

    def image_processor_settings_method(self, department_map: str, system_prompt_file: str, user_prompt_file: str, gpt_model_name: str, images_list: list[str], output_columns: list[str]):
        self.department_map = pl.read_excel(department_map).sort(by = ["product_keywords"], descending = True)
        self.system_prompt  = text_file_processor(system_prompt_file, "r")
        self.user_prompt    = text_file_processor(user_prompt_file, "r")
        self.gpt_model_name = gpt_model_name
        self.department_map = self.department_map.with_columns(pl.col("product_keywords").str.len_chars().alias("key_length"))
        self.department_map = self.department_map.sort(by = ["key_length", "product_keywords"], descending = [True, False])
        self.images_list    = images_list 
        self.gpt_api_object = openai.OpenAI(api_key = os.getenv("GPT_API_KEY"))
        self.output_columns = output_columns
        self.output_data    = []

    def compare_images(self):
        def comparison_process(base_image: str, image_file: str, base_width: int, base_height: int, base_image_object: Image):
            results_list = [self.current_date, base_image.replace("\\", "/"), image_file.replace("\\", "/"), "", "", None, None, None]

            try: 
                converted_image   = preprocess_image(image_file, base_width, base_height)
                flipped_image     = preprocess_image(image_file, base_width, base_height, True)
                algorithm_results = calculate_multi_results(base_image_object, converted_image, flipped_image, ["ssim", "hash"])
                results_list      = [self.current_date, base_image.replace("\\", "/"), image_file.replace("\\", "/"), "", ""] + algorithm_results
            except Exception as E:
                pass 

            return results_list           

        for base_image in self.images_list:
            image_dimensions  = calculate_image_proportions(base_image)
            base_width        = image_dimensions[0]
            base_height       = image_dimensions[1]
            base_image_object = preprocess_image(base_image, base_width, base_height)

            for image_file in self.images_list:
                results_list = comparison_process(base_image, image_file, base_width, base_height, base_image_object)
                self.output_data.append(results_list)

    def process_output_data(self):
        def map_department_names(file_name: str):
            output_value = ""

            for (department_name, keyword) in zip(self.department_map["department_name"].to_list(), self.department_map["product_keywords"].to_list()):
                if (keyword.lower() in file_name.lower()):
                    output_value = department_name 
                    break 

            return output_value 

        def process_columns():
            result_data = pl.DataFrame(self.output_data, schema = self.output_columns, orient = "row")
            result_data = result_data.filter(pl.col("base_file_name") != pl.col("compared_image"))
            result_data = result_data.with_columns(((pl.col("max_phash").fill_null(0) + pl.col("max_SSIM").fill_null(0)) / 2).alias("average_similarity"))
            result_data = result_data.sort(by = ["base_file_name", "average_similarity"], descending = True)

            for (column_name, new_column_name) in zip(["base_file_name", "compared_image"], ["base_department_name", "compared_department_name"]):
                result_data = result_data.with_columns(pl.struct([column_name]).map_elements(lambda x: map_department_names(x[column_name]), return_dtype = pl.String).alias(new_column_name))

            return result_data

        def apply_thresholds(similarity_value: float):
            threshold_dict = {
                "very likely match" : 0.75, 
                "possible match"    : 0.5, 
                "unlikely match"    : 0.25, 
                "no match"          : 0
            }

            for (label, threshold) in threshold_dict.items():
                if (threshold + 0.25 >= similarity_value > threshold):
                    output_value = label
                    break 

            return output_value
        
        self.result_data = process_columns()
        self.result_data = self.result_data.with_columns(pl.struct(["average_similarity"]).map_elements(lambda x: apply_thresholds(x["average_similarity"]), return_dtype = pl.String).alias("match_status"))
        self.result_data = self.result_data.filter(pl.col("base_department_name") == pl.col("compared_department_name")).select(*self.output_columns + ["average_similarity", "match_status"])

    def apply_gen_ai(self):
        def preprocess_for_multiprocessing():
            output_data_list = []

            for index_number in range(0, self.result_data.height, self.result_data.height // 4):
                sub_dataframe = self.result_data[index_number : self.result_data.height // 4 + index_number]
                output_data_list.append(sub_dataframe)

            return output_data_list

        def multiprocessing_function(base_images_list: list[str], comparisons_list: list[str]):
            output_list = []
    
            for (base_image, comparison_image) in zip(base_images_list, comparisons_list):
                results_list = [base_image, comparison_image] + analyze_images(self.gpt_model_name, self.system_prompt, self.user_prompt, base_image, comparison_image, self.gpt_api_object)
                output_list.append(results_list)

            return output_list

        data_list, storage_list = preprocess_for_multiprocessing(), []

        with ThreadPoolExecutor(max_workers = 4) as executor: 
            for dataframe in data_list: 
                base_image_list     = dataframe["base_file_name"].to_list()
                compared_image_list = dataframe["compared_image"].to_list()
                future_object       = executor.submit(multiprocessing_function, base_image_list, compared_image_list)
                storage_list.append(future_object)

        gen_ai_results   = pl.DataFrame([future.result() for future in storage_list], schema = ["base_file_name", "compared_image", "verdict", "reasoning"])                
        self.result_data = self.result_data.join(gen_ai_results, how = "left", on = ["base_file_name", "compared_image"])

if (__name__ == "__main__"):
    with open("./config/ImageProcessorConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    image_processor = ImageProcessor()
    image_processor.image_processor_settings_method(**config_dict["ImageProcessor"]["image_processor_settings_method"])
    image_processor.compare_images()
    image_processor.process_output_data()
    image_processor.apply_gen_ai()
