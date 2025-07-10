import datetime as dt

from typing import Callable 

def download_ops_decorator(indicator_string: str):
    def wrapper_function(inner_function: Callable):
        def wrapped_function(self, *args, **kwargs):
            file_name  = f'{args[1]}_{args[2]}.jpg'

            try: 
                inner_function(self, *args, **kwargs)
                self.data_log_object.info(f"{str(dt.datetime.now())} - {indicator_string} operation successful: {file_name}")
            except Exception as E: 
                self.data_log_object.debug(f"{str(dt.datetime.now())} - {indicator_string} operation failure: {file_name} {E}")
                
        return wrapped_function 
    
    return wrapper_function

def operation_indicator(indicator_string: str):
    def wrapper_function(inner_function: Callable):
        def wrapped_function(self, *args, **kwargs):
            try: 
                inner_function(self, *args, **kwargs)
                self.data_log_object.info(f"{str(dt.datetime.now())} - {indicator_string} operation successful")
            except Exception as E: 
                self.data_log_object.debug(f"{str(dt.datetime.now())} - {indicator_string} operation failure {E}")
                
        return wrapped_function 
    
    return wrapper_function    
