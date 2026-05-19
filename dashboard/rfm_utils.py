"""Classic RFM segmentation (10 segments) and treemap visualization."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Display order and blue gradient (dark = best customers)
SEGMENT_ORDER = [
    'Champions',
    'Loyal Customers',
    'Potential Champions',
    'New Customers',
    'Promising',
    'Need Attention',
    'About to Sleep',
    'At Risk',
    'Hibernating',
    'Do Not Lose',
]

SEGMENT_COLORS = {
    'Champions': '#0d47a1',
    'Loyal Customers': '#1565c0',
    'Potential Champions': '#1976d2',
    'New Customers': '#1e88e5',
    'Promising': '#42a5f5',
    'Need Attention': '#64b5f6',
    'About to Sleep': '#90caf9',
    'At Risk': '#bbdefb',
    'Hibernating': '#e3f2fd',
    'Do Not Lose': '#0d3b66',
}


def fm_score(f: int, m: int) -> float:
    return (int(f) + int(m)) / 2.0


def assign_rfm_segment(r: int, f: int, m: int) -> str:
    """
    Map R/F/M scores (1–5) to classic RFM segment labels.
    Y-axis in the reference chart = Frequency / Monetary (avg of F & M).
    """
    r, f, m = int(r), int(f), int(m)
    fm = fm_score(f, m)

    if r >= 4 and f >= 4 and m >= 4:
        return 'Champions'
    if r >= 3 and fm >= 3.5:
        return 'Loyal Customers'
    if r <= 2 and fm >= 4.5:
        return 'Do Not Lose'
    if r >= 4 and fm <= 1.5:
        return 'New Customers'
    if r >= 3 and 1.5 < fm < 3.5:
        return 'Potential Champions'
    if r >= 3 and fm <= 1.5:
        return 'Promising'
    if 2 <= r <= 3 and 2 <= fm <= 3:
        return 'Need Attention'
    if 2 <= r <= 3 and fm < 2:
        return 'About to Sleep'
    if r <= 2 and 2.5 <= fm <= 4:
        return 'At Risk'
    if r <= 2 and fm < 2.5:
        return 'Hibernating'
    return 'Need Attention'


def apply_rfm_segments(dealers: pd.DataFrame) -> pd.DataFrame:
    """Recompute rfm_segment and FM_score from R/F/M columns."""
    out = dealers.copy()
    if not {'R_score', 'F_score', 'M_score'}.issubset(out.columns):
        return out
    out['FM_score'] = ((out['F_score'] + out['M_score']) / 2).round(1)
    out['rfm_segment'] = out.apply(
        lambda row: assign_rfm_segment(row['R_score'], row['F_score'], row['M_score']),
        axis=1,
    )
    out['RFM_score'] = out['R_score'] + out['F_score'] + out['M_score']
    return out


def build_rfm_treemap(dealers: pd.DataFrame) -> go.Figure:
    """Treemap of dealer counts by RFM segment (size = # dealers)."""
    dealers = apply_rfm_segments(dealers)
    summary = (
        dealers.groupby('rfm_segment', as_index=False)
        .agg(
            count=('customer_code', 'count'),
            total_revenue=('total_revenue', 'sum'),
            avg_R=('R_score', 'mean'),
            avg_FM=('FM_score', 'mean'),
        )
    )
    summary['pct'] = (summary['count'] / summary['count'].sum() * 100).round(1)
    summary['label'] = summary.apply(
        lambda r: f"{r['rfm_segment']}<br>{int(r['count'])} đại lý ({r['pct']}%)",
        axis=1,
    )

    order_map = {s: i for i, s in enumerate(SEGMENT_ORDER)}
    summary['_ord'] = summary['rfm_segment'].map(order_map).fillna(99)
    summary = summary.sort_values('_ord')

    colors = [SEGMENT_COLORS.get(s, '#90caf9') for s in summary['rfm_segment']]

    fig = go.Figure(
        go.Treemap(
            labels=summary['label'],
            parents=[''] * len(summary),
            values=summary['count'],
            text=summary['rfm_segment'],
            textposition='middle center',
            marker=dict(colors=colors, line=dict(width=2, color='white')),
            customdata=summary[['count', 'pct', 'total_revenue', 'avg_R', 'avg_FM']].values,
            hovertemplate=(
                '<b>%{text}</b><br>'
                'Số đại lý: %{customdata[0]}<br>'
                'Tỷ lệ: %{customdata[1]}%<br>'
                'Tổng doanh thu: %{customdata[2]:,.0f} VNĐ<br>'
                'Điểm R trung bình: %{customdata[3]:.1f}<br>'
                'Điểm F/M trung bình: %{customdata[4]:.1f}'
                '<extra></extra>'
            ),
        )
    )
    fig.update_layout(
        title='Phân khúc RFM (Recency × Frequency/Monetary)',
        height=520,
        margin=dict(t=50, l=10, r=10, b=10),
        paper_bgcolor='white',
    )
    return fig


def build_rfm_grid_scatter(dealers: pd.DataFrame) -> go.Figure:
    """Scatter of dealers on R vs FM grid (background for treemap context)."""
    dealers = apply_rfm_segments(dealers)
    fig = px.scatter(
        dealers,
        x='R_score',
        y='FM_score',
        color='rfm_segment',
        color_discrete_map=SEGMENT_COLORS,
        category_orders={'rfm_segment': SEGMENT_ORDER},
        hover_data=['customer_code', 'total_orders', 'total_revenue', 'F_score', 'M_score'],
        opacity=0.35,
        title='Vị trí đại lý trên lưới R × F/M',
        labels={'R_score': 'Recency (1–5)', 'FM_score': 'Frequency / Monetary (1–5)'},
    )
    fig.update_layout(
        height=400,
        xaxis=dict(dtick=1, range=[0.5, 5.5], constrain='domain'),
        yaxis=dict(dtick=1, range=[0.5, 5.5]),
        legend=dict(orientation='h', yanchor='bottom', y=-0.35),
    )
    return fig
