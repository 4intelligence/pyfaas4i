PyFaaS4i - FaaS API modeling with Python
================

![Python](https://img.shields.io/badge/python-3.6|3.7|3.8|3.9-blue.svg) ![License: MPL
2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)

<style>
  r {background-color: #ff0000fa}
</style>

**Repository for running scale modeling on FaaS from Python**


Repository under license [Mozilla Public
Version 2.0](https://www.mozilla.org/en-US/MPL/2.0/).

The script ‘run\_examples.ipynb’ has all the necessary code to run both
examples covered in the tutorial below.

It is presented one case example for modeling one target variable (Y),
using one dataset, and another one with multiple target variables (Y),
which uses a list of datasets.

## Autentication

Each user will need to setup the authentication using the **login** function (*pyfaas4i.faas.login*). The function login will display a URI where 4CastHub's user email and password will be required, as well as the two-factor-authentication code.
```python
from pyfaas4i.faas import login
login()
```
By default, the login function will wait 90 seconds for authentication. If you wish to adjust the wait time, it is possible to change the parameter using a numeric value for **sleep_time**.

## I) How it works

The package is supported by **Python 3** and requires the following packages:

* numpy
* pandas
* requests
* unidecode


Then the package can be installed either by cloning the repository and executing the following command whist in the folder:
```bash
python setup.py install --user
# You might need to change to python3 depending on your configurations
# Linux and Mac users might need to use 'sudo' in the beginning of the command
```
Simply install it using pip:

```python
pip install git+https://github.com/4intelligence/pyfaas4i.git
```

#### Reading Excel files (.xlsx)
Note that an additional package is needed for reading .xlsx files, the **openpyxl** package. It can be installed with one following:

* Installing in an Anaconda environment:
```bash
conda install -c anaconda openpyxl 
```

* Installing using PIP:
```bash
pip install openpyxl
```

* Inside a Jupyter Notebook:
```bash
!pip install openpyxl
```
The package is required only if you are reading .xlsx files or want to follow the tutorial.

## Documentation

Documentation regarding all functions and classes in the package can be found in [docs](docs) folder.


Further examples for sending a project for modeling can be seen [here](run_example.ipynb) and once outputs are available, [here](forecastpack_example.ipynb) you can see how to open the forecast pack using PyFaaS4i.

## Example: Using PyFaaS4i to send a job


Now let's load the function:

``` python
from pyfaas4i.faas import run_models
```

There are some **arguments** to feed ‘run\_models’ function.We are
going through all of them in this example and then will call the API.

#### 1\) Data List \[‘data\_list’\]

A list of datasets to perform modeling;

Since we are dealing with time-series, the dataset *must contain a date
column* (its name is not relevant, since we will automatically detect
it).

Here lie two major conventions to follow:

1)  There must be a date column in the data frame
2)  You must name every dictionary key after the Y variable name

Variables names (column names) that begin with numeric characters will
be renamed to avoid computational issues. For example, variables “32”,
“156\_y”, “3\_pim” will be displayed as “x32”, “x156\_y” and “x3\_pim”
at the end of the process. To avoid this correction, avoid beginning
columns names with numeric characters;

Let us see two examples of data list, one with 1 Y’s and the other with
multiple Y’s <br>

##### Example 1 data\_list \[single Y\]:

``` python

import pandas as pd

# ------ Load dataset -----------------------------------
dataset_1 = pd.read_excel("./inputs/dataset_1.xlsx")

# ------ Declare the date variable and its format --------
date_variable = 'data_tidy'
date_format = '%Y-%m-%d'

# ------ Dataframes must be passed in a dictionary
data_list = {'fs_pim': dataset_1}
```

<br>

##### Example 2 data\_list \[multiple Ys\]:

``` python
# ------ Load datasets -----------------------------------

dataset_1 = pd.read_excel("./inputs/dataset_1.xlsx")
dataset_2 = pd.read_excel("./inputs/dataset_2.xlsx")
dataset_3 = pd.read_excel("./inputs/dataset_3.xlsx")


# ------ Declare the date variable and its format --------

date_variable = 'data_tidy'
date_format = '%Y-%m-%d'

# ------ Dataframes must be passed in a dictionary
data_list = {'dataset_1': dataset_1,
             'dataset_2': dataset_2,
             'dataset_3': dataset_3}
```

<br>



#### 2\) Date Variable \[date\_variable\]

