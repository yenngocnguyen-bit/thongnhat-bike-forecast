from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from functools import lru_cache

from dashboard.data_cache import get_q3_forecasts


@lru_cache(maxsize=1)
def layout():
    q3 = get_q3_forecasts()
    dealers = q3['dealers']
    churn = q3['churn']

    priority_counts = dealers['marketing_priority'].value_counts()
    segment_counts = dealers['rfm_segment'].value_counts()

    kpi = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tổng đại lý", className="text-muted"),
            html.H3(f"{len(dealers)}", className="text-primary"),
        ]), className="shadow-sm"), width=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Giữ chân", className="text-muted"),
            html.H3(f"{priority_counts.get('Giữ chân', 0)}", className="text-success"),
        ]), className="shadow-sm"), width=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Phát triển", className="text-muted"),
            html.H3(f"{priority_counts.get('Phát triển', 0)}", className="text-info"),
        ]), className="shadow-sm"), width=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Cảnh báo", className="text-muted"),
            html.H3(f"{priority_counts.get('Cảnh báo', 0)}", className="text-warning"),
        ]), className="shadow-sm"), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Nguy cơ", className="text-muted"),
            html.H3(f"{priority_counts.get('Nguy cơ', 0)}", className="text-danger"),
        ]), className="shadow-sm"), width=3),
    ], className="mb-4")

    color_map = {
        'Giữ chân': '#27ae60', 'Cảnh báo': '#f39c12',
        'Phát triển': '#3498db', 'Nguy cơ': '#e74c3c'
    }
    fig_scatter = px.scatter(
        dealers, x='prob_order_30d', y='trend_score',
        color='marketing_priority', color_discrete_map=color_map,
        hover_data=['customer_code', 'total_orders', 'total_revenue', 'rfm_segment'],
        title='Ma trận tiếp thị: Xác suất đặt hàng vs Xu hướng',
        labels={'prob_order_30d': 'P(đặt hàng 30 ngày)',
                'trend_score': 'Điểm xu hướng',
                'marketing_priority': 'Ưu tiên'}
    )
    fig_scatter.update_layout(height=500)
    fig_scatter.add_hline(y=dealers['trend_score'].median(), line_dash="dash", line_color="gray", opacity=0.5)
    fig_scatter.add_vline(x=dealers['prob_order_30d'].median(), line_dash="dash", line_color="gray", opacity=0.5)

    fig_priority = px.bar(
        priority_counts.reset_index(), x='marketing_priority', y='count',
        color='marketing_priority', color_discrete_map=color_map,
        title='Số đại lý theo phân khúc tiếp thị',
        labels={'marketing_priority': 'Phân khúc', 'count': 'Số đại lý'}
    )

    fig_rfm = px.bar(
        segment_counts.reset_index(), x='rfm_segment', y='count',
        title='Phân khúc RFM',
        labels={'rfm_segment': 'Segment', 'count': 'Số đại lý'}
    )
    fig_rfm.update_layout(xaxis_tickangle=-30)

    fig_region = dealers.groupby('region')['marketing_priority'].value_counts().reset_index()
    fig_region_bar = px.bar(
        fig_region, x='region', y='count', color='marketing_priority',
        color_discrete_map=color_map, barmode='stack',
        title='Phân bổ theo vùng miền',
        labels={'region': 'Vùng', 'count': 'Số đại lý', 'marketing_priority': 'Ưu tiên'}
    )

    churn_display = churn[['customer_code', 'recency', 'total_orders', 'total_revenue',
                           'prob_order_30d', 'rfm_segment', 'marketing_priority', 'risk_level']].copy()
    churn_display.columns = ['Mã KH', 'Ngày chưa mua', 'Tổng đơn', 'Tổng DT',
                             'P(mua)', 'RFM', 'Ưu tiên', 'Mức rủi ro']
    churn_display['P(mua)'] = churn_display['P(mua)'].round(3)
    churn_display['Tổng DT'] = churn_display['Tổng DT'].apply(lambda x: f"{x:,.0f}")

    dealer_table = dealers.nlargest(50, 'prob_order_30d')[
        ['customer_code', 'prob_order_30d', 'trend_score', 'total_orders',
         'total_revenue', 'rfm_segment', 'marketing_priority', 'region']
    ].copy()
    dealer_table.columns = ['Mã KH', 'P(mua)', 'Xu hướng', 'Tổng đơn',
                            'Tổng DT', 'RFM', 'Ưu tiên', 'Vùng']
    dealer_table['P(mua)'] = dealer_table['P(mua)'].round(3)
    dealer_table['Xu hướng'] = dealer_table['Xu hướng'].round(1)
    dealer_table['Tổng DT'] = dealer_table['Tổng DT'].apply(lambda x: f"{x:,.0f}")

    graph_cfg = {'displayModeBar': False}

    return html.Div([
        html.H2("🏪 Dự báo Hoạt động Đại lý", className="mb-4"),
        kpi,
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_scatter, config=graph_cfg), width=8),
            dbc.Col(dcc.Graph(figure=fig_priority, config=graph_cfg), width=4),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_rfm, config=graph_cfg), width=6),
            dbc.Col(dcc.Graph(figure=fig_region_bar, config=graph_cfg), width=6),
        ], className="mb-4"),
        html.H5("🚨 Đại lý nguy cơ rời bỏ cao nhất", className="mb-3"),
        dash_table.DataTable(
            data=churn_display.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in churn_display.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'center', 'padding': '8px', 'fontSize': '13px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#ecf0f1'},
            style_data_conditional=[
                {'if': {'filter_query': '{Mức rủi ro} = "Cao"'}, 'backgroundColor': '#fadbd8'},
                {'if': {'filter_query': '{Mức rủi ro} = "Trung bình"'}, 'backgroundColor': '#fdebd0'},
            ],
            page_size=15
        ),
        html.H5("📋 Top 50 đại lý theo xác suất mua hàng", className="mb-3 mt-4"),
        dash_table.DataTable(
            data=dealer_table.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in dealer_table.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'center', 'padding': '8px', 'fontSize': '13px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#ecf0f1'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
            ],
            page_size=15
        ),
    ])
