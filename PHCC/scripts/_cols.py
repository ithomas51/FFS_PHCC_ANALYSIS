import pandas as pd
files = [
    'data/cleaned/PHCC_OR_CONTRACTED_CLEAN.csv',
    'data/cleaned/PHCC_OR_PARTICIPATING_CLEAN.csv',
    'data/cleaned/PHCC_WA_PARTICIPATING_CLEAN.csv',
    'data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_COMMERCIAL.csv',
    'data/cms/CMS_2026_Q1_OR.csv',
    'data/cms/OHA_FFS_09_2025_RAW.csv',
    'data/cms/2026_CMS_HCPCS.csv',
]
for f in files:
    df = pd.read_csv(f, nrows=1, dtype=str)
    print(f"--- {f.split('/')[-1]} ---")
    for c in df.columns:
        print(f"  {c}")
    print()
