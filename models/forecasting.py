import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class ForecastingModel:
    """
    Time series forecasting models for technology demand prediction.
    Implements Prophet and ARIMA models with validation and metrics.
    """
    
    def __init__(self, model_type: str = 'prophet'):
        """
        Initialize forecasting model.
        
        Args:
            model_type: Type of model ('prophet' or 'arima')
        """
        self.model_type = model_type
        self.model = None
        self.fitted = False
        self.metrics = {}
        
    def prepare_data(self, data: pd.DataFrame,
                    date_col: str = 'date',
                    value_col: str = 'value') -> pd.DataFrame:
        """
        Prepare data for forecasting.
        
        Args:
            data: Input dataframe
            date_col: Name of date column
            value_col: Name of value column
            
        Returns:
            Prepared dataframe
        """
        df = data.copy()
        
        # Ensure datetime
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Sort by date
        df = df.sort_values(date_col)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=[date_col])
        
        # Handle missing values
        df[value_col] = df[value_col].fillna(method='ffill').fillna(0)
        
        logger.info(f"Prepared {len(df)} records for forecasting")
        return df
        
    def fit_prophet(self, data: pd.DataFrame,
                   seasonality_mode: str = 'multiplicative',
                   yearly_seasonality: bool = True,
                   weekly_seasonality: bool = True) -> None:
        """
        Fit Prophet model.
        
        Args:
            data: Training data with 'ds' and 'y' columns
            seasonality_mode: 'additive' or 'multiplicative'
            yearly_seasonality: Include yearly seasonality
            weekly_seasonality: Include weekly seasonality
        """
        logger.info("Fitting Prophet model...")
        
        # Initialize Prophet
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=False
        )
        
        # Fit model
        self.model.fit(data)
        self.fitted = True
        
        logger.info("Prophet model fitted successfully")
        
    def fit_arima(self, data: pd.Series,
                 order: Tuple[int, int, int] = (1, 1, 1)) -> None:
        """
        Fit ARIMA model.
        
        Args:
            data: Time series data
            order: ARIMA order (p, d, q)
        """
        logger.info(f"Fitting ARIMA{order} model...")
        
        # Initialize and fit ARIMA
        self.model = ARIMA(data, order=order)
        self.model = self.model.fit()
        self.fitted = True
        
        logger.info("ARIMA model fitted successfully")
        
    def predict_prophet(self, periods: int = 30,
                       freq: str = 'D') -> pd.DataFrame:
        """
        Make predictions using Prophet.
        
        Args:
            periods: Number of periods to forecast
            freq: Frequency ('D' for daily, 'W' for weekly, 'M' for monthly)
            
        Returns:
            Dataframe with predictions
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
            
        # Create future dataframe
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        
        # Generate forecast
        forecast = self.model.predict(future)
        
        logger.info(f"Generated {periods} period forecast")
        return forecast
        
    def predict_arima(self, steps: int = 30) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions using ARIMA.
        
        Args:
            steps: Number of steps to forecast
            
        Returns:
            Tuple of (predictions, confidence intervals)
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
            
        # Generate forecast
        forecast_result = self.model.forecast(steps=steps)
        forecast = forecast_result
        
        # Get confidence intervals
        conf_int = self.model.get_forecast(steps=steps).conf_int()
        
        logger.info(f"Generated {steps} step forecast")
        return forecast, conf_int
        
    def calculate_metrics(self, actual: np.ndarray,
                         predicted: np.ndarray) -> Dict[str, float]:
        """
        Calculate forecast accuracy metrics.
        
        Args:
            actual: Actual values
            predicted: Predicted values
            
        Returns:
            Dictionary of metrics
        """
        # Ensure arrays are same length
        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]
        
        # Calculate metrics
        mae = np.mean(np.abs(actual - predicted))
        mse = np.mean((actual - predicted) ** 2)
        rmse = np.sqrt(mse)
        
        # MAPE (avoid division by zero)
        mask = actual != 0
        mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100 if mask.sum() > 0 else 0
        
        metrics = {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'mape': float(mape)
        }
        
        self.metrics = metrics
        logger.info(f"Calculated metrics: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")
        
        return metrics
        
    def detect_trend(self, data: pd.Series) -> Dict[str, Any]:
        """
        Detect trend in time series.
        
        Args:
            data: Time series data
            
        Returns:
            Dictionary with trend information
        """
        # Perform seasonal decomposition
        decomposition = seasonal_decompose(data, model='additive', period=min(12, len(data)//2))
        
        # Get trend component
        trend = decomposition.trend.dropna()
        
        # Calculate trend direction
        trend_slope = np.polyfit(range(len(trend)), trend, 1)[0]
        
        # Perform stationarity test
        adf_result = adfuller(data.dropna())
        
        trend_info = {
            'slope': float(trend_slope),
            'direction': 'increasing' if trend_slope > 0 else 'decreasing',
            'stationary': adf_result[1] < 0.05,
            'adf_statistic': float(adf_result[0]),
            'adf_pvalue': float(adf_result[1])
        }
        
        logger.info(f"Trend: {trend_info['direction']} (slope={trend_slope:.4f})")
        return trend_info
        
    def forecast_technology_demand(self, data: Dict[str, pd.DataFrame],
                                  periods: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Forecast demand for multiple technologies.
        
        Args:
            data: Dictionary mapping technology names to dataframes
            periods: Number of periods to forecast
            
        Returns:
            Dictionary with forecasts for each technology
        """
        logger.info(f"Forecasting demand for {len(data)} technologies")
        
        forecasts = {}
        
        for tech, df in data.items():
            try:
                # Prepare data for Prophet
                prophet_df = df.rename(columns={'date': 'ds', 'value': 'y'})
                
                # Fit model
                self.fit_prophet(prophet_df)
                
                # Generate forecast
                forecast = self.predict_prophet(periods=periods)
                
                # Extract key metrics
                future_forecast = forecast.tail(periods)
                
                forecasts[tech] = {
                    'forecast': future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict('records'),
                    'trend': self.detect_trend(df['value']),
                    'last_value': float(df['value'].iloc[-1]),
                    'forecast_mean': float(future_forecast['yhat'].mean()),
                    'forecast_trend': 'growing' if future_forecast['yhat'].iloc[-1] > future_forecast['yhat'].iloc[0] else 'declining',
                    'confidence': float((future_forecast['yhat_upper'] - future_forecast['yhat_lower']).mean())
                }
                
                logger.info(f"Forecast completed for {tech}")
                
            except Exception as e:
                logger.error(f"Error forecasting {tech}: {e}")
                forecasts[tech] = None
                
        return forecasts
