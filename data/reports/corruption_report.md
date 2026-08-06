# Corruption Flow — Comparison Report

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Repair |
|--------|----------|-----------|----------|-------------|----------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | -0.1667 | 0.1667 |
| `mean_token_f1` | 0.1460 | 0.7222 | 1.0000 | 0.5762 | 0.2778 |
| `judge_accuracy` | 0.0556 | 0.7222 | 1.0000 | 0.6667 | 0.2778 |
| `mean_judge_score` | 1.1111 | 3.8889 | 5 | 2.7778 | 1.1111 |

## 2. Quality Checks Comparison

| Aspect | Corrupted | Repaired |
|--------|-----------|----------|
| Checks passed | 3/6 | 6/6 |
| All passed | ❌ | ✅ |

## 3. Freshness Comparison

| Aspect | Corrupted | Repaired |
|--------|-----------|----------|
| Is fresh | 🔴 | 🟢 |
| Stale rows | 5 | 0 |

## 4. Conclusions

1. **Impact of corruption**: Data corruption affected retrieval and answer quality.
2. **Repair effectiveness**: Repairing from raw source restored data quality and metrics.
