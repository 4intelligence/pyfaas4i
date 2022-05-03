import json
from pyfaas4i import R_tools
import numpy as np
import pandas as pd
import os
import subprocess


class forecast:
    """
    Class defined to store information from the 4intelligence forecast pack.

    The class does not take initial parameters, but requires a forecastpack in a json file to be read using the .from_json() method.

    Each information from the forecastpack can be called as a property of the forecast() class and is presented either as a dictionary or a pandas dataframe

    Example:
    ::
    >>> from pyfaas4i.forecastpack import forecast

    >>> # Setting a path to your provided forecast pack
    >>> path = "path to your JSON"

    >>> # Initializing the class and calling the .from_json() method
    >>> example = forecast()
    >>> example.from_json(path = path)

    >>> # The forecasted values
    >>> forecast_table = example.forecast

    >>> # Note that the default forecasts are shown for the best model
    >>> # acconding to the criteria defined in the FaaS input.
    >>> # To see all the models call

    >>> model_list = example.model_list()

    >>> # An overview can be called using the describe() method

    >>> summary_table = example.describe()

    >>> # Setting the third model as an example (index starts at 0)

    >>> example.set_model(2)

    >>> # the properties are now based on the third model
    >>> forecast_third = example.forecast

    """

    def __init__(self):
        """
        Creates a forecast() object.
        """
        self.json = None
        self.type = None
        self.sample = None
        self.transformation = None
        self.RMSE = None
        self.RMSE_list = None
        self.MPE = None
        self.MPE_list = None
        self.MAPE = None
        self.MAPE_list = None
        self.WMAPE = None
        self.WMAPE_list = None
        self.models = None
        self.infos = None
        self.data = None
        self.data_proj = None
        self.forecast = None
        self.model = None
        self._model = 0

    def _refresh(self, simplify: bool = True):
        """
        Updates the forecast() properties to match with new chosen model

        Args:
            simplify: If the forecast property will receive a simplified version of the original table or the whole data. (Default = True)

        Raises:
            ValueError: if json file was not provided
        """

        if not self.json:

            raise ValueError(
                "JSON source not found, specify a forecastpack using .from_json() or .from_rds()"
            )

        else:

            pack = self.json
            self.type = pack[self._model]["type"]
            self.sample = pack[self._model]["sample"]
            self.transformation = pack[self._model]["transformation"]

            for cv_metric in ["RMSE", "MPE", "MAPE"]:
                try:
                    self.__setattr__(cv_metric, pack[self._model][cv_metric])
                except:
                    self.__setattr__(cv_metric, np.NaN)

            self.RMSE_list = pack[self._model]["RMSE_list"]
            self.MPE_list = pack[self._model]["MPE_list"]
            self.MAPE_list = pack[self._model]["MAPE_list"]

            if "WMAPE" in pack[self._model].keys():
                self.WMAPE = pack[self._model]["WMAPE"]
                self.WMAPE_list = pack[self._model]["WMAPE_list"]

            if pack[self._model]["type"] == "ARIMA":
                self.models = dict(
                    (key, pd.DataFrame(pack[self._model]["models"][key]))
                    for key in pack[self._model]["models"].keys()
                )
            elif pack[self._model]["type"] == "RandomForest":
                self.models = pd.DataFrame(pack[self._model]["models"])
            elif pack[self._model]["type"] in ["Lasso", "Ridge", "ElasticNet"]:
                self.models = dict(
                    (key, pd.DataFrame(pack[self._model]["models"][key]))
                    for key in ["bestTune", "coef", "varImp"]
                )
            else:
                self.models = pack[self._model]["models"]

            self.infos = pack[self._model]["infos"]
            self.data = pd.DataFrame(pack[self._model]["data"])
            self.data_proj = pd.DataFrame(pack[self._model]["data_proj"])

            if simplify:
                forecast = pd.DataFrame(pack[self._model]["forecast"])
                self.forecast = forecast[["data_tidy", "y_all", "type"]]
                del forecast
            else:
                self.forecast = pd.DataFrame(pack[self._model]["forecast"])

    def set_model(
        self, model_number: int = 0, simplify: bool = True, verbose: bool = True
    ):
        """
        Changes the model from which the properties will be taken

        Args:
            model_number: index of the model to be used, starting at 0 (default=0)

        Raises:
            Warning: if there is no forecast pack file loaded

        """

        previous_model = self._model

        self._model = model_number

        if self.json:
            self._refresh(simplify=simplify)
            if verbose:
                print(
                    f"Selected model changed from {previous_model} to {model_number}."
                )
        else:
            Warning("You do not have a forecast pack file loaded")

    def from_json(self, path: str, raw: bool = False, simplify: bool = True):
        """
        Fills the forecast() object properties according to data from a forecastpack json file.

        Args:
            path: The path to the forecastpack.json file.
            raw: Boolean variable, to whether the raw json file is desired of if the information should be used in the class. (Default = False)
            simplify: If the forecast property will receive a simplified version of the original table or the whole data. (Default = True)

        Returns:
            if raw is set to True returns a dictionary of the original json file
        """
        with open(path) as json_file:
            pack = json.load(json_file)

        if raw:
            return pack

        else:
            self.json = pack
            self._refresh(simplify=simplify)

    def from_rds(self, path: str, raw: bool = False, simplify: bool = True):
        """
        Fills the forecast() object properties according to data from a forecastpack rds file.

        Args:
            path: The path to the forecastpack.json file.
            raw: Boolean variable, to whether the raw json file is desired of if the information should be used in the class. (Default = False)
            simplify: If the forecast property will receive a simplified version of the original table or the whole data. (Default = True)

        Returns:
            if raw is set to True returns a dictionary of the original json file
        """

        import importlib.resources as pkg_resources

        from subprocess import Popen, PIPE

        proc = Popen(["which", "R"], stdout=PIPE, stderr=PIPE)
        exit_code = proc.wait()
        if exit_code != 0:
            raise SystemError(
                "R is not installed. Install it through 'https://cran.r-project.org/'"
            )

        try:

            with pkg_resources.path(R_tools, "convert_rds.R") as p:
                converter = str(p)

            json_file = subprocess.check_output(["Rscript", converter, path])

            pack = json.loads(json_file)

            if raw:
                return pack

            else:
                self.json = pack
                self._refresh(simplify=simplify)

        except:

            raise SystemError(
                "R and(or) the following packages are not installed: dplyr, jsonlite, lmtest, broom, randomForest, caret"
            )

    @staticmethod
    def readRDS(path: str, raw: bool = False, simplify: bool = True):
        """
        Creates a forecast() object with the properties according to data from a forecastpack rds file.

        Args:
            path: The path to the forecastpack.json file.
            raw: Boolean variable, to whether the raw json file is desired of if the information should be used in the class. (Default = False)
            simplify: If the forecast property will receive a simplified version of the original table or the whole data. (Default = True)

        Returns:
            if raw is set to True returns a dictionary of the original json file
        """
        forecastpack = forecast()
        forecastpack.from_rds(path=path, raw=raw, simplify=simplify)
        return forecastpack

    @staticmethod
    def readJSON(path: str, raw: bool = False, simplify: bool = True):
        """

        Creates a forecast() object with the properties according to data from a forecastpack JSON file.

        Args:
            path: The path to the forecastpack.json file.
            raw: Boolean variable, to whether the raw json file is desired of if the information should be used in the class. (Default = False)
            simplify: If the forecast property will receive a simplified version of the original table or the whole data. (Default = True)

        Returns:
            if raw is set to True returns a dictionary of the original json file
        """
        forecastpack = forecast()
        forecastpack.from_json(path=path, raw=raw, simplify=simplify)
        return forecastpack

    def describe(self, summarise=True) -> pd.DataFrame:
        """
        Creates a summary dataframe with data from all the models inside the forecastpack

        Args:
            summarise: If a simplified and grouped dataframe is returned, else simply returns all models with their metrics

        Returns:
            desc_df: dataframe with model data

        Raises:
            ValueError: if json file was not provided
        """
        if not self.json:
            raise ValueError(
                "JSON source not found, specify a forecastpack using .from_json()"
            )

        else:
            models = [self.json[i]["type"] for i in range(len(self.json))]
            mapes, mpes, rmses = [], [], []
            for i in range(len(self.json)):
                for metrics_list, cv_metrics in [
                    (mapes, "MAPE"),
                    (mpes, "MPE"),
                    (rmses, "RMSE"),
                ]:
                    try:
                        metrics_list.append(self.json[i][cv_metrics])
                    except:
                        metrics_list.append(np.NaN)

            if "WMAPE" in self.json[0].keys():
                wmapes = []
                for i in range(len(self.json)):
                    try:
                        wmapes.append(self.json[i]["WMAPE"])
                    except:
                        wmapes.append(np.NaN)
                desc_df = pd.DataFrame(
                    {
                        "Model Type": models,
                        "MAPE": mapes,
                        "WMAPE": wmapes,
                        "MPE": mpes,
                        "RMSE": rmses,
                    }
                )
            else:
                desc_df = pd.DataFrame(
                    {"Model Type": models, "MAPE": mapes, "MPE": mpes, "RMSE": rmses}
                )

        if summarise:
            desc_df["Model Type"] = desc_df["Model Type"].str.replace(
                "^comb.*", "Forecast Combination", regex=True
            )
            desc_df = desc_df.groupby("Model Type").describe()
            desc_df.index.rename("Metric", inplace=True)
            desc_df = desc_df.loc[
                :,
                desc_df.columns.get_level_values(1).isin(
                    ["count", "min", "max", "mean"]
                ),
            ].T

            return desc_df

        else:
            return desc_df

    def model_list(self, n_best: int = 20, metric: str = None) -> pd.DataFrame:
        """
        Outputs a list with the best models based on informed criteria and number of models desired

        Args:
            n_best: number of models to be returns (Default is 20)
            metric: metric to be used to order the models (Default is 'MAPE')

        Returns:
            m_list: dataframe with model names, types and performance in each metric

        Raises:
            ValueError: if json file was not provided
        """

        if not self.json:
            raise ValueError(
                "JSON source not found, specify a forecastpack using .from_json()"
            )

        else:
            models = [self.json[i]["type"] for i in range(len(self.json))]
            mapes, mpes, rmses = [], [], []
            for i in range(len(self.json)):
                for metrics_list, cv_metrics in [
                    (mapes, "MAPE"),
                    (mpes, "MPE"),
                    (rmses, "RMSE"),
                ]:
                    try:
                        metrics_list.append(self.json[i][cv_metrics])
                    except:
                        metrics_list.append(np.NaN)

            if "WMAPE" in self.json[0].keys():
                wmapes = []
                for i in range(len(self.json)):
                    try:
                        wmapes.append(self.json[i]["WMAPE"])
                    except:
                        wmapes.append(np.NaN)

                m_list = pd.DataFrame(
                    {
                        "Model": [x for x in range(len(self.json))],
                        "Model Type": models,
                        "MAPE": mapes,
                        "WMAPE": wmapes,
                        "MPE": mpes,
                        "RMSE": rmses,
                    }
                )
            else:
                m_list = pd.DataFrame(
                    {
                        "Model": [x for x in range(len(self.json))],
                        "Model Type": models,
                        "MAPE": mapes,
                        "MPE": mpes,
                        "RMSE": rmses,
                    }
                )

            if metric:
                m_list = m_list.sort_values(metric, ascending=True).head(n_best)
            else:
                m_list = m_list.head(n_best)

            return m_list

    def steps_and_windows(self):
        if not self.json:
            raise ValueError(
                "JSON source not found, specify a forecastpack using .from_json()"
            )

        else:
            for i in range(len(self.json)):
                if self.json[i]["type"] == "ARIMA":
                    n_steps = self.json[i]["infos"]["n_steps"][0]
                    n_windows = self.json[i]["infos"]["n_windows"][0]
                    return n_steps, n_windows

            raise AttributeError(
                "No ARIMA models found. Steps and windows could not be retrieved."
            )


def install_R():

    from subprocess import Popen, PIPE

    proc = Popen(["which", "R"], stdout=PIPE, stderr=PIPE)
    exit_code = proc.wait()
    if exit_code != 0:
        raise SystemError(
            "R is not installed. Install it through 'https://cran.r-project.org/'"
        )

    print("Starting installation")

    install_command = "install.packages(c('dplyr', 'jsonlite', 'lmtest', 'broom', 'randomForest', 'caret'))"
    os.system(f"Rscript -e {install_command}")

    print('Packages have been installed')