The variable that has the dates to be used by the models.
```python
# The name of the columns which contains the dates
date_variable = 'DATE_VARIABLE'
```


#### 3\) Date Format \[date\_format'\]

Which is the format that the date is represented (p.e 1993-05-06 would be %Y-%m-%d)
For reference see: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

```python
date_format = '%Y-%m-%d'
```


#### 4\) **Model Specifications \[‘model\_spec’\]**

Regardless of whether you are modeling one or multiple Ys, the model
spec follows the same logic. A list of desired modeling specification by
the user:

  - **n\_steps**: forecast horizon that will be used in the
    cross-validation (if 3, 3 months ahead; if 12, 12 months ahead,
    etc.);

    - n_steps should be an integer greater than or equal to 1. It is recommended that 'n_steps+n_windows-1' does not exceed 30% of the length of your data.

  - **n\_windows**: how many windows the size of ‘Forecast Horizon’ will
    be evaluated during cross-validation (CV);

    - n_windows should be an integer greater than or equal to 1. It is recommended that 'n_steps+n_windows-1' does not exceed 30% of the length of your data.

  - **seas.d**: if TRUE, it includes seasonal dummies in every
    estimation;

    - Can be set to True or False.

  - **log**: if TRUE apply log transformation to the data (only variables with all values greater than 0 will be log transformed);

    - Can be set to True or False.


  - **accuracy\_crit**: which criterion to measure the accuracy of the
    forecast during the Cross-Validation;

    - Can be set to MPE, MAPE, WMAPE or RMSE.

  - **exclusions**: restrictions on features in the same model (which variables should not be included in the same model);

    - If none, should be passed as an empty list ("exclusions": [] or "exclusions": list()), otherwise it should receive a list containing lists of variables (see advanced options below for examples).


  - **golden_variables**: features that must be included in, at least, one model (separate or together);
    - If none, should be passed as an empty list ("golden_variables": [] or "golden_variables": list()), otherwise it should receive a list with the golden variables (see advanced options below for examples)

  - **fill_forecast**: if True, it enables forecasting explanatory variables in order to avoid NAs in future values;
    - Can be set to True or False.

  - **cv_summary**: determines whether ‘mean’ ou ‘median’ will be used to calculate the summary statistic of the accuracy measure over the CV windows.
    - Can be set to 'mean' or 'median'.
  
  - **lags**: defines dictionary of lags of explanatory variables to be tested in dataset. For example, if you wish to apply lags 1, 2 and 3 to the explanatory variables 'x1' and 'x2' from your dataset, this parameter should be specified as "lags": {"x1": [1,2,3], "x2": [1,2,3]}. If you wish to test lags 1, 2 and 3 for all explanatory variables in the dataset(s), you can define as "lags": {"all": [1,2,3]}. If the user defines "lags": {"all": [1,2,3], "x1": [1,2,3,4,5,6]}, lags 1, 2 and 3 will be applied to all explanatory variables, except for 'x1', which lags 1 through 6 will be tested. 
    - The default is an empty dictionary ("lags": {}).

  - **allowdrift**: if True, drift terms are considered in arima models;

    - Can be set to True or False.

  - **allowoutliers**: if True, the inclusion of outlier variables in models is allowed;

    - Can be set to True or False.

<br>

The critical input we expect from users is the CV settings (n\_steps and
n\_windows). In this example, we set our modeling algorithm to perform a
CV, which will evaluate forecasts 3 steps ahead (‘n\_steps’), 12 times
(‘n\_windows’).


``` python
## EXAMPLE 1
model_spec = {
              'n_steps': 3,
              'n_windows': 6,
              }
```

If the user chooses not to specify the remaining parameters in the model_spec, we will use the default settings (see below). With the default settings we’ll log transform the data and use proper seasonal dummies in every estimation. The accuracy criteria used to select the best models will be 'MAPE', and they will be summarized using the 'mean' across the CV windows. Missing in explanatory variables in the future values will not be filled, and we will use all three feature selection methods available - Lasso, Random Forest and Correlation, while avoiding collinearity among explanatory variables in a model.

