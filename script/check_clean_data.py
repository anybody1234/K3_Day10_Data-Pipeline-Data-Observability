import pandas as pd
import json

df = pd.read_csv('data/clean/papers_clean.csv')
print('=== CSV Analysis ===')
print(f'Rows: {len(df)}')
print(f'Columns ({len(df.columns)}): {list(df.columns)}')
print()

required = ['paper_id', 'title', 'summary', 'text_for_embedding', 'age_days', 'published', 'authors_joined', 'categories_joined', 'summary_chars']
for col in required:
    if col in df.columns:
        nulls = int(df[col].isna().sum())
        empty = int((df[col].astype(str).str.strip() == '').sum()) if df[col].dtype == 'object' else 0
        print(f'  {col}: nulls={nulls}, empty={empty}')
    else:
        print(f'  {col}: MISSING!')

print()
print('=== Sample text_for_embedding (row 0) ===')
print(repr(df['text_for_embedding'].iloc[0][:200]))
print()

with open('data/clean/papers_clean.json', 'r', encoding='utf-8') as f:
    jdata = json.load(f)
print(f'=== JSON Analysis ===')
print(f'JSON records: {len(jdata)}')
if jdata:
    print(f'JSON keys: {list(jdata[0].keys())}')
print()

dupes = int(df['paper_id'].duplicated().sum())
print(f'Duplicate paper_id: {dupes}')
print(f'age_days range: [{df["age_days"].min()}, {df["age_days"].max()}]')
print(f'published range: [{df["published"].min()}, {df["published"].max()}]')
print(f'summary_chars range: [{df["summary_chars"].min()}, {df["summary_chars"].max()}]')
