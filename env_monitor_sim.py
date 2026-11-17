#!/usr/bin/env python3
"""
Mini Project 4.2 - Multi-rate environmental monitoring pipeline with timing-
compliance reporting (Unit 4, Sections 4.1 and 4.2).

One embedded gateway, ONE processing loop, several sensor streams with different
required sampling periods.  The loop is non-preemptive: once a sensor read +
processing step starts it runs to completion (like a CAN frame, Section 4.2).

Documented model
----------------
* Stream i has required period P_i.  Its n-th sample is RELEASED at r = n*P_i and
  has deadline r + P_i (the release of the next sample).
* When the processor becomes idle at time t, every stream whose latest release
  r <= t and which has not yet been serviced is "pending".  The scheduling rule picks
  ONE pending stream (not "service everything every pass"):
    - FP  : fixed priority, shortest period first (rate-monotonic priority)
    - EDF : earliest absolute deadline first among pending streams
    - RR  : round-robin over the streams (fairness, ignores rates)
* Servicing starts at s (the acquisition instant), takes c (random, with an
  occasional long tail = overrun) and ends at f = s + c.  The alert rule runs on the
  sample right after it is processed, so the alert is logged at time f.
* Classification of each REQUIRED sample n (lateness L = s - r):
    on-time : serviced with L <= 10 % of P_i
    late    : serviced with 10 % P_i < L < P_i
    missed  : not started before the next release arrives (it is overwritten/dropped)
* Period overrun = max(0, (s_n - s_prev_serviced) - P_i) for consecutive serviced
  samples (a missed sample therefore shows up as an overrun of one period).
* Common random numbers: the processing time of sample n of stream i is drawn
  once, so every scheduling rule faces exactly the same workload.

Run:  python env_monitor_sim.py     (writes figures + report into ./output_4_2)
"""
import heapq
import math
import os
import random
import statistics as st
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_4_2")
os.makedirs(OUT, exist_ok=True)
RUN_LEN = 300.0          # simulated seconds
ON_TIME_FRAC = 0.10      # on-time tolerance as a fraction of the period
TAIL_PROB = 0.10         # probability that a read hits the long tail (overrun)
TAIL_MULT = (6.0, 14.0)  # tail multiplies the normal processing time


@dataclass
class Stream:
    name: str
    period: float                 # required sampling period [s]
    proc: tuple                   # normal processing time range [s]
    sig_period: float             # period of the synthetic physical signal [s]
    amp: float
    threshold: float              # alert threshold (upward crossing)
    phase: float = 0.0
    # running state / counters
    next_n: int = 0
    on_time: int = 0
    late: int = 0
    missed: int = 0
    last_start: float = None
    overruns: list = field(default_factory=list)
    lateness: list = field(default_factory=list)
    samples: list = field(default_factory=list)      # (start, value, cls)
    missed_rel: list = field(default_factory=list)   # release times of missed samples
    armed: bool = True
    alerts: list = field(default_factory=list)       # (detect_time, true_cross_time)

    def clean(self, t):
        return self.amp * math.sin(2 * math.pi * t / self.sig_period + self.phase)

    def value(self, t):
        return self.clean(t) + 0.01 * self.amp * math.sin(2 * math.pi * 3.1 * t + 1.0)

    def true_crossings(self, run):
        """Analytic upward crossing times of the noise-free signal."""
        x0 = math.asin(self.threshold / self.amp)
        out, k = [], -1
        while True:
            t = ((x0 - self.phase) + 2 * math.pi * k) * self.sig_period / (2 * math.pi)
            if t > run:
                break
            if t >= 0:
                out.append(t)
            k += 1
        return out

    def reset(self):
        self.next_n = 0; self.on_time = self.late = self.missed = 0
        self.last_start = None; self.overruns = []; self.lateness = []
        self.samples = []; self.missed_rel = []; self.armed = True; self.alerts = []


def make_streams(load):
    s = [Stream("temperature", 1.00, (0.015, 0.045), 37.0, 1.0, 0.6),
         Stream("humidity",    0.50, (0.010, 0.030), 27.3, 1.0, 0.6, 0.2),
         Stream("air quality", 0.25, (0.025, 0.055), 9.1, 1.0, 0.6, 0.5)]
    if load == 4:
        s.append(Stream("vibration", 0.10, (0.005, 0.012), 3.7, 1.0, 0.6, 0.4))
    return s


def draw_workload(streams, seed):
    """Pre-draw processing time of every possible sample (common random numbers)."""
    rng = random.Random(seed)
    table = []
    for s in streams:
        n_max = int(RUN_LEN / s.period) + 5
        row = []
        for _ in range(n_max):
            c = rng.uniform(*s.proc)
            if rng.random() < TAIL_PROB:
                c *= rng.uniform(*TAIL_MULT)
            row.append(c)
        table.append(row)
    return table


