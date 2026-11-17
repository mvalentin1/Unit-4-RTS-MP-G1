# Mini Project 4.3 - results

20000 decision events at a nominal 20 Hz, deadline 100 ms, 20 % hard decisions, baseline congestion c = 0.2.


## 1. Latency statistics at baseline congestion

| Architecture | mean [ms] | p95 [ms] | p99 [ms] | worst case [ms] | deadline compliance [%] |
|---|---|---|---|---|---|
| Edge only | 40.1 | 83.8 | 97.4 | 130 | 99.33 |
| Cloud only (c=0.2) | 68.4 | 112.4 | 176.1 | 4617 | 92.10 |
| Hybrid (hard -> cloud) | 39.4 | 78.0 | 117.4 | 4617 | 98.08 |
| Hybrid-hedged (hard -> min(edge, cloud)) | 37.4 | 71.1 | 83.3 | 130 | 99.94 |

## 2. Compliance split by decision difficulty (baseline congestion)

| Architecture | easy: compliance [%] | hard: compliance [%] | hard: p99 [ms] |
|---|---|---|---|
| Edge only | 100.00 | 96.71 | 108 |
| Cloud only (c=0.2) | 92.50 | 90.55 | 181 |
| Hybrid (hard -> cloud) | 100.00 | 90.55 | 181 |
| Hybrid-hedged (hard -> min(edge, cloud)) | 100.00 | 99.68 | 93 |

## 3. Deadline compliance [%] versus congestion level (deadline 100 ms)

| congestion c | Edge | Cloud | Hybrid | Hybrid-hedged | Cloud mean [ms] | Cloud p99 [ms] |
|---|---|---|---|---|---|---|
| 0.0 | 99.33 | 98.98 | 99.72 | 99.98 | 50.1 | 100 |
| 0.1 | 99.33 | 96.32 | 99.08 | 99.97 | 59.1 | 140 |
| 0.2 | 99.33 | 92.10 | 98.08 | 99.94 | 68.4 | 176 |
| 0.3 | 99.33 | 86.33 | 96.78 | 99.91 | 77.4 | 207 |
| 0.4 | 99.33 | 78.53 | 95.11 | 99.85 | 86.3 | 234 |
| 0.5 | 99.33 | 69.51 | 93.06 | 99.78 | 95.2 | 261 |
| 0.6 | 99.33 | 59.34 | 90.92 | 99.72 | 104.1 | 283 |
| 0.7 | 99.33 | 48.42 | 88.69 | 99.64 | 113.1 | 299 |
| 0.8 | 99.33 | 38.47 | 86.67 | 99.53 | 122.1 | 319 |
| 0.9 | 99.33 | 29.66 | 85.00 | 99.50 | 131.2 | 344 |
| 1.0 | 99.33 | 22.06 | 83.52 | 99.45 | 140.4 | 366 |

## 4. Compliance [%] versus deadline (cloud shown at c = 0 and at baseline c = 0.2)

| deadline [ms] | Edge | Cloud c=0 | Cloud c=0.2 | Hybrid c=0.2 | Hedged c=0.2 |
|---|---|---|---|---|---|
| 40 | 76.97 | 22.09 | 3.56 | 77.14 | 77.14 |
| 50 | 79.64 | 58.15 | 19.65 | 82.25 | 82.30 |
| 75 | 89.47 | 95.84 | 75.47 | 93.94 | 96.73 |
| 100 | 99.33 | 98.98 | 92.10 | 98.08 | 99.94 |
| 150 | 100.00 | 99.73 | 98.34 | 99.63 | 100.00 |
| 200 | 100.00 | 99.86 | 99.27 | 99.83 | 100.00 |
| 300 | 100.00 | 99.96 | 99.78 | 99.95 | 100.00 |

## 5. Cloud-only operating envelope

- Highest swept congestion with cloud compliance >= 99 %: None
- Highest swept congestion with cloud compliance >= 95 %: 0.1
- Edge compliance (independent of congestion): 99.33 %
