#!/usr/bin/env python3
"""
Rebuild product-week panel (no gap-filled zero weeks) and Q1 forecast parquets.
Run from project root: python3 scripts/regenerate_q1_pipeline.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import lightgbm as lgb
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dashboard'))
from time_series_utils import weekly_revenue_observed

DATA = ROOT / 'data' / 'processed'
FCAST = DATA / 'forecasts'


def build_product_week_panel(fs: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    fs = fs.copy()
    fs['week_start'] = fs['order_date'].dt.to_period('W').apply(lambda x: x.start_time)

    pw = fs.groupby(['product_code', 'week_start']).agg(
        quantity=('quantity', 'sum'),
        revenue=('line_total', 'sum'),
        unit_price=('unit_price', 'mean'),
        group_code=('group_code', 'first'),
        line_id_fk=('line_id_fk', 'first'),
        line_name=('line_name', 'first'),
        color_std=('color_std', 'first'),
        product_name=('product_name', 'first'),
    ).reset_index()

    all_weeks = pd.DatetimeIndex(sorted(pw['week_start'].unique()))
    all_products = pw['product_code'].unique()
    print(f'Observed weeks: {len(all_weeks)} (missing calendar months are NOT zero revenue)')

    prod_attrs = pw.groupby('product_code').agg(
        group_code=('group_code', 'first'),
        line_id_fk=('line_id_fk', 'first'),
        line_name=('line_name', 'first'),
        color_std=('color_std', 'first'),
        product_name=('product_name', 'first'),
        unit_price=('unit_price', 'last'),
    ).reset_index()

    idx = pd.MultiIndex.from_product([all_products, all_weeks], names=['product_code', 'week_start'])
    pw_full = pd.DataFrame(index=idx).reset_index()
    pw_full = pw_full.merge(pw[['product_code', 'week_start', 'quantity', 'revenue']], on=['product_code', 'week_start'], how='left')
    pw_full['quantity'] = pw_full['quantity'].fillna(0)
    pw_full['revenue'] = pw_full['revenue'].fillna(0)
    pw_full = pw_full.merge(prod_attrs, on='product_code', how='left')

    pw_full['month'] = pw_full['week_start'].dt.month
    pw_full['week_of_year'] = pw_full['week_start'].dt.isocalendar().week.astype(int)
    pw_full['quarter'] = pw_full['week_start'].dt.quarter
    pw_full = pw_full.sort_values(['product_code', 'week_start']).reset_index(drop=True)

    for lag in [1, 2, 4]:
        pw_full[f'qty_lag_{lag}w'] = pw_full.groupby('product_code')['quantity'].shift(lag)
        pw_full[f'rev_lag_{lag}w'] = pw_full.groupby('product_code')['revenue'].shift(lag)

    for win in [4, 8]:
        pw_full[f'qty_roll_{win}w'] = pw_full.groupby('product_code')['quantity'].transform(
            lambda x: x.rolling(win, min_periods=1).mean()
        )
        pw_full[f'rev_roll_{win}w'] = pw_full.groupby('product_code')['revenue'].transform(
            lambda x: x.rolling(win, min_periods=1).mean()
        )

    first_sale = fs.groupby('product_code')['order_date'].min().reset_index()
    first_sale.columns = ['product_code', 'first_sale_date']
    pw_full = pw_full.merge(first_sale, on='product_code', how='left')
    pw_full['weeks_since_first'] = ((pw_full['week_start'] - pw_full['first_sale_date']).dt.days / 7).clip(lower=0)
    pw_full['cum_quantity'] = pw_full.groupby('product_code')['quantity'].cumsum()

    price_changes = prices.sort_values(['product_code', 'effective_from'])
    price_changes['effective_from'] = pd.to_datetime(price_changes['effective_from'])
    pc_count = price_changes.groupby('product_code').size().reset_index(name='n_price_changes')
    pw_full = pw_full.merge(pc_count, on='product_code', how='left')
    pw_full['n_price_changes'] = pw_full['n_price_changes'].fillna(0)

    le_group = LabelEncoder()
    pw_full['group_code_enc'] = le_group.fit_transform(pw_full['group_code'].fillna('UNK').astype(str))
    le_color = LabelEncoder()
    pw_full['color_enc'] = le_color.fit_transform(pw_full['color_std'].fillna('unknown').astype(str))

    return pw_full.drop(columns=['first_sale_date'])


def run_prophet(fs: pd.DataFrame):
    weekly = weekly_revenue_observed(fs)
    train_end = pd.Timestamp('2025-12-31')
    train_p = weekly[weekly['ds'] <= train_end].copy()
    val_p = weekly[weekly['ds'] > train_end].copy()
    print(f'Prophet: {len(train_p)} train weeks, {len(val_p)} val weeks')

    m = Prophet(
        yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
        seasonality_mode='additive',
    )
    m.fit(train_p)
    val_pred = m.predict(val_p[['ds']])
    val_pred['yhat'] = val_pred['yhat'].clip(lower=0)
    val_mape = mean_absolute_percentage_error(val_p['y'], val_pred['yhat'])
    val_rmse = np.sqrt(mean_squared_error(val_p['y'], val_pred['yhat']))

    m_full = Prophet(
        yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
        seasonality_mode='additive',
    )
    m_full.fit(weekly)
    future_weeks = m_full.make_future_dataframe(periods=13, freq='W-MON')
    forecast_prophet = m_full.predict(future_weeks)
    q2_prophet = forecast_prophet[forecast_prophet['ds'] >= '2026-04-01'][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    q2_prophet.columns = ['week', 'revenue_prophet', 'lower', 'upper']
    for col in ['revenue_prophet', 'lower', 'upper']:
        q2_prophet[col] = q2_prophet[col].clip(lower=0)
    q2_prophet['month'] = q2_prophet['week'].dt.month

    return q2_prophet, val_mape, val_rmse, weekly


def run_lightgbm(pw: pd.DataFrame):
    feature_cols = [
        'month', 'week_of_year', 'quarter', 'group_code_enc', 'color_enc',
        'unit_price', 'qty_lag_1w', 'qty_lag_2w', 'qty_lag_4w',
        'rev_lag_1w', 'rev_lag_2w', 'rev_lag_4w',
        'qty_roll_4w', 'qty_roll_8w', 'rev_roll_4w', 'rev_roll_8w',
        'weeks_since_first', 'cum_quantity', 'n_price_changes',
    ]
    pw_model = pw.dropna(subset=feature_cols).copy()

    train_lgb = pw_model[pw_model['week_start'] <= '2025-12-31']
    val_lgb = pw_model[(pw_model['week_start'] > '2025-12-31') & (pw_model['week_start'] <= '2026-03-31')]

    X_train, y_train = train_lgb[feature_cols], train_lgb['quantity']
    X_val, y_val = val_lgb[feature_cols], val_lgb['quantity']

    model_lgb = lgb.LGBMRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=8,
        num_leaves=31, subsample=0.8, colsample_bytree=0.8,
        min_child_samples=10, random_state=42, verbose=-1,
    )
    model_lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50, verbose=False)])
    val_pred_lgb = model_lgb.predict(X_val).clip(min=0)
    mask = y_val > 0
    lgb_mape = mean_absolute_percentage_error(y_val[mask], val_pred_lgb[mask])
    lgb_rmse = np.sqrt(mean_squared_error(y_val, val_pred_lgb))
    lgb_mae = mean_absolute_error(y_val, val_pred_lgb)

    n_est = model_lgb.best_iteration_ if hasattr(model_lgb, 'best_iteration_') else 300
    model_full = lgb.LGBMRegressor(
        n_estimators=n_est, learning_rate=0.05, max_depth=8, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=10, random_state=42, verbose=-1,
    )
    train_full = pw_model[pw_model['week_start'] <= '2026-03-31']
    model_full.fit(train_full[feature_cols], train_full['quantity'])

    last_week = pw_model[pw_model['week_start'] == pw_model['week_start'].max()].copy()
    q2_weeks = pd.date_range('2026-04-06', periods=13, freq='W-MON')
    all_preds = []

    for wk in q2_weeks:
        pred_rows = last_week.copy()
        pred_rows['week_start'] = wk
        pred_rows['month'] = wk.month
        pred_rows['week_of_year'] = wk.isocalendar()[1]
        pred_rows['quarter'] = (wk.month - 1) // 3 + 1
        pred_rows['weeks_since_first'] = pred_rows['weeks_since_first'] + 1
        pred_qty = model_full.predict(pred_rows[feature_cols]).clip(min=0)
        pred_rows['quantity'] = pred_qty
        pred_rows['revenue'] = pred_qty * pred_rows['unit_price']
        all_preds.append(pred_rows[['product_code', 'week_start', 'quantity', 'revenue', 'unit_price',
                                    'group_code', 'line_name', 'color_std', 'product_name']])
        last_week = pred_rows

    q2_preds = pd.concat(all_preds, ignore_index=True)
    q2_preds['month'] = q2_preds['week_start'].dt.month
    return q2_preds, feature_cols, lgb_mape, lgb_rmse, lgb_mae


def main():
    FCAST.mkdir(parents=True, exist_ok=True)
    fs = pd.read_parquet(DATA / 'fact_sales_clean.parquet')
    fs['order_date'] = pd.to_datetime(fs['order_date'])
    prices = pd.read_parquet(DATA / 'product_prices.parquet')

    print('=== Building product-week panel ===')
    pw = build_product_week_panel(fs, prices)
    pw.to_parquet(DATA / 'product_week_panel.parquet', index=False)
    print(f'Saved product_week_panel.parquet: {pw.shape}')

    print('\n=== Prophet ===')
    q2_prophet, val_mape, val_rmse, weekly = run_prophet(fs)
    print(q2_prophet[['week', 'revenue_prophet']])
    print(f'Prophet Q2 total: {q2_prophet["revenue_prophet"].sum():,.0f} VND')
    print(f'Any negative? {(q2_prophet["revenue_prophet"] < 0).any()}')

    print('\n=== LightGBM ===')
    q2_preds, feature_cols, lgb_mape, lgb_rmse, lgb_mae = run_lightgbm(pw)
    print(f'LightGBM Q2 revenue: {q2_preds["revenue"].sum():,.0f} VND')

    monthly_rev = q2_preds.groupby('month').agg(revenue=('revenue', 'sum'), quantity=('quantity', 'sum')).reset_index()
    monthly_rev['month_name'] = monthly_rev['month'].map({4: 'Tháng 4', 5: 'Tháng 5', 6: 'Tháng 6'})

    group_rev = q2_preds.groupby(['group_code', 'month']).agg(revenue=('revenue', 'sum'), quantity=('quantity', 'sum')).reset_index()

    top20 = q2_preds.groupby(['product_code', 'product_name', 'group_code', 'color_std', 'line_name']).agg(
        pred_quantity=('quantity', 'sum'), pred_revenue=('revenue', 'sum'),
    ).reset_index().nlargest(20, 'pred_quantity')
    top20['rank'] = range(1, len(top20) + 1)

    rev_fc = q2_preds.groupby('week_start').agg(revenue_lgb=('revenue', 'sum')).reset_index()
    rev_fc.columns = ['week', 'revenue_lgb']
    rev_fc = rev_fc.merge(q2_prophet[['week', 'revenue_prophet']], on='week', how='outer')

    comparison = pd.DataFrame({
        'Model': ['Prophet', 'LightGBM'],
        'Val MAPE': [val_mape, lgb_mape],
        'Val RMSE': [val_rmse, lgb_rmse],
    })

    rev_fc.to_parquet(FCAST / 'q1_revenue_forecast.parquet', index=False)
    top20.to_parquet(FCAST / 'q1_top20_skus.parquet', index=False)
    group_rev.to_parquet(FCAST / 'q1_group_forecast.parquet', index=False)
    monthly_rev.to_parquet(FCAST / 'q1_monthly_forecast.parquet', index=False)
    comparison.to_parquet(FCAST / 'q1_model_comparison.parquet', index=False)

    print('\n=== Done ===')
    print(comparison)
    print(f'Historical weeks for chart: {len(weekly)} (was 66 with gap-zeros)')


if __name__ == '__main__':
    main()
