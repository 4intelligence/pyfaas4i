import pandas as pd
import re
import numpy as np
import datetime as dt
from typing import Dict, Type
import requests
import json
import gzip
import zlib
import base64
from unidecode import unidecode
import time
from requests.structures import CaseInsensitiveDict
from ._utilities import _get_access_token, APIError, AuthenticationError
from .services.auth_zero import FOURI_USER_AGENT


def _get_url(extension: str) -> str:
    """
    Defines the endpoint for the data to be sent
    Args:
        extension: Wheter to call the validation of modeling API
    Returns:
        An url in the for of a string
    """
    if extension == "projects":
        return "https://fourcasthub-faas-prod.azurewebsites.net/api/v1/projects"
    else:
        return "https://fourcasthub-validation-prod.azurewebsites.net/api/v1/validate"


def _check_model_spec(model_spec: dict) -> dict:
    """
    Checks for needed values in model_spec and fixes any eventual missing values
    Args:
        model_spec: provided dictionary with the specifications for modelling
    Returns:
        model_spec: filled model_spec with possible missing values
    """

    if (
        "golden_variables" in model_spec.keys()
        and isinstance(model_spec["golden_variables"], dict)
        and len(model_spec["golden_variables"]) == 0
    ):
        model_spec["golden_variables"] = []

    model_spec_template = {
        "log": [True],
        "seas.d": [True],
        "n_best": [20],
        "accuracy_crit": ["MAPE"],
        "info_crit": ["AIC"],
        "exclusions": [[]],
        "golden_variables": [],
        "fill_forecast": [False],
        "cv_summary": ["mean"],
        "selection_methods": {
            "lasso": [True],
            "rf": [True],
            "corr": [True],
            "apply.collinear": ["corr", "rf", "lasso", "no_reduction"],
        },
    }

    for key in list(model_spec_template.keys()):
        if key not in list(model_spec.keys()):
            model_spec[key] = model_spec_template[key]
        else:
            if key == "selection_methods":
                for sm_key in model_spec_template[key].keys():
                    if sm_key not in model_spec[key].keys():
                        model_spec[key][sm_key] = model_spec_template[key][sm_key]
                    elif sm_key == "apply.collinear" and isinstance(
                        model_spec[key][sm_key], bool
                    ):
                        if model_spec[key][sm_key] == True:
                            model_spec[key][sm_key] = model_spec_template[key][sm_key]
                        else:
                            model_spec[key][sm_key] = []

    return model_spec


def get_headers():
    pass