``` python
## Default settings
model_spec = {
              'n_steps': user_input,
              'n_windows': user_input,
              'log': True,
              'seas.d': True,
              'n_best': 20,
              'accuracy_crit': 'MAPE',
              'exclusions': [],
              'golden_variables': [],
              'fill_forecast': False,
              'cv_summary': 'mean',
              'selection_methods': {
                  'lasso' : True,
                  'rf' : True,
                  'corr' : True,
                  'apply.collinear' : ["corr","rf","lasso","no_reduction"]
                  },
              'lags': {},
              'allowdrift': True,
              'allowoutliers': True
              }
```

<br>


#### 5\) Project Name \[‘project\_name’\]

Define a project name. A string with character and/or numeric inputs that should be at most 50 characters long. Special
characters will be removed.

``` python
project_name = 'project_example'
```

#### 6\) User model \['user\_model'\]

The definition of a model (or more than one) that user wants to see among the ARIMA models available in the plataform. The user can set the variables it wants in the model, the ARIMA order and the variables constraints.  
By default, the `user_model` parameter is an empty dictionary, to define a user model it is necessary to create a dictionary in which the keys are the response variable names and the values are lists of specifications, as described below.  
Each user model may contain the following parameters:
- **vars**: A list with the names of the explanatory variables the user wants in the customized model;
- **order** (Optional): A list with the ARIMA order [p, d, q] of the customized model. Such list should always be of length 3, but the user can define as 'None' the ARIMA terms that should be estimated freely, for example [None, 1, None] indicates that the ARIMA should be differenced, but `p` and `q` are free to be optimized. Users have the flexibility to specify all `p`, `d` and `q`, only `d` (in this case, `p` and `q` should be set to None) or only `p` and `q` (in this case, `d` should be set to None);
- **constraints** (Optional): A dictionary with the variables (as keys) and constraints that the user wish to impose in the coefficients of this model. It is possible to set a specific value or a range of values, for 1 or more variables in **vars**;
  - At least one variable set on `vars` must be free of constraints;
  - It is also possible to add constraints to the intercept, which should be defined as the other variables, matching the name **intercept**;
  - If a constraint such as greater than 0 is needed, it can be defined as [0, inf], similarly, for constraints that are less than 0, the format is [-inf, 0].
```python
# defining an user_model for one Y
user_model = {
  "fs_pim": [
    {
      "vars": ["fs_ici", "fs_pmc", "fs_pop_des"],
      "order": [None, 0, None],
      "constraints": {
        "intercept": [3],
        "fs_ici": [0, float("inf")],
        "fs_pmc": [-1, 1]
      }
    }, # user model 1 for dataset_1
  ]
}

# defining an user_model for multiple Y
user_model = {
  "fs_pim": [
    {
      "vars": ["fs_ici", "fs_pmc", "fs_pop_des"],
      "order": [None, 0, None],
      "constraints": {
        "intercept": [3],
        "fs_ici": [0, float("inf")],
        "fs_pmc": [-1, 1]
      }
    }, # user model 1 for dataset_1
    {
      "vars": ["fs_ici", "fs_pmc"],
      "order": [1, 1, 1],
      "constraints": {
        "fs_ici": [0.5]
      }
    }, # user model 2 for dataset_1
  ],
  "fs_pib": [
    {
      "vars": ["fs_ici", "fs_pim", "fs_pop_ea"],
      "order": [None, None, None],
      "constraints": {
        "intercept": [0],
        "fs_ici": [0, float("inf")],
        "fs_pim": [-1,1]
      }
    }, # user model 1 for dataset_3
  ]
}
```


#### 7\) Send job request

Wants to make sure everything is alright? Though not necessary, you can validate your request beforehand by using the following function:

``` python
validate_models(data_list, date_variable, date_format, model_spec, project_name, user_model)
```

It will return a message indicating your specifications are in order or it will point out to the arguments that need adjustment.

Or you can simply send your **FaaS API** request. We'll take care of running the validate_request and let you know if something needs your attention before we can proceed. If everything is in order, we'll automatically send the request, and you will see a message with the status of your request in your console.

``` python
run_models(data_list, date_variable, date_format, model_spec, project_name, user_model)
```

If everything went fine you should see the following message:


"HTTP 200:
Request successfully received!

Results will soon be available in your Projects module"



## II) Advanced Options

In this section, we change some the default values of the
**model\_spec**. *Only advanced users should edit them: make sure you
understand the implications before changing them.*

The accuracy criteria used to select the best models will be “RMSE”.
We’re not applying log transformation on data. Moreover, we also make
use of the **exclusions** and **golden\_variables** options:

