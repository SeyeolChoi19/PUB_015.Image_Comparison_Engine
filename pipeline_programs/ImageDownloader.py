import os, json, requests, logging, shutil, unicodedata, re

import datetime as dt 
import polars   as pl 

from exceptions.exceptions         import download_ops_decorator
from exceptions.exceptions         import operation_indicator
from misc_functions.misc_functions import lock_file_ops

class ImageDownloader:
    def __init__(self):
        self.current_date = str(dt.datetime.now().date())
        logging.basicConfig(filename = f"./config/log_files/{self.current_date} Image Download Log.log", filemode = "a", format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s", encoding = "utf-8")

    def image_downloader_settings_method(self, input_file: str, site_code_column: str, tab_label_column: str, image_urls_column: str, filter_dictionary: dict = None):
        self.input_data        = pl.read_excel(input_file)
        self.site_code_column  = site_code_column 
        self.tab_label_column  = tab_label_column 
        self.image_urls_column = image_urls_column
        self.filter_dictionary = filter_dictionary
        self.output_image_path = f"./image_folder/{self.current_date}" 
        self.data_log_object   = logging.getLogger("Image Downloader Log")
        self.data_log_object.setLevel(logging.DEBUG)
        self.data_log_object.info(f"{str(dt.datetime.now())} - Image downloading operations")
        os.makedirs(self.output_image_path, exist_ok = True)

        if (self.filter_dictionary is not None):
            for (key, value) in self.filter_dictionary.items():
                self.input_data = self.input_data.filter(pl.col(key).cast(pl.String).is_in(value))

    @download_ops_decorator("File downloading")
    def __download_image(self, image_url: str, site_code: str, tab_label: str):
        response = requests.get(image_url)

        if (response.status_code == 200):
            with open(f"{self.output_image_path}/{site_code}_{tab_label}.jpg", "wb") as f:
                f.write(response.content)
        else:
            raise Exception("Image download error")

    def download_images(self):
        image_urls, site_codes, tab_labels = self.input_data[self.image_urls_column].to_list(), self.input_data[self.site_code_column].to_list(), self.input_data[self.tab_label_column].to_list()

        for (image_url, site_code, tab_label) in zip(image_urls, site_codes, tab_labels):
            image_url = f"https:{image_url}" if (image_url.startswith("//")) else image_url
            tab_label = re.sub(r'[\/:*?"<>|]', '-', unicodedata.normalize("NFKC", tab_label)).replace("\n", " ").replace("\r", " ")
            self.__download_image(image_url, site_code, tab_label)
       
    @operation_indicator("Packaging image files")
    def package_data(self):
        self.output_file_name = f"./output_images/{str(dt.datetime.now())[0:19].replace(':', '')} Image Files.zip"
        shutil.make_archive(self.output_file_name[:-4], "zip", self.output_image_path)
        shutil.rmtree(self.output_image_path)
        lock_file_ops("remove")

if (__name__ == "__main__"):
    with open("./config/ImageDownloaderConfig.json", "r", encoding = "utf-8") as f:
        config_dict = json.load(f)

    image_downloader = ImageDownloader()
    image_downloader.image_downloader_settings_method(**config_dict["ImageDownloader"]["image_downloader_settings_method"])
    image_downloader.download_images()
    image_downloader.package_data()    