def _build_call(
    data_list: Dict[str, pd.DataFrame],
    date_variable: str,
    date_format: str,
    model_spec: dict,
    project_id: str,
    skip_validation: bool,
    extension: str,
) -> str:

    """
    This is the core function of PyFaaS4i, and it takes local data and sends it to 4intelligence's
    Forecast as a Service product for validation and modelling.
    Args:
        data_list: dictionary of pandas datataframes and their respective keys to be sent to the API
        date_variable: name of the variable to be considered as the timesteps
        date_format: format of date_variable following datetime notation
                    (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
        model_spec: dictionary containing arguments required by the API
        project_id: name of the project defined by the user
        skip_validation: if the validation step should be bypassed
        extension: Wheter to call the validation of modeling API

    Returns:
        A response from the called API
    """

    if not isinstance(skip_validation, bool):
        raise TypeError(f"skip_validation must be boolean (default is False), provided value was: {skip_validation}.")

    # ---- declare dummy email
    user_email = 'user@legitmail.com'
    # ----- Get access token from auth0

    access_token = _get_access_token()

    # ------ Check dataframes inside dictionary and turn them into dictionaries themselves
    missing_date_variable = []
    regex_special_chars= re.compile('[@!#$%^&*()<>?/\\|}{~:\[\].-]')
    
    for key in data_list.keys():
        
        # ----- cleaning column names

        # Checks for absence of date_variable in dataframes
        try:
            data_list[key][date_variable] = data_list[key][date_variable].astype(str)
        except:
            missing_date_variable.append(str(key))
            pass

        if key not in data_list[key].columns:
            raise KeyError(f"Variable {key} not found in the dataset")

        # ------ remove accentuation and special characters ------
        data_list[key].columns = [regex_special_chars.sub('_', unidecode(x)) for x in data_list[key].columns]
        
        # converting dataframes into dictionaries
        data_list[key] = data_list[key].fillna("NA").T.to_dict()

        for inner_key in list(data_list[key]):
            for innerer_key in list(data_list[key][inner_key]):
                if data_list[key][inner_key][innerer_key] == "NA":
                    del data_list[key][inner_key][innerer_key]

    # Checks if any dataframe is missing the date_variable
    if len(missing_date_variable) > 0:
        raise KeyError(
            f"Given date_variable '{date_variable}' not found in dataframe(s): {' '.join([str(x) for x in missing_date_variable])}"
        )

    # ------ Convert dict to list -----------------------------
    position = 1

    for key in list(data_list.keys()):
        data_list[key] = [x for x in data_list[key].values()]
        data_list[f"forecast_{position}_" + regex_special_chars.sub('_', unidecode(key))] = data_list.pop(key)
        position += 1


    
    
    # ------ removing accentuation ------
    if 'golden_variables' in model_spec.keys():
        model_spec["golden_variables"] = [
            regex_special_chars.sub('_', unidecode(i)) for i in model_spec["golden_variables"]
        ]
    
    if 'exclusions' in model_spec.keys():
        temp_exclusions = []
        for i in model_spec["exclusions"]:
            
            temp_j = []
            for j in i:
                if isinstance(j, str):                
                    temp_j.append(regex_special_chars.sub('_', unidecode(j)))
                else:
                    temp_k = []
                    for k in j:
                        temp_k.append(regex_special_chars.sub('_', unidecode(k)))
                    temp_j.append(temp_k)

            temp_exclusions.append(temp_j)
        
        model_spec["exclusions"] = temp_exclusions
    
   

    # ----- Change model_spec to be R compatible
    for key in model_spec.keys():
        if key == "selection_methods":
            for method in model_spec[key].keys():
                if method != "apply.collinear":
                    model_spec[key][method] = [model_spec[key][method]]
        elif key not in ["exclusions", "golden_variables"]:
            model_spec[key] = [model_spec[key]]

    # ----- Filling model_spec if anything is missing
    model_spec = _check_model_spec(model_spec)
    # ------ Unite everything into a dictionary -----------------
    body = {
        "data_list": data_list,
        "model_spec": model_spec,
        'user_email': [user_email],
        "project_id": [project_id],
        "date_variable": [date_variable],
        "date_format": [date_format],
    }
    
    # ----- Get the designated url ----------------------------------

    url = _get_url(extension)
    url_validation = _get_url("validate")
    zipped_body = base64.b64encode(
        gzip.compress(json.dumps(body).encode("utf-8"))
    ).decode("utf-8")

    # Uncomment to save locally

    # with open('./base64_body', 'wt') as save_file:

    #     save_file.write(zipped_body)

    # return 0

    headers = CaseInsensitiveDict()
    headers["authorization"] = f"Bearer {access_token}"
    headers["user-agent"] = FOURI_USER_AGENT

    def send_request(extension):
        if extension == "validate":

            return requests.post(
                url,
                {"body": zipped_body, "check_model_spec": True},
                headers=headers,
                timeout=1200,
            )

        else:
            if skip_validation:
                
                modelling_response = requests.post(
                    url,
                    json={"body": zipped_body, "skip_validation": True},
                    headers=headers,
                    timeout=1200,
                )
                modelling_status = modelling_response.status_code
                modelling_response = json.loads(modelling_response.text)
                modelling_response['api_status_code'] = modelling_status
                validation_response = {"status":"skip_validation", "info": "skip_validation"}
            else:
                # Now calls validation separately

                validation_response = requests.post(url_validation, {'body': zipped_body, 'check_model_spec': True}, headers=headers, timeout=1200)
                
                validation_code =  validation_response.status_code
                validation_response = json.loads(validation_response.text)

                if validation_code in [200, 201, 202] and validation_response['status'] in [200, 201, 202]:
                    if 'info' not in validation_response.keys() or 'error_list' not in validation_response['info'].keys():
                        modelling_response = requests.post(url, json={'body': zipped_body, 'skip_validation': True}, headers=headers, timeout=1200) 
                        modelling_status = modelling_response.status_code
                        modelling_response = json.loads(modelling_response.text)
                        modelling_response['api_status_code'] = modelling_status
                        
                else:
                    modelling_response = {"info": "validation_error"}

                    if validation_code not in [200, 201, 202]:
                        validation_response = {'api_status': validation_code, 'api_content': validation_response}


            return [validation_response, modelling_response]

    for _ in range(5):

        r = send_request(extension)

        if extension == "validate":
            if r.status_code != 500:
                break
            else:
                time.sleep(1)
        else:
            if any(key in ["status", "info"] for key in r[1].keys()):
                break
            else:
                time.sleep(1)

    return r