``` python
## EXAMPLE 2
model_spec = {
    'log': False,
    'seas.d': True,
    'n_steps': 3,
    'n_windows': 6,
    'n_best': 20,
    'accuracy_crit': 'RMSE',
    'exclusions': [["fs_massa_real", "fs_rend_medio"],
                  ["fs_pop_ea", "fs_pop_des", "fs_pop_ocu"]],
    'golden_variables': ["fs_pmc", "fs_ici"],
    'fill_forecast': True,
    'cv_summary': 'median',
    'selection_methods': {
                          'lasso' : False,
                          'rf' : True,
                          'corr' : True,
                          'apply.collinear' : []
                         },
    'lags': {"fs_rend_medio": [1,2,3],
             "fs_pmc": [1,2,3]},
    'allowdrift': False,
    'allowoutliers': True
    }
```

<br>

By setting **exclusions** this way, we add the restriction where the
features/variables in a group can not appear together in the same model.
Pay attention to the following lines:

``` python
'exclusions': [["fs_massa_real", "fs_rend_medio"],
              ["fs_pop_ea", "fs_pop_des", "fs_pop_ocu"]]
```

This list implies that we will never see “fs\_massa\_real” and
“fs\_rend\_medio” in the same model. The same is true for the second
restriction group: we will never estimate models that simultaneously
include “fs\_pop\_ea”, with either “fs\_pop\_des” and “fs\_pop\_ocu”,
and so on.

<br>

With the **golden\_variables** argument, we can guarantee that at least
some of best models contain one or both of the ‘golden’ ones:

``` python
'golden_variables': ["fs_pmc", "fs_ici"]
```

<br>

With the **fill_forecast** argument, we forecast explanatory variables in order to avoid NAs in future values. Warning: For most variables a simple univariate ARIMA is used in this process (exception: dummy variables are filled using Random Forest) which may hinder the performance of the dependent variable forecast.


``` python
'fill_forecast': True
```

<br>

Regarding the **cv_summary** argument, should we calculate the summary statistic of the accuracy measures using the mean or the median? The mean is the most usual, however, the median is more robust to outliers and might be a better statistic when you think that the cross validation is affected by extreme situations, such as the Covid-19 pandemic.

``` python
'cv_summary': 'median'
```

<br>


The **selection\_methods** determine feature selection algorithms that
will be used when it comes to big datasets (one with a large number of
explanatory features). More precisely, if the number of features in the
dataset exceeds 14, feature selection methods will reduce
dimensionality, guaranteeing the best results in a much more efficient
way. In this example, we turn off the Lasso method and work only with
Random Forests and the correlation approach.

``` python
'selection_methods': {
                      'lasso' : False,
                      'rf' : True,
                      'corr' : True,
                      'apply.collinear' : []
                      }  
```

<br>

The **lags** defines dictionary of lags of explanatory variables to be tested in dataset, in this example, we are considering lags 1, 2 and 3 for the variables 'fs_rend_medio' and 'fs_pmc'. Such lags will be called 'l1_fs_rend_medio', 'l2_fs_rend_medio', 'l2_fs_rend_medio', 'l1_fs_pmc', 'l2_fs_pmc' and 'l3_fs_pmc', if these names are not already in used within user's dataset.

``` python
'lags': {"fs_rend_medio": [1,2,3],
         "fs_pmc": [1,2,3]}
```

<br>

---




## Other Functionalities

### 1\) List projects

You can retrieve information about your previous jobs using the **list_projects** function:
```python
from pyfaas4i.faas import list_projects

my_projects = list_projects()
```

The function takes the optional argument *return_dict*, which takes True or False (default is false). If true, function will return a dictionary instead of a dataframe.


### 2\) Download forecast pack

The project outputs (forecast pack) can also be downloaded using the **download_zip** function. The function will download a zip file containing the outputs of the selected project. The outputs will be in the **RDS** format (an *R* native format), and can be read using the submodule [pyfaas4i.forecastpack](https://github.com/4intelligence/pyfaas4i/blob/main/docs/forecastpack.md).
```python
from pyfaas4i.faas import download_zip

download_zip(project_id = "project_id",
             path = "path",
             filename = "file_name")
```

To download the outputs, you will need the **project_id** which is an information available in the output of the [list_projects](###list-projects) function. You need to provide the **path** of the directory you want to save the forecast pack and **filename**.
