from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in records])

    df["title"] = df["title"].apply(normalize_whitespace)
    df["summary"] = df["summary"].apply(normalize_whitespace)

    df = df[df["title"].str.strip().astype(bool) & df["summary"].str.strip().astype(bool)].copy()
    df.drop_duplicates(subset="paper_id", keep="first", inplace=True)

    df["authors_joined"] = df["authors"].apply(compact_join)
    df["categories_joined"] = df["categories"].apply(compact_join)
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = (
        df["title"] + ". " + df["summary"] + " Authors: " + df["authors_joined"]
    )

    df["published"] = pd.to_datetime(df["published"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce").dt.strftime("%Y-%m-%d")
    pub_dt = pd.to_datetime(df["published"], errors="coerce")
    run_naive = run_date.replace(tzinfo=None)
    df["age_days"] = (run_naive - pub_dt).dt.days

    df.sort_values("published", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    df.drop(columns=["authors", "categories"], inplace=True)
    return df