def validate_models(data_list: Dict[str, pd.DataFrame], 
date_variable: str, date_format: str, 
model_spec: dict, project_name: str, 
skip_validation: bool = False):
    '''
    This function directs the _build_call function to the validation API
     Args:
        data_list: dictionary of pandas datataframes and their respective keys to be sent to the API
        date_variable: name of the variable to be considered as the timesteps
        date_format: format of date_variable following datetime notation
                    (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
        model_spec: dictionary containing arguments required by the API
        project_name: name of the project defined by the user
        skip_validation: if the validation step should be bypassed

    Returns:
        If successfully received, returns the API's return code and email address to which the results
        will be sent. If failed, return API's return code.
    '''

    
    req = _build_call(data_list, date_variable, date_format, model_spec, project_name, 
    skip_validation, 'validate')
    req_status = req.status_code

    api_response = json.loads(req.text)
    
    if req_status not in [200, 201, 202]:
        if req_status in [408, 504]:
            raise APIError(f"Status Code: {str(req_status)}. Content: Timeout.\nPlease try sending a smaller data_list.")
        elif req_status == 401:
            raise AuthenticationError()
        elif req_status ==503:
            raise APIError(f"Status Code: {str(req_status)}. Content: Validation - Service Unavailable.\nPlease try again later.")
        else:
            raise APIError(f"Status Code: {str(req_status)}. Content: {str(api_response)}.\nCheck if you have the latest version of this package and/or try again later.")
        

    elif 'status' not in api_response:
        raise APIError(f"Status Code: {str(req_status)}. Content: {str(api_response)}.\nUnmapped internal error.")

    if api_response['status'] in [200, 201, 202]:
        print(f"Request successfully received and validated!\nNow you can call the run_models function to run your model.")
        

    else:
        print(f'Something went wrong!\nStatus code: {api_response["status"]}')
        if "info" in api_response.keys() and isinstance(api_response["info"], str):
            print(api_response["info"])

    if "info" in api_response.keys() and isinstance(api_response["info"], dict):

        if "error_list" in api_response["info"].keys() and isinstance(
            api_response["info"]["error_list"], dict
        ):
            print("\nError User Input:")
            error_list = api_response["info"]["error_list"]

            for error_place in error_list.keys():
                print(f"*{error_place}*\n")
                for error_field in error_list[error_place].keys():
                    error_description = error_list[error_place][error_field]
                    print(
                        f'{error_field}\n - {error_description["status"]}: {error_description["error_type"]}; Original Value: {error_description["original_value"]} in dataset: {error_description["dataset_error"]}'
                    )

        if "warning_list" in api_response["info"].keys() and isinstance(
            api_response["info"]["warning_list"], dict
        ):
            print("\nWarning User Input:")
            warning_list = api_response["info"]["warning_list"]

            for warning_place in warning_list.keys():
                print(f"*{warning_place}*\n")
                for warning_field in warning_list[warning_place].keys():
                    warning_description = warning_list[warning_place][warning_field]

                    print(f'{warning_field}\n - {warning_description["status"]}: {warning_description["error_type"]}; Original Value: {warning_description["original_value"]} in dataset: {warning_description["dataset_error"]}')