def run(streams, rule, workload, run_len=RUN_LEN):
    for s in streams:
        s.reset()
    n_s = len(streams)
    rr_ptr = 0
    t = 0.0
    busy = 0.0
    while t < run_len:
        # 1) drop samples whose deadline (= next release) has already passed
        pend = []
        for i, s in enumerate(streams):
            n_latest = int(t / s.period + 1e-9)
            while s.next_n < n_latest:
                s.missed += 1
                s.missed_rel.append(s.next_n * s.period)
                s.next_n += 1
            if s.next_n <= n_latest and s.next_n * s.period <= t + 1e-12 \
                    and (s.next_n + 1) * s.period <= run_len + 1e-9:
                pend.append(i)
        # 2) idle: jump to the next release
        if not pend:
            nxt = min(s.next_n * s.period for s in streams)
            t = max(t, nxt) if nxt > t else t + 1e-6
            continue
        # 3) pick one stream with the documented rule (heap keyed by the rule)
        heap = []
        for i in pend:
            s = streams[i]
            if rule == "FP":
                key = (s.period, i)
            elif rule == "EDF":
                key = ((s.next_n + 1) * s.period, i)
            elif rule == "RR":
                key = ((i - rr_ptr) % n_s, i)
            else:
                raise ValueError(rule)
            heapq.heappush(heap, (key, i))
        _, i = heapq.heappop(heap)
        rr_ptr = (i + 1) % n_s
        s = streams[i]
        n = s.next_n
        rel = n * s.period
        start = t
        c = workload[i][n]
        fin = start + c
        busy += c
        L = start - rel
        cls = "on-time" if L <= ON_TIME_FRAC * s.period + 1e-12 else "late"
        if cls == "on-time":
            s.on_time += 1
        else:
            s.late += 1
        s.lateness.append(L)
        if s.last_start is not None:
            s.overruns.append(max(0.0, (start - s.last_start) - s.period))
        s.last_start = start
        v = s.value(start)
        s.samples.append((start, v, cls))
        # alert evaluated right after the sample has been processed (time = fin)
        if s.armed and v >= s.threshold:
            tc = s.true_crossings(run_len + s.sig_period)
            true_t = min(tc, key=lambda x: abs(x - start)) if tc else float("nan")  # nearest true crossing
            s.alerts.append((fin, true_t))
            s.armed = False
        elif v < s.threshold - 0.1 * s.amp:
            s.armed = True
        s.next_n = n + 1
        t = fin
    # samples still unaccounted whose deadline falls inside the run are missed
    for s in streams:
        n_req = int(run_len / s.period + 1e-9)
        while s.next_n < n_req:
            s.missed += 1
            s.missed_rel.append(s.next_n * s.period)
            s.next_n += 1
    return busy / run_len


def report_rows(streams):
    rows = []
    for s in streams:
        req = s.on_time + s.late + s.missed
        lat = [d - tt for d, tt in s.alerts if not math.isnan(tt)]
        rows.append(dict(
            name=s.name, period=s.period, req=req, on=s.on_time, late=s.late, miss=s.missed,
            pct_bad=100.0 * (s.late + s.missed) / max(1, req),
            mean_ov=1e3 * st.mean(s.overruns) if s.overruns else 0.0,
            max_ov=1e3 * max(s.overruns) if s.overruns else 0.0,
            mean_late=1e3 * st.mean(s.lateness) if s.lateness else 0.0,
            alerts=len(s.alerts), crossings=len([x for x in s.true_crossings(RUN_LEN) if x <= RUN_LEN - 2 * s.period]),
            alert_mean=1e3 * st.mean(lat) if lat else float("nan"),
            alert_max=1e3 * max(lat) if lat else float("nan")))
    return rows


RULE_NAME = {"FP": "fixed priority (shortest period first)", "EDF": "earliest deadline first",
             "RR": "round-robin"}


def md_table(rows):
    h = ("| Stream | Period [ms] | Required | On-time | Late | Missed | % late+missed | "
         "Mean period overrun [ms] | Max period overrun [ms] | Alerts / true crossings | "
         "Mean alert latency [ms] | Max alert latency [ms] |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    body = [f"| {r['name']} | {r['period']*1e3:.0f} | {r['req']} | {r['on']} | {r['late']} | {r['miss']} | "
            f"{r['pct_bad']:.1f} | {r['mean_ov']:.1f} | {r['max_ov']:.0f} | {r['alerts']} / {r['crossings']} | "
            f"{r['alert_mean']:.0f} | {r['alert_max']:.0f} |" for r in rows]
    return "\n".join([h] + body)


