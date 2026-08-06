# Corruption Flow — Comparison Report

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Repair |
|--------|----------|-----------|----------|-------------|----------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | -0.1667 | 0.1667 |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | -0.0369 | 0.0333 |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | -0.1111 | 0.1111 |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | -0.2778 | 0.2778 |

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
