import os, json, streamlit, streamlit_js_eval

import datetime as dt 
import pandas   as pd 

from typing import List

class GetPreviousFiles:
    def __init__(self, page_title: str, layout: str):
        self.page_title = page_title 
        self.layout     = layout  

    def get_previous_files_settings_method(self, dashboard_title: str):
        self.dashboard_title = dashboard_title 
        self.layout_object   = streamlit 

    def __create_files_table(self, file_path: str):
        categorized_files  = [f"{file_path}/{file_name}" for file_name in sorted(os.listdir(file_path), reverse = True)]
        file_creation_date = [dt.datetime.fromtimestamp(os.path.getctime(file_name)).strftime("%Y-%m-%d %H:%M:%S") for file_name in categorized_files]
        file_sizes_list    = [f"{round(os.path.getsize(file_name) / 1024, 3)} kb" for file_name in categorized_files]
        files_list_table   = pd.DataFrame({"file_name" : categorized_files, "creation_date" : file_creation_date, "file_size" : file_sizes_list})

        return files_list_table 
    
    def __display_files_tables(self, visualization_objects: list[List[streamlit.delta_generator.DeltaGenerator]]):
        result_files_table    = self.__create_files_table("./output_files")
        prompt_files_table    = self.__create_files_table("./config/prompts")
        category_dictionaries = self.__create_files_table("./config/mapping_dictionaries")
        image_zip_files       = self.__create_files_table("./output_images")

        for (visualization_object, dataframe, file_type) in zip(visualization_objects, [result_files_table, prompt_files_table, category_dictionaries, image_zip_files], ["#### 결과 파일", "#### 프롬프트 파일", "#### 카테고리 딕셔너리", "#### 결과 이미지"]): 
            with visualization_object:
                self.layout_object.markdown(file_type)
                self.layout_object.dataframe(dataframe, height = 388, hide_index = True)

    def __file_download_module(self):
        self.layout_object.markdown("")
        self.layout_object.markdown("#### 파일 다운로드")
        input_file_name = self.layout_object.text_input("파일명 입력")

        if (input_file_name):
            if ("last_file" not in self.layout_object.session_state):
                self.layout_object.session_state["last_file"] = ""

            if (input_file_name != self.layout_object.session_state["last_file"]):
                self.layout_object.session_state["file_data"] = None 
                self.layout_object.session_state["file_name"] = None 
                self.layout_object.session_state["last_file"] = input_file_name

            with open(input_file_name, "rb") as file_data:
                file_mime = "text/plain" if (input_file_name.lower().endswith(".txt")) else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                self.layout_object.download_button(label = "데이터 다운로드", data = file_data.read(), file_name = input_file_name.split("/")[-1], mime = file_mime)   

    def __base_page_layout(self):
        self.layout_object.set_page_config(page_title = self.page_title, layout = self.layout)
        self.layout_object.title(self.dashboard_title)
        self.layout_object.markdown("#### 사용방법")
        self.layout_object.markdown(" - 파일 테이블에서 파일명을 확인한 후 '파일 다운로드'에 입력하여 다운로드")
        self.layout_object.markdown(" - 복수 파일 다운로드 시 페이지 새로고침 필요")
        self.layout_object.markdown("")
    
    def show_page_contents(self):
        self.__base_page_layout()
        table_list = self.layout_object.columns(4)
        self.__display_files_tables(table_list)
        self.__file_download_module()

if (__name__ == "__main__"):
    with open("./config/ImageAnalysisInterfaceConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    previous_files_module = GetPreviousFiles(**config_dict["GetPreviousFiles"]["constructor"])
    previous_files_module.get_previous_files_settings_method(**config_dict["GetPreviousFiles"]["get_previous_files_settings_method"])
    previous_files_module.show_page_contents()
