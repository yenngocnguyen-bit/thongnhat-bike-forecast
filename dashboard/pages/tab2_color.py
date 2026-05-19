from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from functools import lru_cache

from dashboard.data_cache import get_q2_forecasts, get_color_hist


@lru_cache(maxsize=1)
def layout():
    q2 = get_q2_forecasts()
    color_fc = q2['color_fc']
    slow = q2['slow']
    hist_cm, months_with_data = get_color_hist()

    fig_hist = px.bar(
        hist_cm, x='ym', y='share', color='color_std',
        barmode='stack', title='Tỷ trọng màu sắc theo tháng (Lịch sử - Top 12)',
        labels={'ym': 'Tháng', 'share': 'Tỷ trọng', 'color_std': 'Màu'},
        category_orders={'ym': months_with_data}
    )
    fig_hist.update_layout(xaxis_tickangle=-45, height=450, xaxis_type='category')

    heatmap_data = hist_cm.pivot(index='color_std', columns='ym', values='quantity').fillna(0)
    heatmap_data = heatmap_data[months_with_data]
    fig_heatmap = px.imshow(
        heatmap_data, aspect='auto',
        title='Heatmap: Số lượng bán theo Màu x Tháng',
        labels={'x': 'Tháng', 'y': 'Màu', 'color': 'Số lượng'},
        x=months_with_data
    )
    fig_heatmap.update_layout(height=450, xaxis_type='category')

    fc_top = color_fc.groupby('color_std')['predicted_qty_share'].mean().nlargest(15).reset_index()
    fig_forecast = px.bar(
        fc_top, x='predicted_qty_share', y='color_std', orientation='h',
        title='Tỷ trọng màu sắc dự báo Q2/2026 (Top 15)',
        labels={'predicted_qty_share': 'Tỷ trọng', 'color_std': 'Màu'}
    )
    fig_forecast.update_layout(yaxis={'categoryorder': 'total ascending'}, height=450)

    slow_alert = slow[slow['status'].isin(['Bán chậm', 'Giảm'])].copy()
    slow_alert = slow_alert.sort_values('velocity_ratio')
    slow_display = slow_alert[['product_name', 'color_std', 'group_code',
                                'avg_recent_4w', 'avg_prior_8w', 'velocity_ratio', 'status']].head(30).copy()
    slow_display.columns = ['Sản phẩm', 'Màu', 'Nhóm', 'TB 4 tuần gần', 'TB 8 tuần trước', 'Tỷ lệ', 'Trạng thái']
    slow_display['Tỷ lệ'] = slow_display['Tỷ lệ'].round(2)
    slow_display['TB 4 tuần gần'] = slow_display['TB 4 tuần gần'].round(1)
    slow_display['TB 8 tuần trước'] = slow_display['TB 8 tuần trước'].round(1)

    status_counts = slow['status'].value_counts()

    graph_cfg = {'displayModeBar': False}

    return html.Div([
        html.H2("🎨 Dự báo Màu sắc Q2/2026", className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("SKU Bình thường", className="text-muted"),
                html.H3(f"{status_counts.get('Bình thường', 0)}", className="text-success"),
            ]), className="shadow-sm"), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("SKU Giảm", className="text-muted"),
                html.H3(f"{status_counts.get('Giảm', 0)}", className="text-warning"),
            ]), className="shadow-sm"), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("SKU Bán chậm", className="text-muted"),
                html.H3(f"{status_counts.get('Bán chậm', 0)}", className="text-danger"),
            ]), className="shadow-sm"), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Tổng SKU", className="text-muted"),
                html.H3(f"{len(slow)}", className="text-primary"),
            ]), className="shadow-sm"), width=3),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_hist, config=graph_cfg), width=6),
            dbc.Col(dcc.Graph(figure=fig_forecast, config=graph_cfg), width=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_heatmap, config=graph_cfg), width=12),
        ], className="mb-4"),
        html.H5("⚠️ SKU có dấu hiệu giảm / bán chậm", className="mb-3"),
        dash_table.DataTable(
            data=slow_display.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in slow_display.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '13px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#ecf0f1'},
            style_data_conditional=[
                {'if': {'filter_query': '{Trạng thái} = "Bán chậm"'}, 'backgroundColor': '#fadbd8'},
                {'if': {'filter_query': '{Trạng thái} = "Giảm"'}, 'backgroundColor': '#fdebd0'},
            ],
            page_size=15
        ),
    ])
