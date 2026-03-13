import pandas as pd
cms = pd.read_csv('data/cms/CMS_2026_Q1_WA.csv', dtype=str)
cms.columns = [c.strip() for c in cms.columns]
for code in ['L0999','L1320','L1499','L3202','L3203','L3206','L3207','L3260','L3999','L4210']:
    found = cms[cms['HCPCS']==code]
    if len(found) > 0:
        print(f'{code}: IN CMS - WA NR={found.iloc[0].get("WA (NR)", "?")}')
    else:
        print(f'{code}: NOT IN CMS')
