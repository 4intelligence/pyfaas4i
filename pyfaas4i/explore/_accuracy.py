from pyfaas4i.forecastpack import forecast
from typing import List
import pandas as pd
import warnings

def compare_packs(packs = List[forecast]) -> pd.DataFrame:
    '''
    Gets comparison of projetions from forecastpacks, the newest treated as the last available value
    
    Args:
     - packs: List of forecast objects

    Returns:
     - comparison: Dataframe with the comparison values from different forecast objects
    '''
    pack_forecast = [x.forecast for x in packs]

    in_sample = [x.loc[x['type'] == 'in_sample'].copy() for x in pack_forecast]

    max_len = max([len(x) for x in in_sample]) # trocar para última data

    orig_data = [x for x in in_sample if len(x) == max_len][0]

    out_sample = [x.loc[x['type'] == 'out_sample'].copy() for x in pack_forecast]

    comparison = orig_data.iloc[:, [0,1]].copy()
    comparison.rename(columns={orig_data.columns[1]: 'real'}, inplace=True)

    for forecast in out_sample:
        tmp_forecast = forecast.iloc[:, [0,1]].copy() # check for duplicates add number
        forecast_date = tmp_forecast.iloc[0, 0]
        tmp_forecast.rename(columns = {tmp_forecast.columns[1] : forecast_date}, inplace=True)
        
        if forecast_date in comparison.columns:
            warnings.warn(f"Forecasts in the list start their projections at the same date ({forecast_date}), some forecasts will not appear in the comparison.", Warning)
        
        comparison = comparison.merge(tmp_forecast, how='left')

    return comparison



def model_accuracy(packs: List[forecast], n_steps: int = 1, cv_summary: str = 'mean', metric: str = 'MAPE') -> dict:
    '''
   Given a list of forecast objects, compares the projections and real values and returns a dict of different comparisons to be plotted

   Args:
    - packs: List of forecast objects
    - n_steps: number of steps per windows, as used inside FaaS
    - cv_summary: 'mean' or 'median' depeding on the option used when modelling. How the window metrics are aggregated.
    - metric: desired metric to be compared

   Returns:
    - plot_comparison: dictionary with different comparisons between forecasts and auxiliary information for plotting
    '''

    lineplot_list = []
    lineplot_dashed = []

    metric_list = [x.__getattribute__(metric) for x in packs]
    forecast_comparison = compare_packs(packs)

    forecast_comparison = forecast_comparison.set_index('data_tidy')

    step_errors = pd.DataFrame(columns=['Step', 'Error', 'Pack Date'])
    pointer = 0
    real_metrics = []
    for column in forecast_comparison.columns:
        
        if forecast_comparison[column].sum() > 0:
        
            lineplot_list.append([forecast_comparison.index, forecast_comparison[column], column])

        if column != 'real': 
            
            if forecast_comparison[column].sum() > 0:
                
                primeiro_valor = forecast_comparison.reset_index()[column].first_valid_index()
                conection = forecast_comparison.index[:(primeiro_valor+1)]
                conection = conection[-2:]
                pred_dates = forecast_comparison.index[(primeiro_valor):]
                erro_pack = abs(forecast_comparison[column][pred_dates] - forecast_comparison['real'][pred_dates]) * 100/forecast_comparison['real'][pred_dates]
                pack_step_errors = pd.DataFrame({'Step': ['Step ' + str(x) for x in range(1, len(pred_dates) + 1)], 'Error': erro_pack})
                pack_step_errors['Pack Date'] = column
                lineplot_dashed.append([conection, [forecast_comparison['real'][conection[0]], forecast_comparison[column][conection[1]]], column])

                step_errors = pd.concat([step_errors, pack_step_errors])
                real_metrics.append(metric_list[pointer])
            
            pointer += 1
 
    
    metric_compare = step_errors[['Error', 'Pack Date']]
    metric_compare['occurence'] = metric_compare.groupby('Pack Date').cumcount()+1
    metric_compare = metric_compare.loc[metric_compare['occurence'] <= n_steps].groupby('Pack Date')['Error'].agg(cv_summary).reset_index()

    metric_compare[f'{metric} -  Cross-Validation'] = real_metrics
    metric_compare.rename(columns={'Error': f'{metric} - Observed'}, inplace=True)
    metric_compare = metric_compare.set_index('Pack Date').stack().reset_index().rename(columns={'level_1': 'Type', 0: metric})


    plot_comparison = {
        'lineplot': lineplot_list, 
        'lineplot_dashed': lineplot_dashed, 
        'metric_step': step_errors, 
        'slope_plot': metric_compare
        }

    return plot_comparison



    
