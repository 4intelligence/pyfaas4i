import json
import sys
from logging import warning
import re
from os import path
import importlib.resources as pkg_resources
import pandas as pd
import requests
import warnings
from pathlib import Path
from requests.structures import CaseInsensitiveDict
from configparser import ConfigParser

import pyfaas4i
from pyfaas4i import auth_files
from .services.constants import FOURI_USER_AGENT

configur = ConfigParser()
with pkg_resources.path(auth_files, "config.ini") as ci:
        config_ini = str(ci)

configur.read(ci)

def _check_version():
    '''
    Checks if the local user version is the latest pyfaas4i release
    '''
    uri = 'https://api.github.com/repos/4intelligence/pyfaas4i/releases/latest'
    git_response = requests.get(uri)

    
    if git_response.ok:
        latest_version = git_response.json()["tag_name"]
        latest_version = latest_version.replace('v', '')
        if pyfaas4i.__version__ != latest_version:
            print(f"Warning: There is a newer version of PyFaaS4i ({latest_version}), you currently have version {pyfaas4i.__version__}. \n This may lead to unexpected behavior. Please update you version of PyFaaS4i")
            
            stop_prompt = "Would you like to update it now? (y/n)"
            update_pyfaas4i = '0'
            while update_pyfaas4i not in [True, False]:
                try:
                    update_pkg = input(stop_prompt).lower()
                    update_pyfaas4i = {"y": True, "n": False}[update_pkg]
                except KeyError:
                    print("Invalid input, please enter Y/y for yes or N/n for No.")

            if update_pyfaas4i:
                raise SystemExit("Please run 'pip install --upgrade git+https://github.com/4intelligence/pyfaas4i.git' to get the latest version.")
        return



def _get_access_token() -> str:
    '''
    Get the access_token from the config.json file. Requires the
    user to run the pyfaas4i.faas.login function first to generate the config.json file.

    Returns:
    access_token: auth0 access token generated by the pyfaas4i.faas.login function
    '''

    config_file = pyfaas4i.__path__[0] + "/config.json"

    if path.isfile(config_file):
        with open(config_file, "r") as config_:
            config_json = json.load(config_)
            domain = configur.get("authentication", "domain")
    else:
        raise ValueError("You must be authenticated in order to access the API. \n \
        Make sure you ran the pyfaas4i.faas.login function.")
    try:
        access_token = config_json["auths"][domain]["access_token"]
    except:
        raise ValueError('access_token not found. Make sure to run the pyfaas4i.faas.login function and complete the login.')
    return access_token


