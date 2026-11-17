# Mini Project 4.2 - results

Run length 300 s, on-time tolerance 10 % of the period, tail probability 0.1, tail multiplier 6-14x. Counts below are for seed 42; the summary at the end averages 30 seeds.


## fixed priority (shortest period first) - 3 streams (processor busy 43 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 228 | 69 | 3 | 24.0 | 83.9 | 1138 | 8 / 8 | 482 | 1054 |
| humidity | 500 | 600 | 377 | 190 | 33 | 37.2 | 70.7 | 1311 | 11 / 11 | 383 | 1002 |
| air quality | 250 | 1200 | 1010 | 138 | 52 | 15.8 | 22.0 | 484 | 33 / 33 | 278 | 794 |

## earliest deadline first - 3 streams (processor busy 43 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 228 | 70 | 2 | 24.0 | 80.5 | 1138 | 8 / 8 | 474 | 989 |
| humidity | 500 | 600 | 376 | 201 | 23 | 37.3 | 62.0 | 1180 | 11 / 11 | 324 | 727 |
| air quality | 250 | 1200 | 997 | 143 | 60 | 16.9 | 24.8 | 570 | 33 / 33 | 288 | 794 |

## round-robin - 3 streams (processor busy 42 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 283 | 17 | 0 | 5.7 | 17.0 | 623 | 8 / 8 | 295 | 604 |
| humidity | 500 | 600 | 500 | 96 | 4 | 16.7 | 43.7 | 662 | 11 / 11 | 249 | 492 |
| air quality | 250 | 1200 | 650 | 457 | 93 | 45.8 | 48.7 | 867 | 33 / 33 | 280 | 808 |

## fixed priority (shortest period first) - 4 streams (processor busy 56 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 202 | 95 | 3 | 32.7 | 95.2 | 1163 | 8 / 8 | 527 | 1212 |
| humidity | 500 | 600 | 210 | 354 | 36 | 65.0 | 80.3 | 1407 | 11 / 11 | 387 | 1034 |
| air quality | 250 | 1200 | 905 | 236 | 59 | 24.6 | 31.8 | 493 | 33 / 33 | 274 | 805 |
| vibration | 100 | 3000 | 2116 | 426 | 458 | 29.5 | 22.8 | 684 | 82 / 81 | 113 | 528 |

## earliest deadline first - 4 streams (processor busy 56 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 203 | 96 | 1 | 32.3 | 88.5 | 1163 | 8 / 8 | 501 | 1001 |
| humidity | 500 | 600 | 207 | 369 | 24 | 65.5 | 69.6 | 1215 | 11 / 11 | 341 | 736 |
| air quality | 250 | 1200 | 894 | 247 | 59 | 25.5 | 33.4 | 643 | 33 / 33 | 285 | 805 |
| vibration | 100 | 3000 | 2098 | 424 | 478 | 30.1 | 23.7 | 1034 | 82 / 81 | 123 | 725 |

## round-robin - 4 streams (processor busy 55 %)

| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | Mean alert latency [ms] | Max alert latency [ms] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temperature | 1000 | 300 | 282 | 18 | 0 | 6.0 | 20.1 | 642 | 8 / 8 | 298 | 616 |
| humidity | 500 | 600 | 491 | 104 | 5 | 18.2 | 45.8 | 681 | 11 / 11 | 253 | 492 |
| air quality | 250 | 1200 | 616 | 487 | 97 | 48.7 | 49.9 | 874 | 33 / 33 | 283 | 819 |
| vibration | 100 | 3000 | 1675 | 656 | 669 | 44.2 | 42.0 | 929 | 82 / 81 | 143 | 664 |

## Summary over 30 random workloads (mean % late+missed, mean alert latency in ms)

| Load | Rule | Stream | % on-time | % late | % missed | mean alert latency [ms] |
|---|---|---|---|---|---|---|
| 3 streams | FP | temperature | 72.3 | 26.9 | 0.8 | 397 |
| 3 streams | FP | humidity | 64.9 | 30.7 | 4.4 | 344 |
| 3 streams | FP | air quality | 84.9 | 12.0 | 3.1 | 216 |
| 3 streams | EDF | temperature | 72.4 | 27.2 | 0.4 | 389 |
| 3 streams | EDF | humidity | 64.5 | 32.6 | 2.8 | 327 |
| 3 streams | EDF | air quality | 84.2 | 12.1 | 3.7 | 221 |
| 3 streams | RR | temperature | 92.5 | 7.5 | 0.0 | 278 |
| 3 streams | RR | humidity | 84.1 | 15.3 | 0.6 | 280 |
| 3 streams | RR | air quality | 55.6 | 37.1 | 7.3 | 231 |
| 4 streams | FP | temperature | 64.5 | 34.5 | 1.1 | 426 |
| 4 streams | FP | humidity | 36.4 | 58.0 | 5.6 | 366 |
| 4 streams | FP | air quality | 75.4 | 20.5 | 4.1 | 220 |
| 4 streams | FP | vibration | 70.9 | 14.1 | 15.0 | 113 |
| 4 streams | EDF | temperature | 64.4 | 35.2 | 0.5 | 418 |
| 4 streams | EDF | humidity | 36.1 | 60.7 | 3.2 | 348 |
| 4 streams | EDF | air quality | 74.3 | 21.4 | 4.2 | 225 |
| 4 streams | EDF | vibration | 70.3 | 13.9 | 15.8 | 116 |
| 4 streams | RR | temperature | 91.5 | 8.5 | 0.0 | 282 |
| 4 streams | RR | humidity | 82.1 | 17.2 | 0.7 | 283 |
| 4 streams | RR | air quality | 51.7 | 40.4 | 7.9 | 233 |
| 4 streams | RR | vibration | 55.7 | 22.6 | 21.8 | 133 |