# -------------------------------------------------------------------- figures
def plot_config(streams, rule, load, util, tag):
    n = len(streams)
    fig, axes = plt.subplots(n, 1, figsize=(11, 2.2 * n + 0.8), sharex=True)
    t_lo, t_hi = 0, 60
    for ax, s in zip(axes, streams):
        tt = [i * 0.02 for i in range(int(t_hi / 0.02))]
        ax.plot(tt, [s.clean(x) for x in tt], color="0.7", lw=1)
        ax.axhline(s.threshold, color="k", ls=":", lw=0.8)
        for cls, col, mk in (("on-time", "tab:green", "o"), ("late", "tab:orange", "D")):
            pts = [(a, b) for a, b, c in s.samples if c == cls and a <= t_hi]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], mk, color=col, ms=3, ls="none", label=cls)
        mrel = [r for r in s.missed_rel if r <= t_hi]
        ax.plot(mrel, [s.clean(r) for r in mrel], "x", color="tab:red", ms=6, ls="none", label="missed")
        al = [(d, tt_) for d, tt_ in s.alerts if d <= t_hi]
        ax.plot([d for d, _ in al], [s.threshold] * len(al), "^", color="purple", ms=8, ls="none", label="alert")
        ax.set_ylabel(s.name, fontsize=9)
    axes[0].legend(ncol=5, fontsize=8, loc="upper right")
    axes[-1].set_xlabel("time [s]  (first 60 s of the 300 s run)")
    fig.suptitle(f"{RULE_NAME[rule]}, {load} streams (CPU util {100*util:.0f} %): signals, samples, alerts", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"fig_signals_{tag}.png"), dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    names = [s.name for s in streams]
    on = [s.on_time for s in streams]; la = [s.late for s in streams]; mi = [s.missed for s in streams]
    ax.bar(names, on, color="tab:green", label="on-time")
    ax.bar(names, la, bottom=on, color="tab:orange", label="late")
    ax.bar(names, mi, bottom=[a + b for a, b in zip(on, la)], color="tab:red", label="missed")
    ax.set_ylabel("required samples"); ax.legend()
    ax.set_title(f"{RULE_NAME[rule]}, {load} streams: on-time / late / missed")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"fig_compliance_{tag}.png"), dpi=120); plt.close(fig)


def main():
    lines = ["# Mini Project 4.2 - results\n",
             f"Run length {RUN_LEN:.0f} s, on-time tolerance {100*ON_TIME_FRAC:.0f} % of the period, "
             f"tail probability {TAIL_PROB}, tail multiplier {TAIL_MULT[0]:.0f}-{TAIL_MULT[1]:.0f}x. "
             "Counts below are for seed 42; the summary at the end averages 30 seeds.\n"]
    fig_cfgs = {("FP", 4), ("RR", 4), ("EDF", 4), ("FP", 3)}
    for load in (3, 4):
        for rule in ("FP", "EDF", "RR"):
            streams = make_streams(load)
            wl = draw_workload(streams, 42)
            util = run(streams, rule, wl)
            rows = report_rows(streams)
            lines += [f"\n## {RULE_NAME[rule]} - {load} streams (processor busy {100*util:.0f} %)\n", md_table(rows)]
            if (rule, load) in fig_cfgs:
                plot_config(streams, rule, load, util, f"{rule}_{load}streams")

    # 30-seed averages
    lines += ["\n## Summary over 30 random workloads (mean % late+missed, mean alert latency in ms)\n",
              "| Load | Rule | Stream | % on-time | % late | % missed | mean alert latency [ms] |", "|---|---|---|---|---|---|---|"]
    for load in (3, 4):
        for rule in ("FP", "EDF", "RR"):
            acc = {}
            for seed in range(100, 130):
                streams = make_streams(load)
                run(streams, rule, draw_workload(streams, seed))
                for r in report_rows(streams):
                    a = acc.setdefault(r["name"], dict(on=[], late=[], miss=[], lat=[]))
                    a["on"].append(100 * r["on"] / r["req"]); a["late"].append(100 * r["late"] / r["req"])
                    a["miss"].append(100 * r["miss"] / r["req"])
                    if not math.isnan(r["alert_mean"]):
                        a["lat"].append(r["alert_mean"])
            for name, a in acc.items():
                lines.append(f"| {load} streams | {rule} | {name} | {st.mean(a['on']):.1f} | {st.mean(a['late']):.1f} | "
                             f"{st.mean(a['miss']):.1f} | {st.mean(a['lat']):.0f} |")
    with open(os.path.join(OUT, "results_4_2.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
