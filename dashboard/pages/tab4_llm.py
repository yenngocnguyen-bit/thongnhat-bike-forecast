from dash import html, dcc
import dash_bootstrap_components as dbc
import json
from pathlib import Path

FCAST = Path(__file__).parent.parent.parent / 'data' / 'processed' / 'forecasts'


def load_insights():
    path = FCAST / 'llm_insights.json'
    if not path.exists():
        return {
            'executive_summary': 'Chưa có dữ liệu. Hãy chạy notebook 04_llm_integration.ipynb với GROQ_API_KEY.',
            'q1_analysis': 'Chưa có.',
            'q2_analysis': 'Chưa có.',
            'q3_analysis': 'Chưa có.',
            'model': 'N/A',
            'generated_at': 'N/A'
        }
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_text(text):
    paragraphs = text.split('\n')
    elements = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('#'):
            level = len(p) - len(p.lstrip('#'))
            text_content = p.lstrip('#').strip()
            if level <= 2:
                elements.append(html.H5(text_content, className="mt-3 mb-2"))
            else:
                elements.append(html.H6(text_content, className="mt-2 mb-1"))
        elif p.startswith('- ') or p.startswith('* '):
            elements.append(html.Li(p[2:], className="mb-1"))
        elif p.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            elements.append(html.Li(p[2:].strip(), className="mb-1"))
        else:
            elements.append(html.P(p, className="mb-2"))
    return elements


def layout():
    insights = load_insights()

    return html.Div([
        html.H2("🤖 Phân tích LLM", className="mb-4"),
        dbc.Alert([
            html.Strong("Model: "), insights.get('model', 'N/A'),
            html.Span(" | ", className="mx-2"),
            html.Strong("Thời gian: "), insights.get('generated_at', 'N/A'),
        ], color="info", className="mb-4"),

        dbc.Card([
            dbc.CardHeader(html.H5("📋 Báo cáo tóm tắt điều hành", className="mb-0")),
            dbc.CardBody(format_text(insights.get('executive_summary', '')))
        ], className="shadow-sm mb-4"),

        dbc.Accordion([
            dbc.AccordionItem(
                format_text(insights.get('q1_analysis', '')),
                title="Câu hỏi 1: Phân tích dự báo doanh số Q2/2026"
            ),
            dbc.AccordionItem(
                format_text(insights.get('q2_analysis', '')),
                title="Câu hỏi 2: Phân tích dự báo màu sắc"
            ),
            dbc.AccordionItem(
                format_text(insights.get('q3_analysis', '')),
                title="Câu hỏi 3: Phân tích hoạt động đại lý"
            ),
        ], start_collapsed=True, className="mb-4"),

        dbc.Alert(
            "💡 Để cập nhật phân tích LLM, hãy thêm GROQ_API_KEY vào file .env và chạy lại notebook 04.",
            color="warning"
        ),
    ])
