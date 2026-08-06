from __future__ import annotations

import random
import string
from datetime import timedelta
from pathlib import Path

import pandas as pd

from core.utils import now_utc, write_json

_SEED = 42
_DROP_LATEST_FRACTION = 0.15
_BLANK_SUMMARY_FRACTION = 0.15
_NOISY_SUMMARY_FRACTION = 0.15
_TRUNCATE_TITLE_FRACTION = 0.15
_STALE_DATE_FRACTION = 0.15
_DUPLICATE_FRACTION = 0.15
_STALE_MIN_DAYS = 500
_STALE_MAX_DAYS = 1500
_NOISE_ALPHABET = string.ascii_letters + string.digits + "@#$%^&*!?"


def _count(total: int, fraction: float, available: int) -> int:
    return min(available, max(1, round(total * fraction)))


def _take(pool: list[int], total: int, fraction: float) -> list[int]:
    n = _count(total, fraction, len(pool))
    taken, pool[:n] = pool[:n], []
    return taken


def _noise_token(rng: random.Random) -> str:
    length = rng.randint(8, 16)
    return "".join(rng.choice(_NOISE_ALPHABET) for _ in range(length))


def _inject_noise(text: str, rng: random.Random) -> str:
    words = text.split()
    noise = _noise_token(rng)
    if not words:
        return noise
    words.insert(rng.randint(0, len(words)), noise)
    return " ".join(words)


def _truncate(title: str, rng: random.Random) -> str:
    keep = max(5, len(title) // rng.randint(3, 5))
    return title[:keep].rstrip()


def _stale_published(rng: random.Random, run_date) -> str:
    offset = timedelta(days=rng.randint(_STALE_MIN_DAYS, _STALE_MAX_DAYS))
    return (run_date - offset).strftime("%Y-%m-%d")


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    rng = random.Random(_SEED)
    run_date = now_utc()
    corrupted = df.reset_index(drop=True).copy()
    rows_before = len(corrupted)

    drop_count = min(_count(rows_before, _DROP_LATEST_FRACTION, rows_before), max(0, rows_before - 1))
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)

    pool = list(corrupted.index)
    rng.shuffle(pool)
    blank_idx = _take(pool, rows_before, _BLANK_SUMMARY_FRACTION)
    noisy_idx = _take(pool, rows_before, _NOISY_SUMMARY_FRACTION)
    truncate_idx = _take(pool, rows_before, _TRUNCATE_TITLE_FRACTION)
    stale_idx = _take(pool, rows_before, _STALE_DATE_FRACTION)

    blank_ids = corrupted.loc[blank_idx, "paper_id"].tolist()
    corrupted.loc[blank_idx, "summary"] = ""

    noisy_ids = corrupted.loc[noisy_idx, "paper_id"].tolist()
    corrupted.loc[noisy_idx, "summary"] = [
        _inject_noise(text, rng) for text in corrupted.loc[noisy_idx, "summary"]
    ]

    truncated_ids = corrupted.loc[truncate_idx, "paper_id"].tolist()
    corrupted.loc[truncate_idx, "title"] = [
        _truncate(text, rng) for text in corrupted.loc[truncate_idx, "title"]
    ]

    stale_ids = corrupted.loc[stale_idx, "paper_id"].tolist()
    stale_published_before = corrupted.loc[stale_idx, "published"].tolist()
    corrupted.loc[stale_idx, "published"] = [_stale_published(rng, run_date) for _ in stale_idx]

    dup_count = min(len(corrupted), max(1, round(rows_before * _DUPLICATE_FRACTION)))
    dup_idx = rng.sample(list(corrupted.index), dup_count) if dup_count else []
    duplicated_ids = corrupted.loc[dup_idx, "paper_id"].tolist()
    corrupted = pd.concat([corrupted, corrupted.loc[dup_idx]], ignore_index=True)

    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = (
        corrupted["title"] + ". " + corrupted["summary"] + " Authors: " + corrupted["authors_joined"]
    )
    pub_dt = pd.to_datetime(corrupted["published"], errors="coerce")
    corrupted["age_days"] = (run_date.replace(tzinfo=None) - pub_dt).dt.days

    write_json(
        Path(output_log_path),
        {
            "generated_at": run_date.isoformat(),
            "seed": _SEED,
            "rows_before": rows_before,
            "rows_after": len(corrupted),
            "operations": {
                "dropped_latest_records": {"count": len(dropped_ids), "paper_ids": dropped_ids},
                "blanked_summary": {"count": len(blank_ids), "paper_ids": blank_ids},
                "noisy_summary": {"count": len(noisy_ids), "paper_ids": noisy_ids},
                "truncated_title": {"count": len(truncated_ids), "paper_ids": truncated_ids},
                "stale_published_date": {
                    "count": len(stale_ids),
                    "paper_ids": stale_ids,
                    "published_before": stale_published_before,
                },
                "duplicated_rows": {"count": len(duplicated_ids), "paper_ids": duplicated_ids},
            },
        },
    )
    return corrupted
