#!/usr/bin/env python3
"""
Mini Project 4.1 - Simulating sampling jitter and processing overruns in an
embedded sensing-and-control loop (Unit 4, Sections 4.1, 4.5, 4.7).

Timing model (documented assumptions)
-------------------------------------
* Cycle k is RELEASED at r_k = k * T_nominal (the nominal scan/sampling schedule).
* Sampling jitter:   the sample is taken at  s_k = max(r_k + jitter_k, f_{k-1})
                     with jitter_k ~ U(-J, +J).  A cycle can never start before
                     the previous one has finished (single processing loop).
* Computation time:  c_k is usually short (U(0.5, 2) ms).  With probability
                     p_over it is drawn from the overrun range U(60, 150) ms, i.e. it
                     exceeds T_nominal = 50 ms (a WCET violation, Section 4.1).
* Finish / actuation: f_k = s_k + c_k.  The controller can only act at f_k.
  Because s_{k+1} >= f_k, an overrun pushes the following cycles back exactly
  like an overrunning PLC scan delays the next scan (Section 4.5); the schedule
  then catches up because later cycles run back-to-back until the backlog drains.
* Ideal baseline: s_k = r_k, c_k = 0 (zero-jitter, zero-overrun scan cycle).

Run:  python rt_sampling_sim.py      (writes figures + results into ./output_4_1)
"""
import math
import os
import random
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------- parameters
T_NOM = 0.05            # nominal sampling period [s]  (20 Hz)
RUN_LEN = 20.0          # simulated run length [s]
SIG_AMP, SIG_PERIOD = 1.0, 4.0
THRESHOLD, HYST = 0.5, 0.10     # controller threshold and re-arm hysteresis
C_TYP = (0.0005, 0.002)         # typical computation time range [s]
OVER_RANGE = (0.060, 0.150)     # overrun computation time range [s] (absolute)
MATCH_WINDOW = 1.0              # max |actuation difference| to pair crossings [s]
KP, A_PLANT, B_GAIN = 30.0, 1.0, 1.0  # P-type loop: y' = +A*y + B*u + d(t), u = -KP*y (open-loop UNSTABLE plant)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_4_1")
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------- the plant
def clean_signal(t):
    """Noise-free process value (also used as the disturbance of the P-loop)."""
    return SIG_AMP * math.sin(2 * math.pi * t / SIG_PERIOD)


def true_signal(t):
    """Sine wave plus small continuous (deterministic) noise, as a sensor sees it.
    The noise is a sum of two fast sinusoids so that the ideal and jittered runs
    observe exactly the same underlying analogue quantity."""
    return (clean_signal(t)
            + 0.020 * math.sin(2 * math.pi * 3.7 * t + 0.5)
            + 0.015 * math.sin(2 * math.pi * 9.1 * t + 1.3))


# ---------------------------------------------------------------- the loop sim
def simulate(T=T_NOM, run=RUN_LEN, J=0.0, p_over=0.0, rng=None, ideal=False,
             c_typ=C_TYP, over_range=OVER_RANGE):
    """Event loop. Returns per-cycle lists: release, start(sample time), finish,
    jitter, computation time, overrun flag, sampled value."""
    rng = rng or random.Random(0)
    n = int(round(run / T))
    rel, start, fin, jit, comp, over, val = [], [], [], [], [], [], []
    prev_f = 0.0
    for k in range(n):
        r = k * T
        if ideal:
            j, c, ov = 0.0, 0.0, False
        else:
            j = rng.uniform(-J, J) if J > 0 else 0.0
            ov = rng.random() < p_over
            c = rng.uniform(*over_range) if ov else rng.uniform(*c_typ)
        s = max(r + j, prev_f, 0.0)          # cannot start before previous cycle ends
        f = s + c
        prev_f = f
        rel.append(r); start.append(s); fin.append(f)
        jit.append(j); comp.append(c); over.append(ov); val.append(true_signal(s))
    return dict(T=T, rel=rel, start=start, fin=fin, jit=jit, comp=comp, over=over, val=val)


# ------------------------------------------------------------------ controller
def threshold_controller(sim):
    """Issue an actuation command the first time a sample reaches THRESHOLD from
    below; re-arm only after the signal falls below THRESHOLD-HYST (no chatter).
    Returns list of (sample_time, actuation_time)."""
    armed, events = True, []
    for s, f, y in zip(sim["start"], sim["fin"], sim["val"]):
        if armed and y >= THRESHOLD:
            events.append((s, f)); armed = False
        elif y < THRESHOLD - HYST:
            armed = True
    return events


