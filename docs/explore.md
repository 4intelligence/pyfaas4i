# Explore submodule
Tools to explore the forecastpacks

## explore.compare packs()
**function <span style="color:orange">compare_packs</span>(packs)**

Gets comparison of projetions from forecastpacks, the newest treated as the last available value
    

**Parameters**:

- **packs: List[forecast]**
    List of forecast objects

**Returns**: 
    Dataframe with the comparison values from different forecast objects.

### **Examples**
```python
import glob
from pyfaas4i.forecastpack import forecast
# Reading from rds files
rds_list = glob.glob('./*.rds')
forecast_list = [forecast.readRDS(x) for x in rds_list]
comparison = compare_packs(forecast_list)
```

---

## explore.model_accuracy()
**function <span style="color:orange">model_accuracy</span>(packs, n_steps, cv_summary, metric)**

Given a list of forecast forecast objects, compares the projections and real values and returns a dict of different comparisons to be plotted.


**Parameters**

- **packs: List[forecast]**
    List of forecast objects

- **n_steps: int, *default* 1**
    number of steps per windows, as used inside FaaS

- **cv_summary: str, *default* 'mean'** 
    'mean' or 'median' depeding on the option used when modelling. How the window metrics are aggregated.
    
- **metric: str, *default* 'MAPE'** 
    desired metric to be compared

**Returns**: 
    dictionary with different comparisons between forecasts and auxiliary information for plotting.


### **Examples**

```python
import glob
from pyfaas4i.forecastpack import forecast
# Reading from rds files
rds_list = glob.glob('./*.rds')
forecast_list = [forecast.readRDS(x) for x in rds_list]
comparison = model_accuracy(packs=forecast_list, n_steps=1, cv_summary='mean', metric='MAPE')
```

---

## explore.get_dashboard()
**function <span style="color:orange">get_dashboard</span>(base_path, target_path:, metric, cv_summary, verbose)**

This function saves a HTML dashboard with the comparison between different forecast objects for the same series.
It requires the optional package [**plotly**](https://plotly.com/) to be used.


**Parameters**

- **base_path: str**
    folder where the forecastpacks are located (no other file should be in the folder).

- **target_path: str**
    where the dashboard should be saved, including file name and html extension.

    
- **metric: str, *default* 'MAPE'** 
    desired metric to be compared

- **cv_summary: str, *default* 'mean'** 
    'mean' or 'median' depeding on the option used when modelling. How the window metrics are aggregated.

- **verbose: bool, *default* True** 
    whether a message stating the saved path will be saved or not.

```python
# folder where forecastpack files are
base_path = './example_inputs/' 
# desired path and name of the HTML file
target_path = './example_dashboard.html'
 
get_dashboard(base_path, target_path, metric='WMAPE')
```
