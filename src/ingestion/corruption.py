from __future__ import annotations

import random

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate multiple data corruption scenarios."""
    random.seed(42)
    corrupted = df.copy()
    corruption_log: list[dict] = []
    n = len(corrupted)

    # 1. Drop latest records
    drop_count = min(3, n // 4)
    if drop_count > 0:
        drop_indices = corrupted.index[:drop_count].tolist()
        corrupted = corrupted.drop(drop_indices).reset_index(drop=True)
        corruption_log.append({"type": "drop_latest_records", "count": drop_count, "dropped_indices": drop_indices})
        n = len(corrupted)

    # 2. Blank summary
    blank_count = min(3, n // 4)
    if blank_count > 0 and n > 0:
        blank_indices = random.sample(range(n), blank_count)
        for idx in blank_indices:
            corrupted.at[idx, "summary"] = ""
            corrupted.at[idx, "summary_chars"] = 0
        corruption_log.append({"type": "blank_summary", "count": blank_count, "affected_indices": blank_indices})

    # 3. Inject noise
    noise_count = min(3, n // 4)
    if noise_count > 0 and n > 0:
        noise_text = " [NOISE] xyzzy lorem garble corrupted data #$%! "
        noise_indices = random.sample(range(n), noise_count)
        for idx in noise_indices:
            original = str(corrupted.at[idx, "summary"])
            corrupted.at[idx, "summary"] = original + noise_text
            corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])
        corruption_log.append({"type": "inject_noise", "count": noise_count, "affected_indices": noise_indices, "noise_text": noise_text.strip()})

    # 4. Truncate title
    truncate_count = min(2, n // 4)
    if truncate_count > 0 and n > 0:
        truncate_indices = random.sample(range(n), truncate_count)
        for idx in truncate_indices:
            original_title = str(corrupted.at[idx, "title"])
            corrupted.at[idx, "title"] = original_title[:max(10, len(original_title) // 3)]
        corruption_log.append({"type": "truncate_title", "count": truncate_count, "affected_indices": truncate_indices})

    # 5. Stale date
    stale_count = min(3, n // 4)
    if stale_count > 0 and n > 0:
        stale_indices = random.sample(range(n), stale_count)
        for idx in stale_indices:
            corrupted.at[idx, "published"] = "2020-01-01"
            corrupted.at[idx, "age_days"] = 2000
        corruption_log.append({"type": "stale_date", "count": stale_count, "affected_indices": stale_indices, "stale_date": "2020-01-01"})

    # 6. Duplicate rows
    dupe_count = min(3, n // 4)
    if dupe_count > 0 and n > 0:
        dupe_indices = random.sample(range(n), dupe_count)
        dupes = corrupted.iloc[dupe_indices].copy()
        corrupted = pd.concat([corrupted, dupes], ignore_index=True)
        corruption_log.append({"type": "duplicate_rows", "count": dupe_count, "duplicated_indices": dupe_indices})

    # Rebuild text_for_embedding
    def _rebuild_text(row):
        parts = [str(row.get("title", ""))]
        summary = str(row.get("summary", ""))
        authors = str(row.get("authors_joined", ""))
        parts.append(summary)
        if authors:
            parts.append(f"Authors: {authors}")
        return ". ".join(p for p in parts if p)

    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text, axis=1)

    log_payload = {
        "total_corruptions": len(corruption_log),
        "original_rows": len(df),
        "corrupted_rows": len(corrupted),
        "corruptions": corruption_log,
    }
    write_json(output_log_path, log_payload)
    print(f"  Applied {len(corruption_log)} corruption types, {len(df)} -> {len(corrupted)} rows")
    print(f"  Corruption log -> {output_log_path}")

    return corrupted
