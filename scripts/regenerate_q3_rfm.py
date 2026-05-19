#!/usr/bin/env python3
"""Re-apply classic RFM segments and save Q3 parquet files."""
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dashboard'))
from rfm_utils import apply_rfm_segments

FCAST = ROOT / 'data' / 'processed' / 'forecasts'


def main():
    dealers = pd.read_parquet(FCAST / 'q3_dealer_probability.parquet')
    churn = pd.read_parquet(FCAST / 'q3_churn_risk.parquet')

    dealers = apply_rfm_segments(dealers)
    if 'rfm_segment' in churn.columns:
        churn = churn.drop(columns=['rfm_segment'], errors='ignore')
    churn = churn.merge(
        dealers[['customer_code', 'rfm_segment', 'FM_score']],
        on='customer_code',
        how='left',
    )

    dealers.to_parquet(FCAST / 'q3_dealer_probability.parquet', index=False)
    churn.to_parquet(FCAST / 'q3_churn_risk.parquet', index=False)

    print('RFM segments updated:')
    print(dealers['rfm_segment'].value_counts())
    print('Saved q3_dealer_probability.parquet and q3_churn_risk.parquet')


if __name__ == '__main__':
    main()