def match_actuations(ideal_ev, real_ev):
    """Pair every ideal actuation with the nearest real one; return signed delays
    (real - ideal) and the number of ideal crossings with no partner (missed)."""
    delays, missed = [], 0
    real_t = [a for _, a in real_ev]
    for _, a_ideal in ideal_ev:
        cand = [a for a in real_t if abs(a - a_ideal) <= MATCH_WINDOW]
        if not cand:
            missed += 1
            continue
        a = min(cand, key=lambda x: abs(x - a_ideal))
        delays.append(a - a_ideal)
    return delays, missed


# --------------------------------------------------------------- P-type control
def p_loop_rms(sim):
    """Closed loop with a proportional rule.  At each sample instant s_k the
    controller reads y; the new command u=-KP*y is only APPLIED at f_k and held
    (zero-order hold) until the next actuation.  Plant: y' = A*y + B*u + d(t) with A=+1
    (open-loop unstable, so timing quality really matters), d(t)=clean_signal(t).
    Returns RMS of y over the run."""
    y, t, u, acc = 0.0, 0.0, 0.0, 0.0

    def step_to(t_end, y, u, acc):
        nonlocal t
        dt_total = t_end - t
        if dt_total <= 0:
            return y, acc
        n = max(1, int(math.ceil(dt_total / 0.005)))
        h = dt_total / n
        for _ in range(n):  # midpoint (RK2) integration
            f1 = A_PLANT * y + B_GAIN * u + clean_signal(t)
            ym = y + 0.5 * h * f1
            f2 = A_PLANT * ym + B_GAIN * u + clean_signal(t + 0.5 * h)
            acc += y * y * h
            y += h * f2
            t += h
        return y, acc

    for s, f in zip(sim["start"], sim["fin"]):
        y, acc = step_to(s, y, u, acc)
        u_new = -KP * y                      # computed from the sample
        y, acc = step_to(f, y, u, acc)       # old command still applied until f
        u = u_new
    run_end = sim["rel"][-1] + sim["T"]
    y, acc = step_to(max(run_end, t), y, u, acc)
    return math.sqrt(acc / t)


# ------------------------------------------------------------- statistics
def timing_stats(sim):
    s, T = sim["start"], sim["T"]
    iv = [b - a for a, b in zip(s, s[1:])]
    over_amt = [max(c - T, 0.0) for c in sim["comp"]]
    missed = sum(1 for k, f in enumerate(sim["fin"]) if f > (k + 1) * T + 1e-12)
    return dict(
        mean_iv=st.mean(iv), std_iv=st.pstdev(iv), max_over=max(over_amt),
        pct_missed=100.0 * missed / len(sim["fin"]),
        pct_15T=100.0 * sum(1 for x in iv if x > 1.5 * T) / len(iv),
        n_over=sum(sim["over"]))


def monte_carlo(T=T_NOM, J=0.0, p_over=0.0, runs=200, with_p=True, seed0=1000,
                c_typ=C_TYP, over_range=OVER_RANGE):
    """Aggregate over many random runs (a 20 s run only has 5 threshold
    crossings, so single runs are very noisy)."""
    agg = {k: [] for k in ("mean_iv", "std_iv", "max_over", "pct_missed", "pct_15T")}
    delays_all, missed_tot, cross_tot, rms_ratio = [], 0, 0, []
    ideal = simulate(T=T, ideal=True)
    ideal_ev = threshold_controller(ideal)
    rms_ideal = p_loop_rms(ideal) if with_p else None
    for i in range(runs):
        rng = random.Random(seed0 + i)
        sim = simulate(T=T, J=J, p_over=p_over, rng=rng, c_typ=c_typ, over_range=over_range)
        ts = timing_stats(sim)
        for k in agg:
            agg[k].append(ts[k])
        d, m = match_actuations(ideal_ev, threshold_controller(sim))
        delays_all += d; missed_tot += m; cross_tot += len(ideal_ev)
        if with_p and i < 60:
            rms_ratio.append(p_loop_rms(sim) / rms_ideal)
    out = dict(
        mean_iv_ms=1e3 * st.mean(agg["mean_iv"]), std_iv_ms=1e3 * st.mean(agg["std_iv"]),
        max_over_ms=1e3 * max(agg["max_over"]), pct_missed=st.mean(agg["pct_missed"]),
        pct_15T=st.mean(agg["pct_15T"]),
        mean_delay_ms=1e3 * st.mean(delays_all) if delays_all else float("nan"),
        mean_abs_delay_ms=1e3 * st.mean(abs(x) for x in delays_all) if delays_all else float("nan"),
        max_delay_ms=1e3 * max(delays_all) if delays_all else float("nan"),
        pct_late_cycle=100.0 * sum(1 for x in delays_all if x >= T) / max(1, len(delays_all)),
        pct_missed_cross=100.0 * missed_tot / max(1, cross_tot),
        p_rms_ratio=st.median(rms_ratio) if rms_ratio else float("nan"),
        p_bad=100.0 * sum(1 for x in rms_ratio if x > 2.0) / max(1, len(rms_ratio)))
    return out


