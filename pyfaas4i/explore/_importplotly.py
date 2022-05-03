from packaging import version
from pyfaas4i._checkimports import try_import

# Checks import availability of plotly components
with try_import() as _imports: 
    import plotly 
    from plotly import __version__ as plotly_version
    import plotly.express as px
    import plotly.graph_objs as go 
    from plotly.graph_objs import Scatter 
    from plotly.subplots import make_subplots 

    if version.parse(plotly_version) < version.parse("4.0.0"):
        raise ImportError(
            "Your version of Plotly is " + plotly_version + " . "
            "Please install plotly version 4.0.0 or higher. "
            "Plotly can be installed by executing `$ pip install -U plotly>=4.0.0`. "
            "For further information, please refer to the installation guide of plotly. ",
            name="plotly",
        )