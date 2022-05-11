
import os
import requests
import time
import json
import sys

import importlib.resources as pkg_resources
from configparser import ConfigParser
from urllib.parse import urlencode

import pyfaas4i 
from pyfaas4i import auth_files
from .constants import AUTH0_DEVICE_CODE_URL, AUTH0_TOKEN_REQUEST_URL, FOURI_USER_AGENT



CONFIG = ConfigParser()

with pkg_resources.path(auth_files, "config.ini") as ci:
        config_ini = str(ci)

CONFIG.read(os.getenv("CONFIG_INI", config_ini))

DOMAIN = CONFIG.get("authentication", "domain")
CLIENT_ID = CONFIG.get("authentication", "client_id")
SCHEME = "https://"
AUDIENCE = CONFIG.get("authentication", "audience")
TIMEOUT = 10
TOKEN_ETA = 90
HTTP_403 = 403


def get_device_code():
    '''
    Performs the login flow to allow a user to utilise the APIs from the 4casthub 
    environment.
    '''
    url = f"{SCHEME}{DOMAIN}{AUTH0_DEVICE_CODE_URL}"
    scope = "offline_access openid profile email"
    payload = urlencode({"client_id": CLIENT_ID, "scope": scope, "audience": AUDIENCE})
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "User-Agent": FOURI_USER_AGENT,
    }
    
    response = requests.post(url, data=payload, headers=headers, timeout=TIMEOUT)
    if response.ok:
        print(
            "Please copy and paste the URL bellow on the browser to authorize your device"
        )
        verification_uri_complete = response.json()["verification_uri_complete"]
        print(f"Device verification URI: {verification_uri_complete}")
        print("Waiting for URI authentication... (This process may take up to 90 seconds)")
        _write_config_file(response.json())
        _request_token(response.json())
    return


def _request_token(device_code_response):
    '''
    This function accesses the auth0 API with a device code
    and gets the access token.
    Args:
        device_code_response: JSON provided by the auth0 device login API
    '''
    url = f"{SCHEME}{DOMAIN}{AUTH0_TOKEN_REQUEST_URL}"
    device_code = device_code_response["device_code"]

    payload = urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": CLIENT_ID,
        }
    )

    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "User-Agent": FOURI_USER_AGENT,
    }



    # DEPRECATED CODE: progress bar

    # toolbar_width = TOKEN_ETA

    # # setup toolbar
    # sys.stdout.write("[%s]" % (" " * 1))
    # sys.stdout.flush()
    # sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

    # for _ in range(toolbar_width):
    #     time.sleep(1) 
    #     sys.stdout.write("=")
    #     sys.stdout.flush()

    # sys.stdout.write("]\n")
    time.sleep(90)

    response = requests.post(url, data=payload, headers=headers, timeout=TIMEOUT)
    if response.ok:
        print("Login successful!")
        _append_config_file(response.json())
        
    elif response.status_code == HTTP_403:
        print("ERROR: Login unsuccessful!")
        error_message = response.json()["error"]
        print(_get_error_feedback(error_message))

    return


def refresh_token():
    # TODO Get a brand new token to call 4i API
    # we must implement a new route on our API to avoid the disclojure of our auth0 client_secret
    raise NotImplementedError


def _write_config_file(json_) -> None:
    '''
    Writes config.json initial version
    Args:
        json_: JSON provided by the auth0 device login API
    '''
    with open(pyfaas4i.__path__[0] + "/config.json", "w") as config_:
        config_dict = {"auths": {DOMAIN: json_}}
        json.dump(config_dict, config_, indent=4)
    return


def _append_config_file(json_, filename= pyfaas4i.__path__[0] + "/config.json") -> None:
    '''
    Appends authentication info to the config.json file
    Args:
    json_: JSON provided by the auth0 authentication API
    filename: Path to the initial config.json file
    '''
    
    with open(filename, "r+") as config_:
        file_data = json.load(config_)
        file_data["auths"][DOMAIN].update(json_)
        config_.seek(0)
        json.dump(file_data, config_, indent=4)
    return


def _get_error_feedback(error_message):
    '''
    Gets appropriate error message depending on the reponse from the API
    Args:
        error_message: name of the error returned by the API
    Returns:
        error_feedback: Error message respective to the response from the API.
    '''
    errors = {
        "authorization_pending": {
            "message": "User has yet to authorize device code. Please restart the login flow running the 'pyfaas4i.faas.login' command"
        }
    }
    # error message will be only "authorization_pending" for the time being
    if error_message in errors:
        error_feedback =  errors[error_message]["message"]
    else:
        error_feedback = "Unexpected error has occured. Please restart the login flow running the 'pyfaas4i.faas.login' command"
    return error_feedback
