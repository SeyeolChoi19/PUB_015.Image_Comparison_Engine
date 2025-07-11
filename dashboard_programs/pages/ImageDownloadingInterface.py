import json, os, streamlit

import datetime as dt 
import pandas   as pd 

from typing import List

from misc_functions.misc_functions import json_processor 
from misc_functions.misc_functions import lock_file_ops 

class ImageDownloadingInterface: 
    def __init__(self, page_title: str, layout: str):
        self.page_title   = page_title 
        self.layout       = layout 
        self.current_date = str(dt.datetime.now().date())

    def image_downloading_interface_settings_method(self, dashboard_title: str, image_downloader_file: str):
        self.dashboard_title       = dashboard_title 
        self.image_downloader_file = image_downloader_file
        self.image_downloader_dict = json_processor(image_downloader_file, "r")
        self.layout_object         = streamlit

    def __create_settings_table(self):
        def parse_filter_dictionary(filter_dictionary: dict):
            output_string = ""

            for (key, value) in filter_dictionary.items():
                output_string += f"{key} : {', '.join(value)}\n\n"

            return output_string

        settings_table    = self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"]
        input_file_name   = ["이미지 리스트 파일", settings_table["input_file"].replace("\\", "/").split("/")[-1]]
        site_code_column  = ["사이트 코드 구분자 컬럼", settings_table["site_code_column"]]
        tab_label_column  = ["탭 라벨 컬럼", settings_table["tab_label_column"]]
        image_urls_column = ["이미지 URL 컬럼", settings_table["image_urls_column"]]
        filter_dictionary = ["필터 설정", parse_filter_dictionary(settings_table["filter_dictionary"])]
        output_dictionary = pd.DataFrame([input_file_name, site_code_column, tab_label_column, image_urls_column, filter_dictionary], columns = ["설정 항목", "설정 값"])

        return output_dictionary

    def __display_settings_table(self, visualization_object: List[streamlit.delta_generator.DeltaGenerator]):
        with visualization_object: 
            self.layout_object.markdown("")
            self.layout_object.markdown("설정 확인")
            self.layout_object.dataframe(self.settings_table, height = 213, hide_index = True)
            self.layout_object.markdown("")
    
    def __base_page_layout(self):
        self.layout_object.set_page_config(page_title = self.page_title, layout = self.layout)
        self.layout_object.title(self.dashboard_title)
        self.layout_object.markdown("#### Test")
        self.settings_table = self.__create_settings_table()
        
    def show_page_contents(self):
        self.__base_page_layout()
        settings_preview, settings_module = self.layout_object.columns(2)
        self.__display_settings_table(settings_preview)

if (__name__ == "__main__"):
    with open("./config/ImageAnalysisInterfaceConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    downloader_interface = ImageDownloadingInterface(**config_dict["ImageDownloadingInterface"]["constructor"])
    downloader_interface.image_downloading_interface_settings_method(**config_dict["ImageDownloadingInterface"]["image_downloading_interface_settings_method"])
    downloader_interface.show_page_contents()