# -------------------------------------------------------------------- figures
def make_figures(name, title, J, p_over, seed=7):
    ideal = simulate(ideal=True)
    real = simulate(J=J, p_over=p_over, rng=random.Random(seed))
    ev_i, ev_r = threshold_controller(ideal), threshold_controller(real)
    delays, _ = match_actuations(ev_i, ev_r)

    # ---- Figure 1: signal + samples, and per-cycle interval deviation
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5))
    tt = [i * 0.002 for i in range(int(RUN_LEN / 0.002))]
    ax1.plot(tt, [true_signal(t) for t in tt], color="0.6", lw=1.2, label="true signal")
    ax1.plot(ideal["start"], ideal["val"], "o", ms=3.5, color="tab:blue", label="ideal samples")
    ax1.plot(real["start"], real["val"], "x", ms=4, color="tab:red", label="jittered/overrun samples")
    ax1.axhline(THRESHOLD, color="k", ls=":", lw=0.8, label="threshold")
    ax1.set_xlim(0, 10); ax1.set_xlabel("time [s]  (first 10 s shown for legibility)")
    ax1.set_ylabel("signal"); ax1.set_title(f"Figure 1 - {title}"); ax1.legend(loc="lower center", ncol=4, fontsize=8, framealpha=0.9)
    iv = [b - a for a, b in zip(real["start"], real["start"][1:])]
    dev = [1e3 * (x - T_NOM) for x in iv]
    ax2.plot(range(1, len(dev) + 1), dev, lw=0.9, color="tab:purple")
    ax2.axhline(0, color="k", lw=1)
    ov_idx = [k for k, o in enumerate(real["over"]) if o and k < len(dev)]
    ax2.plot([k + 1 for k in ov_idx], [dev[k] for k in ov_idx], "v", color="tab:red", ms=5,
             label="interval after an overrun cycle")
    ax2.set_xlabel("cycle index k"); ax2.set_ylabel("inter-sample interval - T_nominal [ms]")
    if ov_idx: ax2.legend(loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"fig1_{name}.png"), dpi=130); plt.close(fig)

    # ---- Figure 2: actuation instants on a shared time axis
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(tt, [0.5 * true_signal(t) + 1.5 for t in tt], color="0.8", lw=1)
    ax.plot([a for _, a in ev_i], [1] * len(ev_i), "o", color="tab:blue", ms=9, label="ideal actuation")
    ax.plot([a for _, a in ev_r], [2] * len(ev_r), "s", color="tab:red", ms=8, label="jittered/overrun actuation")
    for (_, a1), (_, a2) in zip(ev_i, ev_r):
        ax.annotate("", xy=(a2, 2), xytext=(a1, 1), arrowprops=dict(arrowstyle="-", color="0.5", lw=0.8))
    txt = (f"mean delay = {1e3 * st.mean(delays):+.1f} ms\nmax delay = {1e3 * max(delays):+.1f} ms"
           if delays else "no matched crossings")
    ax.text(0.01, 0.92, txt, transform=ax.transAxes, va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="w", ec="0.5"))
    ax.set_yticks([1, 2]); ax.set_yticklabels(["ideal", "real"]); ax.set_ylim(0.4, 2.8)
    ax.set_xlim(0, RUN_LEN); ax.set_xlabel("time [s]"); ax.legend(loc="upper right", ncol=2)
    ax.set_title(f"Figure 2 - actuation instants: {title}")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"fig2_{name}.png"), dpi=130); plt.close(fig)


# ----------------------------------------------------------------------- main
def fmt_row(label, r):
    return (f"| {label} | {r['mean_iv_ms']:.2f} | {r['std_iv_ms']:.2f} | {r['max_over_ms']:.0f} | "
            f"{r['pct_missed']:.1f} | {r['pct_15T']:.1f} | {r['mean_delay_ms']:+.2f} | "
            f"{r['mean_abs_delay_ms']:.2f} | {r['max_delay_ms']:.1f} | {r['pct_late_cycle']:.1f} | "
            f"{r['p_rms_ratio']:.3f} | {r['p_bad']:.0f} |")


