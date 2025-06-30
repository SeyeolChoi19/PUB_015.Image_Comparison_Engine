import json

import datetime as dt 
import polars   as pl
import numpy    as np 

from skimage.metrics               import structural_similarity 
from misc_functions.misc_functions import calculate_image_proportions
from misc_functions.misc_functions import convert_image_to_array

class ImageProcessor:
    def __init__(self):
        self.current_date = str(dt.datetime.now().date())

    def image_processor_settings_method(self, department_map: str, images_list: list[str], output_columns: list[str]):
        self.department_map = pl.read_excel(department_map).sort(by = ["product_keywords"], descending = True)
        self.department_map = self.department_map.with_columns(pl.col("product_keywords").str.len_chars().alias("key_length"))
        self.department_map = self.department_map.sort(by = ["key_length", "product_keywords"], descending = [True, False])
        self.images_list    = images_list 
        self.output_columns = output_columns
        self.output_data    = []

    def compare_images(self):
        def comparison_process(base_image: str, image_file: str):
            results_list = [self.current_date, base_image.replace("\\", "/").split("/")[-1], image_file.replace("\\", "/").split("/")[-1], "", "", None, None, None]

            try: 
                converted_image = convert_image_to_array(image_file, self.base_width, self.base_height)
                flipped_image   = convert_image_to_array(image_file, self.base_width, self.base_height, True)
                base_score      = structural_similarity(self.base_image_object, converted_image)
                flip_score      = structural_similarity(self.base_image_object, flipped_image)
                average_score   = (base_score + flip_score) / 2
                results_list    = [self.current_date, base_image.replace("\\", "/").split("/")[-1], image_file.replace("\\", "/").split("/")[-1], "", "", base_score, flip_score, average_score]
            except Exception as E:
                pass 

            return results_list           

        for base_image in self.images_list:
            self.image_dimensions  = calculate_image_proportions(base_image)
            self.base_width        = self.image_dimensions[0]
            self.base_height       = self.image_dimensions[1]
            self.base_image_object = convert_image_to_array(base_image, self.base_width, self.base_height)

            for image_file in self.images_list:
                results_list = comparison_process(base_image, image_file)
                self.output_data.append(results_list)

    def process_output_data(self):
        def map_department_names(file_name: str):
            output_value = ""

            for (department_name, keyword) in zip(self.department_map["department_name"].to_list(), self.department_map["product_keywords"].to_list()):
                if (keyword.lower() in file_name.lower()):
                    output_value = department_name 
                    break 

            return output_value 

        self.result_data = pl.DataFrame(self.output_data, schema = self.output_columns, orient = "row")
        self.result_data = self.result_data.filter(pl.col("base_file_name") != pl.col("compared_image"))
        self.result_data = self.result_data.sort(by = ["base_file_name", "average_SSIM"], descending = True)

        for (column_name, new_column_name) in zip(["base_file_name", "compared_image"], ["base_department_name", "compared_department_name"]):
            self.result_data = self.result_data.with_columns(pl.struct([column_name]).map_elements(lambda x: map_department_names(x[column_name]), return_dtype = pl.String).alias(new_column_name))

        self.result_data.filter(pl.col("base_department_name") == pl.col("compared_department_name")).select(*self.output_columns).write_excel("2025-06-30 Image Processing Results.xlsx")

if (__name__ == "__main__"):
    with open("./config/ImageProcessorConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    image_processor = ImageProcessor()
    image_processor.image_processor_settings_method(**config_dict["ImageProcessor"]["image_processor_settings_method"])
    image_processor.compare_images()
    image_processor.process_output_data()
