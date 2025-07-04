import streamlit, json, os, shutil, streamlit_js_eval

import datetime as dt 
import pandas   as pd 

from typing import List

from misc_functions.misc_functions    import json_processor
from misc_functions.misc_functions    import text_file_processor
from misc_functions.misc_functions    import lock_file_ops
from pipeline_programs.ImageProcessor import ImageProcessor

class ImageAnalysisInterface:
    def __init__(self, page_title: str, layout: str):
        self.page_title   = page_title 
        self.layout       = layout 
        self.current_date = str(dt.datetime.now())[0:19].replace(":", "")

    def image_analysis_interface_settings_method(self, dashboard_title: str, image_processor_config: str, model_options: list[str]):
        self.dashboard_title             = dashboard_title 
        self.model_options               = model_options
        self.image_processor_config_file = image_processor_config 
        self.image_processor_config_dict = json_processor(image_processor_config, "r")
        self.layout_object               = streamlit 
        os.makedirs(f"./data/{self.current_date}/base_images", exist_ok = True)
        os.makedirs(f"./data/{self.current_date}/comparison_images", exist_ok = True)

        if (len(os.listdir(f"./data")) > 300):
            sub_list = sorted(os.listdir(f"./data"))

            for sub_folder in sub_list:
                shutil.rmtree(f"./data/{sub_folder}")

    def __create_settings_table(self):
        settings_table    = self.image_processor_config_dict["ImageProcessor"]["image_processor_settings_method"]
        base_images       = ["베이스 이미지", ", \n".join([file_name.replace("\\", "/").split("/")[-1] for file_name in settings_table["base_images"]])]
        comparison_images = ["비교 이미지", ", \n".join([file_name.replace("\\", "/").split("/")[-1] for file_name in settings_table["comparison_images"]])]
        system_prompt     = ["분석 프롬프트", text_file_processor(settings_table["system_prompt_file"], "r")]
        output_table      = pd.DataFrame([base_images, comparison_images, system_prompt], columns = ["설정 항목", "설정 값"])

        return output_table 

    def __display_settings_table(self):
        self.layout_object.markdown("")
        self.layout_object.markdown("설정 확인")
        self.layout_object.dataframe(self.settings_table, height = 143, hide_index = True)    
        self.layout_object.markdown("")

    def __zip_file_handler(self, config_key: str, file_path: str, uploaded_file):
        if (uploaded_file.name.endswith(".zip") != True):
            self.image_processor_config_dict["ImageProcessor"]["image_processor_settings_method"][config_key] = file_path 
        else:
            shutil.unpack_archive(file_path, f"./data/{self.current_date}/{config_key}", "zip")
            files_list = [f"./data/{self.current_date}/{config_key}/{file_name}" for file_name in os.listdir(f"./data/{self.current_date}/{config_key}")]
            self.image_processor_config_dict["ImageProcessor"]["image_processor_settings_method"][config_key] = files_list
        
        json_processor(self.image_processor_config_file, "w", self.image_processor_config_dict)
        
    def __create_uploader(self, config_key: str, upload_label: str, file_type: str, visualization_object: List[streamlit.delta_generator.DeltaGenerator]):
        with visualization_object:
            uploaded_file = self.layout_object.file_uploader(upload_label, type = file_type)

            if (uploaded_file is not None):
                bytes_data = uploaded_file.read()
                file_path  = f"./{(lambda x: 'config/prompts/' if (x == 'system_prompt_file') else 'config/' if (x == 'department_map') else '')(config_key)}{uploaded_file.name}"
                streamlit_js_eval.streamlit_js_eval(js_expressions = "parent.window.location.reload()")
                
                with open(file_path, "wb") as output_file:
                    output_file.write(bytes_data)

                self.__zip_file_handler(config_key, file_path, uploaded_file)

    def __toggle_gpt_model(self, visualization_object: List[streamlit.delta_generator.DeltaGenerator]):
        with visualization_object: 
            model_choice = self.layout_object.selectbox("모형 선택", self.model_options)

            if (model_choice):
                self.image_processor_config_dict["ImageProcessor"]["image_processor_settings_method"]["gpt_model_name"] = model_choice.split("(")[0].strip()
                json_processor(self.image_processor_config_file, "w", self.image_processor_config_dict)

    def __execute_program(self, visualization_object: List[streamlit.delta_generator.DeltaGenerator]):
        def backend_execution():
            lock_file_ops("running")

            try:
                image_analyzer = ImageProcessor()
                image_analyzer.image_processor_settings_method(**self.image_processor_config_dict["ImageProcessor"]["image_processor_settings_method"])
                image_analyzer.compare_images()
                image_analyzer.process_output_data()
                image_analyzer.apply_gen_ai()
                image_analyzer.save_output_data(self.current_date)

                with open(f"./output_files/{self.current_date} Image Processing Results.xlsx", "rb") as f:
                    self.layout_object.download_button(label = "결과 데이터 받기", data = f.read(), file_name = f"{self.current_date} Image Processing Results.xlsx", mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except Exception as E:
                print(E)
            
            lock_file_ops("remove")

        with visualization_object:
            backend_status = "실행 중" if (os.path.exists("./config/job.lock")) else "대기 중"
            self.layout_object.markdown(f"프로그램 실행 (백 앤드 상태: {backend_status})")
            
            if (self.layout_object.button("작업 실행")):
                if (backend_status == "대기 중"):
                    with self.layout_object.status("분석 진행 중......"):
                        backend_execution()
                else:
                    self.layout_object.write("백엔드 작업이 실행 중입니다. 종료될 때까지 기다려 주세요")
                
    def __create_uploaders(self, base_uploader: List[streamlit.delta_generator.DeltaGenerator], comparison_uploader: List[streamlit.delta_generator.DeltaGenerator], map_uploader: List[streamlit.delta_generator.DeltaGenerator], prompt_uploader: List[streamlit.delta_generator.DeltaGenerator]):
        config_keys    = ["base_images", "comparison_images", "department_map", "system_prompt_file"]
        upload_labels  = ["베이스 이미지", "비교 이미지", "부서 매핑 파일", "분석 프롬프트"]
        file_types     = ["zip", "zip", "xlsx", "txt"]
        visual_objects = [base_uploader, comparison_uploader, map_uploader, prompt_uploader]
        
        for (config_key, upload_label, file_type, viz_object) in zip(config_keys, upload_labels, file_types, visual_objects):
            self.__create_uploader(config_key, upload_label, file_type, viz_object)
                       
    def __base_page_layout(self):
        self.layout_object.set_page_config(page_title = self.page_title, layout = self.layout)
        self.layout_object.title(self.dashboard_title)
        self.layout_object.markdown("#### 주의사항")
        self.layout_object.markdown(" - 업로드하는 파일명에 한국어가 포함되면 안 됩니다.")
        self.layout_object.markdown(" - 프롬프트는 한국어 또는 영어로 작성할 수 있으나, 가능한 한 영어로 작성하는 것을 권장합니다")
        self.layout_object.markdown(" - 이미지는 압축파일로 업로드해야 합니다 (.zip 파일)")
        self.settings_table = self.__create_settings_table()

    def show_page_contents(self):
        self.__base_page_layout()
        self.__display_settings_table()
        base_uploader, comparison_uploader, gpt_toggle  = self.layout_object.columns(3)
        map_uploader, prompt_uploader, execution_button = self.layout_object.columns(3)
        self.__toggle_gpt_model(gpt_toggle)
        self.__execute_program(execution_button)
        self.__create_uploaders(base_uploader, comparison_uploader, map_uploader, prompt_uploader)

if (__name__ == "__main__"):
    with open("./config/ImageAnalysisInterfaceConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    analysis_interface = ImageAnalysisInterface(**config_dict["ImageAnalysisInterface"]["constructor"])
    analysis_interface.image_analysis_interface_settings_method(**config_dict["ImageAnalysisInterface"]["image_analysis_interface_settings_method"])
    analysis_interface.show_page_contents()
