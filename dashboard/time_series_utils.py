"""Helpers for time series — missing calendar periods are not zero revenue."""
import pandas as pd


def weekly_revenue_observed(
    sales: pd.DataFrame,
    date_col: str = 'order_date',
    value_col: str = 'line_total',
) -> pd.DataFrame:
    """
    Sum revenue by week only for weeks that have at least one sale row.
    Does NOT fill gaps between data windows with zeros.
    """
    df = sales.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df['week_start'] = df[date_col].dt.to_period('W').apply(lambda x: x.start_time)
    weekly = (
        df.groupby('week_start', as_index=False)[value_col]
        .sum()
        .rename(columns={'week_start': 'ds', value_col: 'y'})
        .sort_values('ds')
        .reset_index(drop=True)
    )
    return weekly


def weeks_with_any_sales(sales: pd.DataFrame, date_col: str = 'order_date') -> pd.DatetimeIndex:
    """Week starts where the dataset has at least one transaction."""
    df = sales.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    weeks = df[date_col].dt.to_period('W').apply(lambda x: x.start_time).unique()
    return pd.DatetimeIndex(sorted(weeks))
