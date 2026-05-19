import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

DATA = Path(__file__).parent.parent.parent / 'data' / 'processed'
FCAST = DATA / 'forecasts'


def load_data():
    monthly = pd.read_parquet(FCAST / 'q1_monthly_forecast.parquet')
    group_fc = pd.read_parquet(FCAST / 'q1_group_forecast.parquet')
    top20 = pd.read_parquet(FCAST / 'q1_top20_skus.parquet')
    rev_fc = pd.read_parquet(FCAST / 'q1_revenue_forecast.parquet')
    comparison = pd.read_parquet(FCAST / 'q1_model_comparison.parquet')

    fs = pd.read_parquet(DATA / 'fact_sales_clean.parquet')
    fs['order_date'] = pd.to_datetime(fs['order_date'])
    hist_weekly = fs.set_index('order_date').resample('W-MON')['line_total'].sum().reset_index()
    hist_weekly.columns = ['week', 'revenue']

    return monthly, group_fc, top20, rev_fc, comparison, hist_weekly


def layout():
    monthly, group_fc, top20, rev_fc, comparison, hist_weekly = load_data()

    total_rev = monthly['revenue'].sum()
    total_qty = monthly['quantity'].sum()

    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tổng doanh thu Q2", className="text-muted"),
            html.H3(f"{total_rev:,.0f}", className="text-primary"),
            html.Small("VNĐ")
        ]), className="shadow-sm"), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tổng số lượng Q2", className="text-muted"),
            html.H3(f"{total_qty:,.0f}", className="text-success"),
            html.Small("xe")
        ]), className="shadow-sm"), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tháng 4", className="text-muted"),
            html.H3(f"{monthly[monthly['month']==4]['revenue'].values[0]:,.0f}", className="text-info"),
            html.Small("VNĐ")
        ]), className="shadow-sm"), width=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tháng 5", className="text-muted"),
            html.H3(f"{monthly[monthly['month']==5]['revenue'].values[0]:,.0f}", className="text-info"),
            html.Small("VNĐ")
        ]), className="shadow-sm"), width=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tháng 6", className="text-muted"),
            html.H3(f"{monthly[monthly['month']==6]['revenue'].values[0]:,.0f}", className="text-info"),
            html.Small("VNĐ")
        ]), className="shadow-sm"), width=2),
    ], className="mb-4")

    rev_fc['week'] = pd.to_datetime(rev_fc['week'])
    fig_timeline = go.Figure()
    fig_timeline.add_trace(go.Scatter(
        x=hist_weekly['week'], y=hist_weekly['revenue'],
        mode='lines', name='Thực tế', line=dict(color='#2c3e50')
    ))
    fig_timeline.add_trace(go.Scatter(
        x=rev_fc['week'], y=rev_fc['revenue_lgb'],
        mode='lines+markers', name='LightGBM', line=dict(color='#e74c3c', dash='dash')
    ))
    if 'revenue_prophet' in rev_fc.columns:
        fig_timeline.add_trace(go.Scatter(
            x=rev_fc['week'], y=rev_fc['revenue_prophet'],
            mode='lines+markers', name='Prophet', line=dict(color='#3498db', dash='dot')
        ))
    fig_timeline.update_layout(
        title='Doanh thu tuần: Lịch sử + Dự báo Q2/2026',
        xaxis_title='Tuần', yaxis_title='Doanh thu (VNĐ)',
        hovermode='x unified', height=400
    )

    group_fc['month_name'] = group_fc['month'].map({4: 'T4', 5: 'T5', 6: 'T6'})
    fig_group = px.bar(
        group_fc, x='month_name', y='revenue', color='group_code',
        barmode='stack', title='Doanh thu dự báo theo nhóm SP & tháng',
        labels={'month_name': 'Tháng', 'revenue': 'Doanh thu', 'group_code': 'Nhóm'}
    )

    top20_display = top20[['rank', 'product_name', 'group_code', 'color_std',
                           'pred_quantity', 'pred_revenue']].copy()
    top20_display.columns = ['#', 'Sản phẩm', 'Nhóm', 'Màu', 'SL dự báo', 'DT dự báo']
    top20_display['SL dự báo'] = top20_display['SL dự báo'].round(0).astype(int)
    top20_display['DT dự báo'] = top20_display['DT dự báo'].apply(lambda x: f"{x:,.0f}")

    return html.Div([
        html.H2("📊 Dự báo Doanh số Q2/2026", className="mb-4"),
        kpi_cards,
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_timeline), width=12),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_group), width=6),
            dbc.Col([
                html.H5("So sánh Model", className="mb-3"),
                dash_table.DataTable(
                    data=comparison.round(4).to_dict('records'),
                    columns=[{'name': c, 'id': c} for c in comparison.columns],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '8px'},
                    style_header={'fontWeight': 'bold', 'backgroundColor': '#ecf0f1'},
                )
            ], width=6),
        ], className="mb-4"),
        html.H5("🏆 Top 20 SKU dự kiến bán chạy nhất", className="mb-3"),
        dash_table.DataTable(
            data=top20_display.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in top20_display.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '13px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#ecf0f1'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
            ],
            page_size=20
        ),
    ])