def run_models(data_list: Dict[str, pd.DataFrame], 
date_variable: str, date_format: str, 
model_spec: dict, project_name: str, skip_validation: bool = False) -> str:
    '''

    This function directs the _build_call function to the modeling API
     Args:
        data_list: dictionary of pandas datataframes and their respective keys to be sent to the API
        date_variable: name of the variable to be considered as the timesteps
        date_format: format of date_variable following datetime notation
                    (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
        model_spec: dictionary containing arguments required by the API
        project_name: name of the project defined by the user
        skip_validation: if the validation step should be bypassed

    Returns:
        If successfully received, returns the API's return code and email address to which the results
        will be sent. If failed, return API's return code.
    '''
    
    req = _build_call(data_list, date_variable, date_format, model_spec, project_name, 
    skip_validation, 'projects')
    api_response_validation = req[0]
    api_response_modelling = req[1]

    
    if 'api_status' in api_response_validation and api_response_validation['api_status'] not in [200, 201, 202] :
        if api_response_validation['api_status'] in [408, 504]:
            raise APIError(f"Status Code: {str(api_response_validation['api_status'])}. Content: Timeout.\nPlease try sending a smaller data_list.")
        elif api_response_validation['api_status'] == 503:
            raise APIError(f"Status Code: {str(api_response_validation['api_status'])}. Content: Validation - Service Unavailable.\nPlease try again later.")
        elif api_response_validation['api_status'] == 401:
            raise AuthenticationError()

        else:
            raise APIError(f"Status Code: {str(api_response_validation['api_status'])}. Content: {str(api_response_validation['api_content'])}.\nCheck if you have the latest version of this package and/or try again later.")

    elif 'status' not in api_response_validation:
        raise APIError(f"Status Code: {str(api_response_validation['api_status'])}. Content: {str(api_response_validation['api_content'])}.\nUnmapped internal error.")

    if 'info' not in api_response_validation.keys() or api_response_validation['info'] != 'skip_validation':

        if api_response_validation['status'] in [200, 201, 202]:
            print(f"Request successfully received and validated!")
    
        else:
            print(
                f'Something went wrong!\nStatus code: {api_response_validation["status"]}'
            )
            if "info" in api_response_validation.keys() and isinstance(
                api_response_validation["info"], str
            ):
                print(api_response_validation["info"])

        if "info" in api_response_validation.keys() and isinstance(
            api_response_validation["info"], dict
        ):

            if "error_list" in api_response_validation["info"].keys() and isinstance(
                api_response_validation["info"]["error_list"], dict
            ):
                print("\nError User Input:")
                error_list = api_response_validation["info"]["error_list"]

                for error_place in error_list.keys():
                    print(f"*{error_place}*\n")
                    for error_field in error_list[error_place].keys():
                        error_description = error_list[error_place][error_field]
                        print(
                            f'{error_field}\n - {error_description["status"]}: {error_description["error_type"]}; Original Value: {error_description["original_value"]} in dataset: {error_description["dataset_error"]}'
                        )

            if "warning_list" in api_response_validation["info"].keys() and isinstance(
                api_response_validation["info"]["warning_list"], dict
            ):
                print("\nWarning User Input:")
                warning_list = api_response_validation["info"]["warning_list"]

                for warning_place in warning_list.keys():
                    print(f"*{warning_place}*\n")
                    for warning_field in warning_list[warning_place].keys():
                        warning_description = warning_list[warning_place][warning_field]
                        print(
                            f'{warning_field}\n - {warning_description["status"]}: {warning_description["error_type"]}; Original Value: {warning_description["original_value"]} in dataset: {warning_description["dataset_error"]}'
                        )

    if (
        "info" not in api_response_modelling.keys()
        or api_response_modelling["info"] != "validation_error"
    ):
        
        if "status" in api_response_modelling.keys():
            if api_response_modelling["status"] in [200, 201, 202, "created"]:

                print(
                    f"HTTP: {api_response_modelling['status']}: Request successfully received!\nResults will soon be available in your Projects module."
                )

            else: # if the error was returned in the status inside the API
                if api_response_modelling["status"] in [408, 504]:
                    raise APIError(f"Status Code: {str(api_response_modelling['status'])}. Content: Timeout.\nPlease try sending a smaller data_list.")
                
                elif api_response_modelling["status"] == 503:
                    raise APIError(f"Status Code: {str(api_response_modelling['status'])}. Content: Modeling - Service Unavailable.\nPlease try again later.")
                elif api_response_modelling["status"] == 401:
                    raise AuthenticationError()
                else:
                    raise APIError(
                        f"Something went wrong when sending to modeling!\nStatus code: {api_response_modelling['status']}."
                )
        else: # if the api did not return expected dictionary
            if api_response_modelling["api_status_code"] in [408, 504]:
                    raise APIError(f"Status Code: {str(api_response_modelling['api_status_code'])}. Content: Timeout.\nPlease try sending a smaller data_list.")
                
            elif api_response_modelling["api_status_code"] == 503:
                raise APIError(f"Status Code: {str(api_response_modelling['api_status_code'])}. Content: Modeling - Service Unavailable.\nPlease try again later.")
            elif api_response_modelling["api_status_code"] == 401:
                raise AuthenticationError()
            else:
                raise APIError(
                    f"Something went wrong when sending to modeling!\nStatus code: {api_response_modelling['api_status_code']}."
                )
