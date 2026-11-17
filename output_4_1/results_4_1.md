# Mini Project 4.1 - results

T_nominal = 50 ms, run = 20 s, 200 Monte-Carlo runs per row (P-loop ratio: 60 runs), threshold = 0.5, Kp = 30.0, plant pole +1.


## 0. Sanity check (J = 0, p = 0, c = 0)

| Config | mean interval [ms] | std interval [ms] | max overrun [ms] | % cycles missing period | % intervals >1.5T | mean act. delay [ms] | mean abs delay [ms] | max act. delay [ms] | % crossings >=1 cycle late | P-loop median RMS / ideal | % P-loop runs with RMS > 2x ideal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero-everything | 50.00 | 0.00 | 0 | 0.0 | 0.0 | +0.00 | 0.00 | 0.0 | 0.0 | 1.000 | 0 |


## 1. Configuration sweep (threshold controller + P-type loop)

| Config | mean interval [ms] | std interval [ms] | max overrun [ms] | % cycles missing period | % intervals >1.5T | mean act. delay [ms] | mean abs delay [ms] | max act. delay [ms] | % crossings >=1 cycle late | P-loop median RMS / ideal | % P-loop runs with RMS > 2x ideal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| jitter J=0.1T | 50.00 | 4.08 | 0 | 0.0 | 0.0 | +1.36 | 2.82 | 6.8 | 0.0 | 1.000 | 0 |
| jitter J=0.3T | 49.99 | 12.23 | 0 | 0.0 | 1.3 | +2.93 | 11.94 | 65.9 | 2.7 | 1.001 | 0 |
| jitter J=0.5T | 49.99 | 20.38 | 0 | 0.0 | 12.5 | +7.49 | 19.59 | 76.1 | 7.2 | 1.001 | 0 |
| overrun p=0.02 | 50.00 | 10.45 | 100 | 3.2 | 1.6 | +3.72 | 4.21 | 137.4 | 2.1 | 1.003 | 0 |
| overrun p=0.05 | 50.00 | 17.08 | 100 | 8.2 | 4.1 | +7.98 | 8.95 | 196.9 | 6.1 | 1.010 | 2 |
| overrun p=0.14 | 50.03 | 28.97 | 100 | 24.1 | 11.6 | +22.96 | 24.78 | 225.6 | 20.1 | 1.331 | 28 |
| combined J=0.3T,p=0.05 | 50.00 | 20.96 | 100 | 8.6 | 5.5 | +11.01 | 19.31 | 203.5 | 10.3 | 1.012 | 2 |
| combined J=0.5T,p=0.14 | 50.02 | 33.54 | 100 | 24.4 | 19.7 | +28.21 | 37.26 | 224.6 | 25.2 | 1.883 | 48 |

## 2. Sensitivity: threshold controller vs P-type controller

| Config | threshold: mean abs delay / T | P-loop: median RMS degradation | P-loop: % runs RMS > 2x ideal |
|---|---|---|---|
| jitter J=0.1T | 0.06 | +0.0 % | 0 % |
| jitter J=0.3T | 0.24 | +0.1 % | 0 % |
| jitter J=0.5T | 0.39 | +0.1 % | 0 % |
| overrun p=0.02 | 0.08 | +0.3 % | 0 % |
| overrun p=0.05 | 0.18 | +1.0 % | 2 % |
| overrun p=0.14 | 0.50 | +33.1 % | 28 % |
| combined J=0.3T,p=0.05 | 0.39 | +1.2 % | 2 % |
| combined J=0.5T,p=0.14 | 0.75 | +88.3 % | 48 % |

## 3. Equal average disturbance: J=0.3T (mean |jitter| = 0.15T) vs p=0.14 (mean extra delay/cycle = 0.14 x 1.1T = 0.154T)

Compare rows `jitter J=0.3T` and `overrun p=0.14` in the table of section 1.


## 4. Halving T_nominal with absolute jitter/overrun magnitudes fixed (J = 15 ms, overrun 60-150 ms, p = 0.14)

| T_nominal | relative jitter J/T | std interval / T | max overrun / T | mean abs delay [ms] | % intervals >1.5T | % cycles missing period | P-loop median RMS / ideal | % P runs RMS>2x |
|---|---|---|---|---|---|---|---|---|
| 50 ms | 0.30 | 0.61 | 2.0 | 32.22 | 12.5 | 24.3 | 1.464 | 30 |
| 25 ms | 0.60 | 1.44 | 5.0 | 41.54 | 19.9 | 57.6 | 747.071 | 100 |
| 50 ms (jitter only) | 0.30 | 0.24 | - | 11.94 | 1.3 | 0.0 | 1.001 | 0 |
| 25 ms (jitter only) | 0.60 | 0.48 | - | 9.83 | 16.8 | 0.0 | 1.000 | 0 |
