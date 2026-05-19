import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

try:
    from dashboard.data_cache import warm_cache
    from dashboard.pages.tab1_sales import layout as tab1_layout
    from dashboard.pages.tab2_color import layout as tab2_layout
    from dashboard.pages.tab3_dealer import layout as tab3_layout
    from dashboard.pages.tab4_llm import layout as tab4_layout
except ImportError:
    from data_cache import warm_cache
    from pages.tab1_sales import layout as tab1_layout
    from pages.tab2_color import layout as tab2_layout
    from pages.tab3_dealer import layout as tab3_layout
    from pages.tab4_llm import layout as tab4_layout

# Pre-load data and build all pages once at startup
warm_cache()
PAGES = {
    '/': tab1_layout(),
    '/color': tab2_layout(),
    '/dealer': tab3_layout(),
    '/llm': tab4_layout(),
}

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    title="Thống Nhất Bike - Dự báo Q2/2026"
)
server = app.server

sidebar = dbc.Nav(
    [
        dbc.NavLink("Doanh số", href="/", active="exact", id="nav-sales"),
        dbc.NavLink("Màu sắc", href="/color", active="exact", id="nav-color"),
        dbc.NavLink("Đại lý", href="/dealer", active="exact", id="nav-dealer"),
        dbc.NavLink("Phân tích LLM", href="/llm", active="exact", id="nav-llm"),
    ],
    vertical=True, pills=True, className="bg-light p-3"
)

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.Row([
        dbc.Col(
            html.Div([
                html.H4("🚲 Thống Nhất Bike", className="text-primary mb-3 mt-3"),
                html.P("Dự báo nhu cầu Q2/2026", className="text-muted small"),
                html.Hr(),
                sidebar,
            ], className="bg-light vh-100 position-fixed", style={"width": "220px", "padding": "10px"}),
            width=2, className="p-0"
        ),
        dbc.Col(
            html.Div([
                html.Div(PAGES['/'], id='page-sales', style={'display': 'block'}),
                html.Div(PAGES['/color'], id='page-color', style={'display': 'none'}),
                html.Div(PAGES['/dealer'], id='page-dealer', style={'display': 'none'}),
                html.Div(PAGES['/llm'], id='page-llm', style={'display': 'none'}),
            ], className="p-4"),
            width=10, style={"marginLeft": "220px"}
        ),
    ], className="g-0"),
], fluid=True)


@app.callback(
    [
        Output('page-sales', 'style'),
        Output('page-color', 'style'),
        Output('page-dealer', 'style'),
        Output('page-llm', 'style'),
    ],
    Input('url', 'pathname'),
)
def toggle_pages(pathname):
    active = pathname if pathname in PAGES else '/'
    hidden = {'display': 'none'}
    visible = {'display': 'block'}
    return [
        visible if active == '/' else hidden,
        visible if active == '/color' else hidden,
        visible if active == '/dealer' else hidden,
        visible if active == '/llm' else hidden,
    ]


if __name__ == '__main__':
    app.run(debug=True, port=8050)