HDR = ("| Config | mean interval [ms] | std interval [ms] | max overrun [ms] | % cycles missing period | "
       "% intervals >1.5T | mean act. delay [ms] | mean abs delay [ms] | max act. delay [ms] | "
       "% crossings >=1 cycle late | P-loop median RMS / ideal | % P-loop runs with RMS > 2x ideal |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|")


def main():
    T = T_NOM
    lines = ["# Mini Project 4.1 - results\n",
             f"T_nominal = {T*1e3:.0f} ms, run = {RUN_LEN:.0f} s, 200 Monte-Carlo runs per row "
             f"(P-loop ratio: 60 runs), threshold = {THRESHOLD}, Kp = {KP}, plant pole +1.\n"]

    # sanity check
    z = monte_carlo(J=0.0, p_over=0.0, runs=5, with_p=True, c_typ=(0.0, 0.0))
    lines += ["\n## 0. Sanity check (J = 0, p = 0, c = 0)\n", HDR, fmt_row("zero-everything", z), ""]

    # sweep
    sweep = [("jitter J=0.1T", dict(J=0.1 * T)), ("jitter J=0.3T", dict(J=0.3 * T)),
             ("jitter J=0.5T", dict(J=0.5 * T)),
             ("overrun p=0.02", dict(p_over=0.02)), ("overrun p=0.05", dict(p_over=0.05)),
             ("overrun p=0.14", dict(p_over=0.14)),
             ("combined J=0.3T,p=0.05", dict(J=0.3 * T, p_over=0.05)),
             ("combined J=0.5T,p=0.14", dict(J=0.5 * T, p_over=0.14))]
    res = {}
    for lab, kw in sweep:
        res[lab] = monte_carlo(**kw)
    lines += ["\n## 1. Configuration sweep (threshold controller + P-type loop)\n", HDR]
    lines += [fmt_row(l, res[l]) for l, _ in sweep]

    # P-controller sensitivity
    lines += ["\n## 2. Sensitivity: threshold controller vs P-type controller\n",
              "| Config | threshold: mean abs delay / T | P-loop: median RMS degradation | P-loop: % runs RMS > 2x ideal |", "|---|---|---|---|"]
    for l, _ in sweep:
        r = res[l]
        lines.append(f"| {l} | {r['mean_abs_delay_ms']/(T*1e3):.2f} | {100*(r['p_rms_ratio']-1):+.1f} % | {r['p_bad']:.0f} % |")

    # matched disturbance
    lines += ["\n## 3. Equal average disturbance: J=0.3T (mean |jitter| = 0.15T) vs p=0.14 "
              "(mean extra delay/cycle = 0.14 x 1.1T = 0.154T)\n",
              "Compare rows `jitter J=0.3T` and `overrun p=0.14` in the table of section 1.\n"]

    # halve T
    lines += ["\n## 4. Halving T_nominal with absolute jitter/overrun magnitudes fixed "
              "(J = 15 ms, overrun 60-150 ms, p = 0.14)\n",
              "| T_nominal | relative jitter J/T | std interval / T | max overrun / T | mean abs delay [ms] | "
              "% intervals >1.5T | % cycles missing period | P-loop median RMS / ideal | % P runs RMS>2x |", "|---|---|---|---|---|---|---|---|---|"]
    for Tn in (0.05, 0.025):
        r = monte_carlo(T=Tn, J=0.015, p_over=0.14)
        lines.append(f"| {Tn*1e3:.0f} ms | {0.015/Tn:.2f} | {r['std_iv_ms']/(Tn*1e3):.2f} | "
                     f"{r['max_over_ms']/(Tn*1e3):.1f} | {r['mean_abs_delay_ms']:.2f} | {r['pct_15T']:.1f} | "
                     f"{r['pct_missed']:.1f} | {r['p_rms_ratio']:.3f} | {r['p_bad']:.0f} |")
    for Tn in (0.05, 0.025):
        r = monte_carlo(T=Tn, J=0.015, p_over=0.0)
        lines.append(f"| {Tn*1e3:.0f} ms (jitter only) | {0.015/Tn:.2f} | {r['std_iv_ms']/(Tn*1e3):.2f} | "
                     f"- | {r['mean_abs_delay_ms']:.2f} | {r['pct_15T']:.1f} | {r['pct_missed']:.1f} | "
                     f"{r['p_rms_ratio']:.3f} | {r['p_bad']:.0f} |")

    # figures for three configurations
    make_figures("jitter30", "jitter only, J = 0.3 T", 0.3 * T, 0.0)
    make_figures("overrun14", "overruns only, p = 0.14", 0.0, 0.14)
    make_figures("combined", "jitter J = 0.3 T + overruns p = 0.05", 0.3 * T, 0.05)

    with open(os.path.join(OUT, "results_4_1.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
