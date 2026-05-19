# Thống Nhất Bike - Dự báo nhu cầu Q2/2026

Pipeline dự báo nhu cầu cho Thống Nhất Bike (xe đạp) - Hạng mục C: Dự báo nhu cầu & Chiến lược.

## Cấu trúc dự án

```
├── data/                     # Dữ liệu
│   ├── *.xlsx                # File gốc
│   └── processed/            # Parquet đã xử lý
│       └── forecasts/        # Kết quả dự báo
├── notebooks/                # Jupyter notebooks
│   ├── 01_data_cleaning_eda.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_forecasting_models.ipynb
│   └── 04_llm_integration.ipynb
├── dashboard/                # Plotly Dash app
│   ├── app.py
│   └── pages/
└── requirements.txt
```

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy notebooks

```bash
cd notebooks
jupyter notebook
# Chạy lần lượt: 01 -> 02 -> 03 -> 04
```

## Chạy dashboard

```bash
python dashboard/app.py
# Mở http://localhost:8050
```

## Ba câu hỏi dự báo

1. **Dự báo doanh số Q2/2026** - Prophet + LightGBM, top 20 SKU, phân tích theo 5 nhóm SP
2. **Dự báo màu sắc** - Xu hướng theo mùa, tỷ trọng Q2, SKU bán chậm
3. **Dự báo đại lý** - XGBoost P(đặt hàng 30 ngày), RFM, ma trận tiếp thị

## LLM Integration

Thêm Groq API key vào `.env`:
```
GROQ_API_KEY=your_key_here
```
Sau đó chạy lại `04_llm_integration.ipynb`.

## Deploy

Deploy lên Render.com:
1. Push code lên GitHub
2. Tạo Web Service trên Render, trỏ đến repo
3. Thêm biến môi trường `GROQ_API_KEY`
