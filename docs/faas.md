# Modelling Calls

## faas.validate_models()
**function <span style="color:orange">validate_models</span>.(data_list, date_variable, date_format, model_spec, project_name)**

Sends a request to 4intelligence's Forecast as a Service (FaaS) validation API.

**Parameters**:

- **data_list: Dict[str, pd.Dataframe]:**

    Dictionary of pandas datataframes and their respective keys to be sent to the API
- **date_variable: str**

    Name of the variable to be considered as the timesteps
- **date_format: str** 

    Format of date_variable following datetime notation (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) 
- **model_spec: dict** 

    Dictionary containing arguments required by the API
- **project_name: str**

    Name of the project defined by the user

**Returns**: 
    API return code, and errors and/or warnings if any were found.



## faas.run_models()
**function <span style="color:orange">run_models</span>.(data_list, date_variable, date_format, model_spec, project_name, skip_validation= False)**

Sends a request to 4intelligence's Forecast as a Service (FaaS) for modeling.

**Parameters**

- **data_list: Dict[str, pd.Dataframe]:**

    Dictionary of pandas datataframes and their respective keys to be sent to the API
- **date_variable: str**
    Name of the variable to be considered as the timesteps
- **date_format: str** 

    Format of date_variable following datetime notation (See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) 
    
- **model_spec: dict** 

    Dictionary containing arguments required by the API
- **project_name: str**

    Name of the project defined by the user

- **skip_validation: bool**

    If the validation step should be bypassed

**Returns**: 
    API return code, and errors and/or warnings if any were found.


**Examples**

---

For examples of usage, refer to this [notebook](https://github.com/4intelligence/pyfaas4i/blob/main/run_example.ipynb).

# Utility Functions


## faas.download_zip()
**function <span style="color:orange">download_zip</span>.(project_name, path, filename, verbose)**

Makes a request and downloads all files from a project created in FaaS Modelling or Model Update.

**Parameters**

- **project_name: str:**

    id of the project to be downloaded - must have been concluded
- **path: str**

    Folder to which the files will be downloaded
- **filename: str:**

    name of the zipped file (without the .zip extension)
- **verbose: bool**
    If the message indicating the path for the downaloaded file is to be printed

**Returns**: 
    The API response



## faas.list_projects()
**function <span style="color:orange">list_projects</span>.(return_dict)**

Retrieves a list of projects previously sent to be modelled or updated in FaaS from the user.

**Parameters**

- **return_dict: str**

    If a dictionary should be returned instead of a dataframe

**Returns**: 
    A dataframe or dictionary containing information about the user's projects