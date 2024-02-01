import pandas as pd
import re
import copy
import numpy as np
import datetime as dt
from typing import Dict, Type, Union
import requests
import json
import gzip
import zlib
import base64
from unidecode import unidecode
import time
from requests.structures import CaseInsensitiveDict
from ._utilities import _get_access_token, _version_check, _get_proxies, APIError, AuthenticationError
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
        return "https://run-prod-4casthub-faas-modelling-api-zdfk3g7cpq-ue.a.run.app/api/v1/projects"
    else:
        return "https://run-prod-4casthub-api-faas-validation-zdfk3g7cpq-ue.a.run.app/api/v1/validate"


def _check_model_spec(model_spec: dict, column_list: list) -> dict:
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

    # If lags is 'all', we replace it by all variable names, except for variables
    # that are y and date_variable
   
    if 'lags' in model_spec.keys() and 'all' in model_spec['lags'].keys():
        lags_all = model_spec['lags']['all'].copy()    
        for var in column_list:
            if var not in model_spec['lags'].keys():
                model_spec['lags'][var] = lags_all
        model_spec['lags'].pop('all')

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
        "lags": {},
        "allowdrift": [True],
        "user_model": [[]]
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



def _build_call(
    data_list: Dict[str, pd.DataFrame],
    date_variable: str,
    date_format: str,
    model_spec: dict,
    project_id: str,
    skip_validation: bool,
    version_check: bool,
    extension: str,
    proxy_url: Union[str, None],
    proxy_port: Union[str, None]
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
        proxy_url: A proxy for URL during the request
        proxy_port: A proxy for port to compose the URL during the request
    Returns:
        A response from the called API
    """

    if not isinstance(skip_validation, bool):
        raise TypeError(f"skip_validation must be boolean (default is False), provided value was: {skip_validation}.")

    # ---- Check project_id length
    if len(project_id) > 50:
        raise ValueError("The project_name should be at most 50 characters long.")

    data_list = data_list.copy()
    formatted_model_spec = copy.deepcopy(model_spec)

    # ---- declare dummy email
    user_email = 'user@legitmail.com'
    # ----- Get access token from auth0

    access_token = _get_access_token()

    # ----- Get proxies (if any)
    proxies = _get_proxies(proxy_url=proxy_url,
                           proxy_port=proxy_port)

    # ---- Check package version

    if version_check:
        _version_check(proxies=proxies)

    # ------ Check dataframes inside dictionary and turn them into dictionaries themselves
    missing_date_variable = []
    long_variable_name = []
    regex_special_chars = re.compile('[@!#$%^&*()<>?/\\|}{~:\[\].-]')
    columns_list = []

    # Formatting date_variable and keeping the original value for checking
    orig_date_variable = date_variable
    date_variable = regex_special_chars.sub('_', unidecode(date_variable.lower()))

    for key in data_list.keys():
        
        # ----- cleaning column names

        # Checks for absence of orig_date_variable in dataframes
        try:
            data_list[key][orig_date_variable] = data_list[key][orig_date_variable].astype(str)
        except:
            missing_date_variable.append(str(key))
            pass

        if key not in data_list[key].columns:
            raise KeyError(f"Variable {key} not found in the dataset")

        # ------ remove accentuation and special characters ------
        data_list[key].columns = [regex_special_chars.sub('_', unidecode(x.lower())) for x in data_list[key].columns]

        # fill columns_list removing date and y variables
        columns_list = columns_list + list(data_list[key].columns)
        formatted_y_var = regex_special_chars.sub('_', unidecode(key.lower()))
        columns_list.remove(formatted_y_var)
        try:
            columns_list.remove(date_variable)
        except:
            pass

        if any(len(col) > 50 for col in data_list[key].columns):
            long_variable_name.append(str(key))

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

    # Checks if any dataframe have a variable name longer than 50 characters
    if len(long_variable_name) > 0:
        raise KeyError(
            f"At least one variable name longer than 50 characters found in dataframe(s): {' '.join([str(x) for x in long_variable_name])}"
        )

    # ------ Convert dict to list -----------------------------
    position = 1

    for key in list(data_list.keys()):
        data_list[key] = [x for x in data_list[key].values()]
        data_list[f"forecast_{position}_" + regex_special_chars.sub('_', unidecode(key.lower()))] = data_list.pop(key)
        position += 1


    
    
    # ------ removing accentuation and special characters------
    if 'golden_variables' in formatted_model_spec.keys():
        formatted_model_spec["golden_variables"] = [
            regex_special_chars.sub('_', unidecode(i.lower())) for i in formatted_model_spec["golden_variables"]
        ]
    
    if 'exclusions' in formatted_model_spec.keys():
        temp_exclusions = []
        for i in formatted_model_spec["exclusions"]:
            
            temp_j = []
            for j in i:
                if isinstance(j, str):                
                    temp_j.append(regex_special_chars.sub('_', unidecode(j.lower())))
                else:
                    temp_k = []
                    for k in j:
                        temp_k.append(regex_special_chars.sub('_', unidecode(k.lower())))
                    temp_j.append(temp_k)

            temp_exclusions.append(temp_j)
        
        formatted_model_spec["exclusions"] = temp_exclusions
    
    if 'lags' in formatted_model_spec.keys():
        temp_lags = {}
        for var, lags in formatted_model_spec['lags'].items():
            var_tidy = regex_special_chars.sub('_', unidecode(var.lower()))
            temp_lags[var_tidy] = lags
        formatted_model_spec['lags'] = temp_lags
    
    
    if 'user_model' in formatted_model_spec.keys():
        temp_user_model = []

        for i in formatted_model_spec["user_model"]:       
                temp_j = []
                for j in i:
                    temp_j.append(regex_special_chars.sub('_', unidecode(j.lower())))
                temp_user_model.append(temp_j)
        formatted_model_spec["user_model"] = temp_user_model

    # ----- Change formatted_model_spec to be R compatible
    for key in formatted_model_spec.keys():
        if key == "selection_methods":
            for method in formatted_model_spec[key].keys():
                if method != "apply.collinear":
                    formatted_model_spec[key][method] = [formatted_model_spec[key][method]]
        elif key not in ["lags", "exclusions", "golden_variables", "user_model"]:
            formatted_model_spec[key] = [formatted_model_spec[key]]

    # ----- Filling formatted_model_spec if anything is missing
    columns_list = list(set(columns_list))
    formatted_model_spec = _check_model_spec(model_spec=formatted_model_spec, column_list=columns_list)
    # ------ Unite everything into a dictionary -----------------
   
    body = {
        "data_list": data_list,
        "model_spec": formatted_model_spec,
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

    # with open('./base64_body_lag_2', 'wt') as save_file:

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
                proxies=proxies
            )

        else:
            if skip_validation:
                
                modelling_response = requests.post(
                    url,
                    json={"body": zipped_body, "skip_validation": True},
                    headers=headers,
                    timeout=1200,
                    proxies=proxies
                )
                modelling_status = modelling_response.status_code
                modelling_response = json.loads(modelling_response.text)
                modelling_response['api_status_code'] = modelling_status
                validation_response = {"status":"skip_validation", "info": "skip_validation"}
            else:
                # Now calls validation separately

                validation_response = requests.post(url_validation,
                                                    {'body': zipped_body,
                                                     'check_model_spec': True},
                                                    headers=headers,
                                                    timeout=1200,
                                                    proxies=proxies)
                
                validation_code =  validation_response.status_code
                validation_response = json.loads(validation_response.text)

                if validation_code in [200, 201, 202] and validation_response['status'] in [200, 201, 202]:

                    if 'info' not in validation_response.keys() or 'error_list' not in validation_response['info'].keys() or len(validation_response['info']['error_list']) == 0:
                        modelling_response = requests.post(url,
                                                           json={'body': zipped_body,
                                                                 'skip_validation': True},
                                                           headers=headers,
                                                           timeout=1200,
                                                           proxies=proxies) 
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
                    date_variable: str,
                    date_format: str,
                    model_spec: dict,
                    project_name: str,
                    **kwargs):
    '''
    This function directs the _build_call function to the validation API
     Args:
        data_list: dictionary of pandas datataframes and their respective keys to be sent to the API
        date_variable: name of the variable to be considered as the timesteps
        date_format: format of date_variable following datetime notation
                    (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
        model_spec: dictionary containing arguments required by the API
        project_name: name of the project defined by the user, that should be at most 50 characters long
        skip_validation: if the validation step should be bypassed

    Returns:
        If successfully received, returns the API's return code and email address to which the results
        will be sent. If failed, return API's return code.
    '''
    if any([x not in ['skip_validation', 'version_check',
                      'proxy_url', 'proxy_port'] for x in list(kwargs.keys())]):
        unexpected = list(kwargs.keys())
        for arg in ['skip_validation', 'version_check',
                    'proxy_url', 'proxy_port']:
            if arg in list(kwargs.keys()):
                unexpected.remove(arg)

        raise TypeError(f'validate_models() got an unexpected keyword argument: {", ".join(unexpected)}')
    skip_validation = False
    version_check = True
    proxy_url = None
    proxy_port = None

    if 'skip_validation' in kwargs:
        skip_validation = kwargs['skip_validation']

    if 'version_check' in kwargs:
        version_check = kwargs['version_check']

    if 'proxy_url' in kwargs:
        proxy_url = kwargs['proxy_url']

    if 'proxy_port' in kwargs:
        proxy_port = kwargs['proxy_port']

    req = _build_call(data_list, date_variable,
                      date_format, model_spec,
                      project_name, skip_validation,
                      version_check, 'validate',
                      proxy_url, proxy_port)
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
                        f'{error_field}\n - {error_description["status"]} {error_description["error_type"]}. Original Value: {error_description["original_value"]} in dataset: {error_description["dataset_error"]}'
                    )

        if "warning_list" in api_response["info"].keys() and isinstance(
            api_response["info"]["warning_list"], dict
        ):
            print("\nWarning User Input:\n")
            warning_list = api_response["info"]["warning_list"]

            for warning_place in warning_list.keys():
                print(f"*{warning_place}*")
                warning_description = warning_list[warning_place]
                print(f'{warning_description["status"]} {warning_description["error_type"]}. Original Value: {warning_description["original_value"]} in dataset: {warning_description["dataset_error"]}\n')



def run_models(data_list: Dict[str, pd.DataFrame],
               date_variable: str,
               date_format: str,
               model_spec: dict,
               project_name: str,
               **kwargs) -> str:
    '''

    This function directs the _build_call function to the modeling API
     Args:
        data_list: dictionary of pandas datataframes and their respective keys to be sent to the API
        date_variable: name of the variable to be considered as the timesteps
        date_format: format of date_variable following datetime notation
                    (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
        model_spec: dictionary containing arguments required by the API
        project_name: name of the project defined by the user, that should be at most 50 characters long
        skip_validation: if the validation step should be bypassed

    Returns:
        If successfully received, returns the API's return code and email address to which the results
        will be sent. If failed, return API's return code.
    '''
    
    if any([x not in ['skip_validation', 'version_check',
                      'proxy_url', 'proxy_port'] for x in list(kwargs.keys())]):
        unexpected = list(kwargs.keys())
        for arg in ['skip_validation', 'version_check',
                    'proxy_url', 'proxy_port']:
            if arg in list(kwargs.keys()):
                unexpected.remove(arg)

        raise TypeError(f'run_models() got an unexpected keyword argument: {", ".join(unexpected)}')
    
    skip_validation = False
    version_check = True
    proxy_url = None
    proxy_port = None

    if 'skip_validation' in kwargs:
        skip_validation = kwargs['skip_validation']
    
    if 'version_check' in kwargs:
        version_check = kwargs['version_check']

    if 'proxy_url' in kwargs:
        proxy_url = kwargs['proxy_url']

    if 'proxy_port' in kwargs:
        proxy_port = kwargs['proxy_port']

    req = _build_call(data_list, date_variable, 
                      date_format, model_spec,
                      project_name, skip_validation,
                      version_check, 'projects',
                      proxy_url, proxy_port)
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
                            f'{error_field}\n - {error_description["status"]} {error_description["error_type"]}. Original Value: {error_description["original_value"]} in dataset: {error_description["dataset_error"]}'
                        )

            if "warning_list" in api_response_validation["info"].keys() and isinstance(
                api_response_validation["info"]["warning_list"], dict
            ):
                print("\nWarning User Input:\n")
                warning_list = api_response_validation["info"]["warning_list"]

                for warning_place in warning_list.keys():
                    print(f"*{warning_place}*")
                    warning_description = warning_list[warning_place]
                    print(f'{warning_description["status"]} {warning_description["error_type"]}. Original Value: {warning_description["original_value"]} in dataset: {warning_description["dataset_error"]}\n')

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
