from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from ingestion.corruption import corrupt_clean_dataframe


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    clean_df = pd.DataFrame(read_json(paths.clean_json))
    print(f"Loaded {len(clean_df)} clean baseline records.")

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"Corrupted dataset: {len(corrupted_df)} records.")
    print(f"Saved: {paths.corrupted_clean_csv}")
    print(f"Saved: {paths.corrupted_clean_json}")
    print(f"Corruption log: {paths.corruption_log}")


if __name__ == "__main__":
    main()
