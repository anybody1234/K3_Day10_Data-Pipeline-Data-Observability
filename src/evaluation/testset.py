from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build an evaluation test set from the cleaned dataframe."""
    if df.empty or len(df) < 2:
        raise ValueError("Need at least 2 documents to build a test set.")

    num_papers = min(6, len(df))
    step = max(1, len(df) // num_papers)
    selected_indices = list(range(0, len(df), step))[:num_papers]
    selected = df.iloc[selected_indices]

    test_set: list[dict[str, Any]] = []
    sample_id = 0

    def _safe_str(val) -> str:
        """Convert value to string, handling NaN/None."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return str(val).strip()

    for _, row in selected.iterrows():
        paper_id = _safe_str(row["paper_id"])
        title = _safe_str(row["title"])
        doc_ids = [paper_id]

        # Summary question
        sample_id += 1
        test_set.append({
            "id": f"q{sample_id:03d}",
            "question_type": "summary",
            "question": f"What is the main finding or contribution of the paper '{title}'?",
            "ground_truth": first_sentence(_safe_str(row["summary"])),
            "ground_truth_doc_ids": doc_ids,
        })

        # Authors question
        authors_joined = _safe_str(row.get("authors_joined", ""))
        if authors_joined:
            sample_id += 1
            test_set.append({
                "id": f"q{sample_id:03d}",
                "question_type": "authors",
                "question": f"Who authored the paper '{title}'?",
                "ground_truth": str(authors_joined),
                "ground_truth_doc_ids": doc_ids,
            })

        # Date question
        published = _safe_str(row.get("published", ""))
        if published:
            sample_id += 1
            test_set.append({
                "id": f"q{sample_id:03d}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": str(published),
                "ground_truth_doc_ids": doc_ids,
            })

        # Categories question
        categories_joined = _safe_str(row.get("categories_joined", ""))
        if categories_joined:
            sample_id += 1
            test_set.append({
                "id": f"q{sample_id:03d}",
                "question_type": "categories",
                "question": f"What categories or subjects does the paper '{title}' belong to?",
                "ground_truth": categories_joined,
                "ground_truth_doc_ids": doc_ids,
            })

    write_json(output_path, test_set)
    print(f"  Built test set with {len(test_set)} questions from {num_papers} papers -> {output_path}")
    return test_set
