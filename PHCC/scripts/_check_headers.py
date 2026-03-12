import csv
files = [
    ("Integra Commercial", "data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_COMMERCIAL.csv"),
    ("Integra ASO", "data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_ASO.csv"),
    ("Integra Medicare", "data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_MEDICARE.csv"),
    ("Integra Medicaid", "data/INTEGRA_PHP_FFS/INTEGRA_PHP_CARVEOUTS_MEDICAID.csv"),
    ("CMS OR", "data/cms/CMS_2026_Q1_OR.csv"),
    ("CMS WA", "data/cms/CMS_2026_Q1_WA.csv"),
    ("OHA", "data/cms/OHA_FFS_09_2025_RAW.csv"),
    ("HCPCS Ref", "data/cms/2026_CMS_HCPCS.csv"),
]
for label, path in files:
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        headers = next(r)
        rows = sum(1 for _ in r)
    print(f"{label} ({rows} rows): {headers}")
