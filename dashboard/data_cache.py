"""Cached data loaders — read parquet once per worker process."""
from functools import lru_cache
from pathlib import Path
import json
import pandas as pd

DATA = Path(__file__).parent.parent / 'data' / 'processed'
FCAST = DATA / 'forecasts'


@lru_cache(maxsize=1)
def get_fact_sales():
    fs = pd.read_parquet(DATA / 'fact_sales_clean.parquet')
    fs['order_date'] = pd.to_datetime(fs['order_date'])
    return fs


@lru_cache(maxsize=1)
def get_hist_weekly():
    from dashboard.time_series_utils import weekly_revenue_observed
    fs = get_fact_sales()
    weekly = weekly_revenue_observed(fs)
    weekly.columns = ['week', 'revenue']
    return weekly


@lru_cache(maxsize=1)
def get_color_hist():
    fs = get_fact_sales()
    fs = fs.copy()
    fs['ym'] = fs['order_date'].dt.to_period('M').astype(str)
    months_with_data = sorted(fs['ym'].unique())
    top_colors = fs['color_std'].value_counts().head(12).index.tolist()
    hist = fs[fs['color_std'].isin(top_colors)]
    hist_cm = hist.groupby(['ym', 'color_std'])['quantity'].sum().reset_index()
    hist_cm = hist_cm[hist_cm['ym'].isin(months_with_data)]
    total_by_m = hist.groupby('ym')['quantity'].sum().reset_index(name='total')
    hist_cm = hist_cm.merge(total_by_m, on='ym')
    hist_cm['share'] = hist_cm['quantity'] / hist_cm['total']
    return hist_cm, months_with_data


@lru_cache(maxsize=1)
def get_q1_forecasts():
    return {
        'monthly': pd.read_parquet(FCAST / 'q1_monthly_forecast.parquet'),
        'group_fc': pd.read_parquet(FCAST / 'q1_group_forecast.parquet'),
        'top20': pd.read_parquet(FCAST / 'q1_top20_skus.parquet'),
        'rev_fc': pd.read_parquet(FCAST / 'q1_revenue_forecast.parquet'),
        'comparison': pd.read_parquet(FCAST / 'q1_model_comparison.parquet'),
    }


@lru_cache(maxsize=1)
def get_q2_forecasts():
    return {
        'color_fc': pd.read_parquet(FCAST / 'q2_color_forecast.parquet'),
        'slow': pd.read_parquet(FCAST / 'q2_slow_moving.parquet'),
    }


@lru_cache(maxsize=1)
def get_q3_forecasts():
    return {
        'dealers': pd.read_parquet(FCAST / 'q3_dealer_probability.parquet'),
        'churn': pd.read_parquet(FCAST / 'q3_churn_risk.parquet'),
    }


@lru_cache(maxsize=1)
def get_llm_insights():
    path = FCAST / 'llm_insights.json'
    if not path.exists():
        return {
            'executive_summary': 'Chưa có dữ liệu. Hãy chạy notebook 04_llm_integration.ipynb với GROQ_API_KEY.',
            'q1_analysis': 'Chưa có.',
            'q2_analysis': 'Chưa có.',
            'q3_analysis': 'Chưa có.',
            'model': 'N/A',
            'generated_at': 'N/A',
        }
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def warm_cache():
    """Pre-load all data at startup so first page view is fast too."""
    get_fact_sales()
    get_hist_weekly()
    get_color_hist()
    get_q1_forecasts()
    get_q2_forecasts()
    get_q3_forecasts()
    get_llm_insights()
