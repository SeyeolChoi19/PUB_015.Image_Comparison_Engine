import json, os, streamlit, streamlit_js_eval, io

import datetime as dt 
import pandas   as pd 

from typing import List

from misc_functions.misc_functions     import json_processor 
from misc_functions.misc_functions     import lock_file_ops 
from pipeline_programs.ImageDownloader import ImageDownloader

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
        os.makedirs(f"./image_source_files/{self.current_date}", exist_ok = True)

    def __create_settings_table(self):
        def parse_filter_dictionary(filter_dictionary: dict):
            output_string = ""

            if (filter_dictionary is not None):
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
            self.layout_object.markdown("#### 설정 확인")
            self.layout_object.dataframe(self.settings_table, height = 213, hide_index = True)
            self.layout_object.markdown("")

    def __create_dropdown_menus(self, dataframe: pd.DataFrame):
        columns_dict = {"site_code_column" : "국가 구분자 컬럼", "tab_label_column" : "탭 라벨 컬럼", "image_urls_column" : "이미지 URL 컬럼"}

        for (key, value) in columns_dict.items():
            column_choice = self.layout_object.selectbox(value, list(dataframe.columns))

            if (column_choice):
                self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"][key] = column_choice
                json_processor(self.image_downloader_file, "w", self.image_downloader_dict)

    def __filter_dict_parser(self):
        text_window_strings = self.layout_object.text_input('컬럼별 필터링 조건 (없으면 "없음" 입력) (서식: {"컬럼명1" : ["필터링 조건1", "필터링 조건2"], "컬럼명2" : ["필터링 조건1", "필터링 조건2"]})')

        if (text_window_strings):
            if (text_window_strings != "없음"):
                try: 
                    filter_dict = json.loads(text_window_strings)
                    self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"]["filter_dictionary"] = filter_dict 
                    json_processor(self.image_downloader_file, "w", self.image_downloader_dict)
                except json.decoder.JSONDecodeError:
                    self.layout_object.write("필터 입력 포맷 오류")
                except Exception as E:
                    self.layout_object.write(f"필터 입력 오류: {E}")
            else:
                self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"]["filter_dictionary"] = None
                json_processor(self.image_downloader_file, "w", self.image_downloader_dict)

    def __file_upload_module(self):
        self.layout_object.markdown("#### 파일 업로드") 
        uploaded_file = self.layout_object.file_uploader("이미지 엑셀 파일 업로드", type = "xlsx")

        if (uploaded_file is not None):
            bytes_data = uploaded_file.read()
            file_path  = f"./image_source_files/{self.current_date}/{uploaded_file.name}"
            input_data = pd.read_excel(io.BytesIO(bytes_data))
            self.__create_dropdown_menus(input_data)
            self.__filter_dict_parser()
            self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"]["input_file"] = file_path
            json_processor(self.image_downloader_file, "w", self.image_downloader_dict)

            with open(file_path, "wb") as f:
                f.write(bytes_data)         

            if (self.layout_object.button("설정 적용")):
                streamlit_js_eval.streamlit_js_eval(js_expressions = "parent.window.location.reload()")

    def __file_download_module(self):
        def backend_execution():
            return_value = "Processing complete"

            if (not os.path.exists("./config/job.lock")):
                try:
                    lock_file_ops("running")
                    image_downloader = ImageDownloader()
                    image_downloader.image_downloader_settings_method(**self.image_downloader_dict["ImageDownloader"]["image_downloader_settings_method"])
                    image_downloader.download_images()
                    image_downloader.package_data()
                    
                    with open(image_downloader.output_file_name, "rb") as f:
                        self.layout_object.download_button(label = "결과 파일 받기", data = f.read(), file_name = image_downloader.output_file_name.split("/")[-1], mime = "application/zip")

                    lock_file_ops("remove")
                except Exception as E:
                    return_value = f"Exception Detected: {E}"
                    lock_file_ops("remove")

            else: 
                self.layout_object.write("백엔드 작업이 실행 중입니다. 종료될 때까지 기다려 주세요")
                return_value = "Backend processes running"

            return return_value
    
        self.layout_object.markdown("#### 이미지 다운로드")

        if (self.layout_object.button("작업 실행")):
            with self.layout_object.status("이미지 다운로드 중......"):
                return_value = backend_execution()

            match (return_value):
                case "Processing complete"       : self.layout_object.write("Processing complete")
                case "Backend processes running" : self.layout_object.write("")
                case _                           : self.layout_object.write(return_value)

    def __create_file_io_module(self, visualization_object: List[streamlit.delta_generator.DeltaGenerator]):
        with visualization_object:
            self.__file_upload_module()
    
    def __base_page_layout(self):
        self.layout_object.set_page_config(page_title = self.page_title, layout = self.layout)
        self.layout_object.title(self.dashboard_title)
        self.layout_object.markdown("#### 사용방법")
        self.layout_object.markdown("1. 이미지 URL이 있는 엑셀 파일을 업로드하면 컬럼 설정이 보임")
        self.layout_object.markdown("2. 드롭다운 메뉴로 필요 컬럼 지정")
        self.layout_object.markdown("3. 필터링이 필요할 경우 '{\"컬럼1\" : [\"규칙 1\", \"규칙 2\"], \"컬럼2\" : [\"규칙1\", \"규칙2\"]}' 형태로 입력")
        self.settings_table = self.__create_settings_table()
        
    def show_page_contents(self):
        self.__base_page_layout()
        settings_preview, file_io_module = self.layout_object.container(), self.layout_object.container()
        self.__display_settings_table(settings_preview)
        self.__create_file_io_module(file_io_module)
        self.__file_download_module()

if (__name__ == "__main__"):
    with open("./config/ImageAnalysisInterfaceConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    downloader_interface = ImageDownloadingInterface(**config_dict["ImageDownloadingInterface"]["constructor"])
    downloader_interface.image_downloading_interface_settings_method(**config_dict["ImageDownloadingInterface"]["image_downloading_interface_settings_method"])
    downloader_interface.show_page_contents()
