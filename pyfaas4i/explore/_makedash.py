import glob
from typing import List

from pyfaas4i.forecastpack import forecast
from ._accuracy import model_accuracy
from ._importplotly import _imports

if _imports.is_successful():
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots


def get_dashboard(base_path: List[forecast], target_path: str, metric: str = 'MAPE', cv_summary: str = 'mean', verbose: bool=True):
    '''
    This function saves a HTML dashboard with the comparison between different forecast objects for the same series.

    Args:
     - base_path: folder where the forecastpacks are located (no other file should be in the folder).
     - target_path: where the dashboard should be saved, including file name and html extension.
     - metric: desired metric to be compared.
     - cv_summary: 'mean' or 'median' depeding on the option used when modelling. How the window metrics are aggregated.
     - verbose: whether a message stating the saved path will be saved or not.
    '''

    _imports.check()
    file_list = glob.glob(base_path + '*')
    lista_teste = []

    for i in file_list:
        if i.endswith('.json'):
            temp = forecast.readJSON(i)
        else:
            temp = forecast.readRDS(i)

        lista_teste.append(temp)

    n_steps, _ = temp.steps_and_windows()
    
    plot_dict = model_accuracy(lista_teste, n_steps= n_steps, cv_summary=cv_summary, metric=metric) # TODO: Trocar nome da variavel

    color_list = px.colors.qualitative.Plotly
    pack_names = plot_dict['metric_step']['Pack Date'].drop_duplicates().to_list() + ['real', 'Median error']
    color_dict = dict(zip(pack_names, color_list[:len(pack_names)]))


    dash = make_subplots(rows=2, cols=2, specs = [[{"colspan": 2}, None], [{}, {}]], 
            subplot_titles=('Series Accuracy', 'Model error per step outside original sample', "Error Comparison"))

    for series in plot_dict['lineplot']:
        dash.add_trace(go.Scatter(x=series[0][-8:], y=series[1][-8:], name=series[2], legendgroup=series[2], marker_color = color_dict[series[2]], mode='lines+markers'), row=1, col=1)
    for dashes in plot_dict['lineplot_dashed']:
        dash.add_trace(go.Scatter(x=dashes[0], y=dashes[1], mode='lines', legendgroup=dashes[2], showlegend=False, line={'dash': 'dash', 'color': 'gray'}), row=1, col=1)



    median_agg = plot_dict['metric_step'].groupby('Step')['Error'].median().reset_index()
    for pack_date in plot_dict['metric_step']['Pack Date'].drop_duplicates():
        plot_points = plot_dict['metric_step']
        plot_points = plot_points.loc[plot_points['Pack Date'] == pack_date]
        dash.add_trace(go.Scatter(x=plot_points['Step'], y=plot_points['Error'], mode = 'markers', name = pack_date, marker_color = color_dict[pack_date], legendgroup = pack_date, showlegend=False), row=2, col=1)

        date_slope = plot_dict['slope_plot']
        date_slope = date_slope.loc[date_slope['Pack Date'] == pack_date]
        dash.add_trace(go.Scatter(x=date_slope['Type'], y=date_slope.iloc[:,-1], mode='lines+markers', name = pack_date, marker_color = color_dict[pack_date], legendgroup = pack_date, showlegend=False), row=2, col=2)

    dash.add_trace(go.Scatter(x=median_agg['Step'], y=median_agg['Error'], mode='lines+markers', name='Median error', marker_color = color_dict['Median error']), row=2, col=1)
    
    dash.update_xaxes(categoryorder='array', categoryarray = [f'{metric} -  Cross-Validation', f'{metric} - Observed'], row=2, col=2)
    dash.update_layout(showlegend=True)

        
    dash.update_yaxes(title_text="Series Values", row=1, col=1)
    dash.update_yaxes(title_text=f"{metric}", row=2, col=1)
    dash.update_yaxes(title_text=f"{metric}", row=2, col=2)

    dash.update_xaxes(title_text="Step ahead original sample", row=2, col=1)

    dash.update_layout(title_text="Model Accuracy - Dashboard (Alpha Version)", title_x=0.5)


    dash.write_html(target_path)

    if verbose:
        print(f'Dashboard saved to {target_path}')

