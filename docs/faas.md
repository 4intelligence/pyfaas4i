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

    Dictionary containing arguments required for modeling. The model specifications will be the same for all datasets in the same project. 
    The model_spec expects the following specifications:

    - n_steps: forecast horizon that will be used in the cross-validation (if 3, 3 months ahead; if 12, 12 months ahead, etc.);
        It should be an integer greater than or equal to 1. Typically, 'n_steps+n_windows-1' should not exceed 30% of the length of your data.

    - n_windows: how many windows the size of ‘Forecast Horizon’ will be evaluated during cross-validation (CV);
        It should be an integer greater than or equal to 1. Typically, 'n_steps+n_windows-1' should not exceed 30% of the length of your data.

    - log (Optional): if True apply log transformation to the data (only variables with all values greater than 0 will be log transformed);
        A logical parameter: True or False (Default: True).

    - seas.d (Optional): if True, it includes seasonal dummies in every estimation;
        A logical parameter: True or False (Default: True).

    - n_best (Optional): number of best models to be chosen for each feature selection method;
        Default is 20.

    - accuracy_crit (Optional): which criterion should be used to measure the accuracy of the forecast during the CV;
        Options: "MPE","MAPE", "WMAPE" or "RMSE" (Default: "MAPE").

    - exclusions (Optional): restrictions on features in the same model (which variables should not be included in the same model);
        Default is '"exclusions": []', otherwise it should receive a list of lists containing the exclusion variables in the list.

    - golden_variables (Optional): features that must be included in, at least, one model (separate or together);
        Default is  '"golden_variables": []', otherwise it should be a list with the golden variables.

    - fill_forecast (Optional): if True, it enables forecasting explanatory variables in order to avoid NAs in future values;
        A logical parameter: True or False (Default is False).

    - cv_summary (Optional): determines whether ‘mean’ ou ‘median’ will be used to calculate the summary statistic of the accuracy measure over the CV windows;
        Options: "mean" or "median" (Default is "mean").

    - selection_methods (Optional): specifies which selection methods should be used for feature selection and whether explanatory variables should be chosen in order to avoid collinearity;
        - lasso: True if our method of feature selection using Lasso should be applied,
        - rf: True if our method of feature selection using Random Forest should be applied,
        - corr: True if our method of feature selection using Pearson correlation filter should be applied,
        - apply.collinear: True if you wish that our feature selection avoids collinearity within the explanatory variables in the models - this is equivalent to setting ["corr","rf","lasso","no_reduction"]. False or "" otherwise.

    - lags (Optional): defines dictionary of lags of explanatory variables to be tested in dataset. For example, if you wish to apply lags 1, 2 and 3 to the explanatory variables 'x1' and 'x2' from your dataset, this parameter should be specified as "lags": {"x1": [1,2,3], "x2": [1,2,3]}. However, if you wish to test lags 1, 2 and 3 for all explanatory variables in the dataset(s), you can define as "lags": {"all": [1,2,3]}. If, for example the user defines "lags": {"all": [1,2,3], "x1": [1,2,3,4,5,6]}, lags 1, 2 and 3 will be applied to all explanatory variables, except for 'x1', which lags 1 through 6 will be tested. The default is "lags": {}.

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

    Dictionary containing arguments required for modeling. The model specifications will be the same for all datasets in the same project. 
    The model_spec expects the following specifications:

    - n_steps: forecast horizon that will be used in the cross-validation (if 3, 3 months ahead; if 12, 12 months ahead, etc.);
        It should be an integer greater than or equal to 1. Typically, 'n_steps+n_windows-1' should not exceed 30% of the length of your data.

    - n_windows: how many windows the size of ‘Forecast Horizon’ will be evaluated during cross-validation (CV);
        It should be an integer greater than or equal to 1. Typically, 'n_steps+n_windows-1' should not exceed 30% of the length of your data.

    - log (Optional): if True apply log transformation to the data (only variables with all values greater than 0 will be log transformed);
        A logical parameter: True or False (Default: True).

    - seas.d (Optional): if True, it includes seasonal dummies in every estimation;
        A logical parameter: True or False (Default: True).

    - n_best (Optional): number of best models to be chosen for each feature selection method;
        Default is 20.

    - accuracy_crit (Optional): which criterion should be used to measure the accuracy of the forecast during the CV;
        Options: "MPE","MAPE", "WMAPE" or "RMSE" (Default: "MAPE").

    - exclusions (Optional): restrictions on features in the same model (which variables should not be included in the same model);
        Default is '"exclusions": []', otherwise it should receive a list of lists containing the exclusion variables in the list.

    - golden_variables (Optional): features that must be included in, at least, one model (separate or together);
        Default is  '"golden_variables": []', otherwise it should be a list with the golden variables.

    - fill_forecast (Optional): if True, it enables forecasting explanatory variables in order to avoid NAs in future values;
        A logical parameter: True or False (Default is False).

    - cv_summary (Optional): determines whether ‘mean’ ou ‘median’ will be used to calculate the summary statistic of the accuracy measure over the CV windows;
        Options: "mean" or "median" (Default is "mean").

    - selection_methods (Optional): specifies which selection methods should be used for feature selection and whether explanatory variables should be chosen in order to avoid collinearity;
        - lasso: True if our method of feature selection using Lasso should be applied,
        - rf: True if our method of feature selection using Random Forest should be applied,
        - corr: True if our method of feature selection using Pearson correlation filter should be applied,
        - apply.collinear: True if you wish that our feature selection avoids collinearity within the explanatory variables in the models - this is equivalent to setting ["corr","rf","lasso","no_reduction"]. False or "" otherwise.

    - lags (Optional): defines dictionary of lags of explanatory variables to be tested in dataset. For example, if you wish to apply lags 1, 2 and 3 to the explanatory variables 'x1' and 'x2' from your dataset, this parameter should be specified as "lags": {"x1": [1,2,3], "x2": [1,2,3]}. However, if you wish to test lags 1, 2 and 3 for all explanatory variables in the dataset(s), you can define as "lags": {"all": [1,2,3]}. If, for example the user defines "lags": {"all": [1,2,3], "x1": [1,2,3,4,5,6]}, lags 1, 2 and 3 will be applied to all explanatory variables, except for 'x1', which lags 1 through 6 will be tested. The default is "lags": {}.
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