def download_zip(
    project_id: str,
    path: str,
    filename: str,
    verbose: bool = True,
    **kwargs
) -> str:
    """
    Downloads all output files from a project in a .zip file

    Args:
        project_id: id of the project to be downloaded
        path: folder to which the files will be downloaded
        filename: name of the zipped file
        verbose: if messages will be printed
    Returns:
        response: API response
    Raises:
        Error: if request is not successfull

    """

    if any([x not in ['check_version'] for x in list(kwargs.keys())]):
        unexpected = list(kwargs.keys())
        for arg in ['check_version']:
            if arg in list(kwargs.keys()):
                unexpected.remove(arg)
        raise TypeError(f'download_zip() got an unexpected keyword argument: {", ".join(unexpected)}')
    
    
    check_version = True

    
    if 'check_version' in kwargs:
        check_version = kwargs['check_version']
    
    # ---- Check for PyFaaS4i latest version
    if check_version:
        _check_version()

    
    regex_filename= re.compile('[@!#$%^&*()<>?/\\|}{~:\[\]]')
    if regex_filename.search(filename):
        raise ValueError("Variable 'filename' must not contain special characters")

    access_token = _get_access_token()
    headers = CaseInsensitiveDict()
    headers["authorization"] = f"Bearer {access_token}"
    headers["user-agent"] = FOURI_USER_AGENT

    try:
        response_check = requests.get(
            url=f"https://run-prod-4casthub-faas-modelling-api-zdfk3g7cpq-ue.a.run.app/api/v1/projects/{project_id}",
            timeout=1200,
            headers=headers,
        )
    except Exception as e:
        print(f"Error: {e}")

    
    if not response_check.ok:

        if response_check.status_code == 401:
            raise AuthenticationError()

        elif response_check.status_code == 403:
            raise ForbiddenError()

        elif response_check.status_code == 503:
            raise APIError(f"Status code: {str(response_check.status_code)} \
            \nContent: Service Unavailable\nPlease try again later")
        else:
            raise APIError(f"Status code: {str(response_check.status_code)} \
                \nAPI Error: An error occurred when trying to retrieve the requested information. \
                \nPlease try again later.")
    else:    
        check_content = json.loads(response_check.text)
        if check_content['status'] == "error":
            raise ModelingError("There was an error while running your job.")
        
        elif check_content['status'] == "excluded":
            raise ModelingError("The project with this project_id has been excluded.")
        
        elif check_content['status'] == "partial_success":
            warnings.warn("At least one of the outputs from this request is not yet ready, downloading available files.")

        elif check_content['status'] != "success":
            print(f"Your request is still being processed, with the following status: {check_content['status']}")
            return check_content['status']
    
    Path(path).mkdir(parents=True, exist_ok=True)

    with open(Path(f"{path}/forecast-{filename}.zip"), "wb+") as fi:
        try:
            response = requests.get(
                url=f"https://run-prod-4casthub-faas-modelling-api-zdfk3g7cpq-ue.a.run.app/api/v1/projects/{project_id}/download",
                timeout=1200,
                headers=headers,
                stream=True,
            )
        except Exception as e:
            print(f"Error: {e}")
        for chunk in response.iter_content(32 * 1024):
            fi.write(chunk)
        if verbose:
            print(f"File downloaded to {path}/forecast-{filename}.zip")

    if response.status_code == 500:
        raise APIError('Status Code: 500 - Error downloading file \nCheck your internet connection and try again.')

    return response.status_code


def list_projects(return_dict: bool = False, **kwargs):
    """
    Retrieves a list of projects previously sent to FaaS that belongs to the user

    Args:
        return_dict: if a dictionary should be returned instead of a dataframe
    Returns:
        project_dict: dataframe or dictionary with information regarding the user projects
    """

    if any([x not in ['check_version'] for x in list(kwargs.keys())]):
        unexpected = list(kwargs.keys())
        for arg in ['check_version']:
            if arg in list(kwargs.keys()):
                unexpected.remove(arg)
        raise TypeError(f'list_projects() got an unexpected keyword argument: {", ".join(unexpected)}')
    
    
    check_version = True

    
    if 'check_version' in kwargs:
        check_version = kwargs['check_version']
    
    # ---- Check for PyFaaS4i latest version
    if check_version:
        _check_version()


    access_token = _get_access_token()
    headers = CaseInsensitiveDict()

    headers["authorization"] = f"Bearer {access_token}"
    headers["user-agent"] = FOURI_USER_AGENT
    
    try:
        response = requests.get(
            url="https://run-prod-4casthub-faas-modelling-api-zdfk3g7cpq-ue.a.run.app/api/v1/projects",
            timeout=1200,
            headers=headers,
        )
    except Exception as e:
        print(f"Error: {e}")

    if response.status_code == 401:
        raise AuthenticationError()

    project_dict = json.loads(response.text)["records"]
    if return_dict:
        return project_dict
    else:
        return pd.DataFrame(project_dict)



class APIError(Exception):
    '''
    Inherits from generic exception to be used in cases where there's an error in any API
    '''
    pass

class ModelingError(Exception):
    '''
    Inherits from generic exception to be used in cases where there's an error in any modeling matter
    '''
    pass

class AuthenticationError(Exception):
    '''
    Inherits from generic exception to be used in cases where there's an error in any authentication matter
    ''' 
    def __init__(self, msg="Status Code: 401. Content: Expired Authentication.\nPlease run 'pyfaas4i.faas.login()' again.", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class ForbiddenError(Exception):
    '''
    Inherits from generic exception to be used in cases where there's an error in any forbidden matter
    ''' 
    def __init__(self, msg="Status Code: 403. Content: You don't have access rights to this content.", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
