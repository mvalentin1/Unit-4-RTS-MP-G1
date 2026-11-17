#!/usr/bin/env python3
"""
Mini Project 4.3 - Edge-versus-cloud latency simulator for a real-time IoT
decision task (Unit 4, Sections 4.8 and 4.9).

Task: a sensor reading arrives at a fixed rate; each needs one "is this an anomaly?"
decision before a deadline (default 100 ms).  Decisions are independent and
asynchronous (no queueing between events).  A fraction HARD_FRAC of the decisions
are "hard" (need a heavier model).

Latency models (all in milliseconds)
------------------------------------
EDGE   : transport 0.5 ms + compute  ~ LogNormal(median 30, sigma 0.15)  (easy)
                                       LogNormal(median 75, sigma 0.15)  (hard)
         -> limited local hardware: slow-ish but tight and predictable.
CLOUD  : upload leg + remote compute + download leg
         leg     = LogNormal(median 20 * (1 + 1.5 c), sigma 0.35)
                   + with prob (0.01 + 0.20 c): congestion spike of 30 * Pareto(1.8) ms
                   (heavy-tailed: unbounded in principle)
         compute = LogNormal(median 5 (easy) / 9 (hard), sigma 0.3)
         c = congestion_level in [0, 1]  (the configurable stress parameter)
HYBRID : easy decisions -> edge; hard decisions -> cloud   (route by difficulty)
HEDGED : easy -> edge; hard -> send to BOTH, take the first answer (min of the two)

Common random numbers: every random variate is drawn ONCE per event, so every
architecture and every congestion level faces exactly the same event sequence.

Run:  python edge_cloud_sim.py      (writes figures + results into ./output_4_3)
"""
import math
import os
import random
import statistics as st
from dataclasses import dataclass

import matplotlib 
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_4_3")
os.makedirs(OUT, exist_ok=True)

N_EVENTS = 20000
RATE_HZ = 20.0              # nominal sensor rate (events are independent)
DEADLINE = 100.0            # ms
HARD_FRAC = 0.20
BASE_CONGESTION = 0.20      # "stated baseline congestion" for the results table


@dataclass
class Event:
    t: float            # arrival time [ms]
    hard: bool
    z_edge: float
    z_up: float; z_cmp: float; z_dn: float
    u_up: float; u_dn: float
    par_up: float; par_dn: float


def make_events(n=N_EVENTS, seed=2026):
    rng = random.Random(seed)
    return [Event(t=i * 1000.0 / RATE_HZ, hard=rng.random() < HARD_FRAC,
                  z_edge=rng.gauss(0, 1), z_up=rng.gauss(0, 1), z_cmp=rng.gauss(0, 1),
                  z_dn=rng.gauss(0, 1), u_up=rng.random(), u_dn=rng.random(),
                  par_up=rng.paretovariate(1.8), par_dn=rng.paretovariate(1.8))
            for i in range(n)]


def edge_latency(ev):
    median = 75.0 if ev.hard else 30.0
    return 0.5 + median * math.exp(0.15 * ev.z_edge)


def _leg(z, u, par, c):
    base = 20.0 * (1 + 1.5 * c) * math.exp(0.35 * z)
    spike = 30.0 * par if u < 0.01 + 0.20 * c else 0.0
    return base + spike


def cloud_latency(ev, congestion_level):
    c = congestion_level
    up = _leg(ev.z_up, ev.u_up, ev.par_up, c)
    comp = (9.0 if ev.hard else 5.0) * math.exp(0.3 * ev.z_cmp)
    dn = _leg(ev.z_dn, ev.u_dn, ev.par_dn, c)
    return up + comp + dn


def hybrid_latency(ev, c):
    return cloud_latency(ev, c) if ev.hard else edge_latency(ev)


def hedged_latency(ev, c):
    return min(cloud_latency(ev, c), edge_latency(ev)) if ev.hard else edge_latency(ev)


def pct(sorted_x, q):
    """nearest-rank percentile of an already sorted list"""
    k = max(0, min(len(sorted_x) - 1, math.ceil(q / 100.0 * len(sorted_x)) - 1))
    return sorted_x[k]


def summarize(lat, deadline=DEADLINE):
    s = sorted(lat)
    return dict(mean=st.mean(lat), p95=pct(s, 95), p99=pct(s, 99), worst=s[-1],
                comp=100.0 * sum(1 for x in lat if x <= deadline) / len(lat))


def latencies(events, c):
    return {"edge": [edge_latency(e) for e in events],
            "cloud": [cloud_latency(e, c) for e in events],
            "hybrid": [hybrid_latency(e, c) for e in events],
            "hedged": [hedged_latency(e, c) for e in events]}


def main():
    ev = make_events()
    lines = ["# Mini Project 4.3 - results\n",
             f"{N_EVENTS} decision events at a nominal {RATE_HZ:.0f} Hz, deadline {DEADLINE:.0f} ms, "
             f"{100*HARD_FRAC:.0f} % hard decisions, baseline congestion c = {BASE_CONGESTION}.\n"]

    # ---- results table at baseline congestion
    L = latencies(ev, BASE_CONGESTION)
    lines += ["\n## 1. Latency statistics at baseline congestion\n",
              "| Architecture | mean [ms] | p95 [ms] | p99 [ms] | worst case [ms] | deadline compliance [%] |",
              "|---|---|---|---|---|---|"]
    names = {"edge": "Edge only", "cloud": f"Cloud only (c={BASE_CONGESTION})",
             "hybrid": "Hybrid (hard -> cloud)", "hedged": "Hybrid-hedged (hard -> min(edge, cloud))"}
    S = {}
    for k in ("edge", "cloud", "hybrid", "hedged"):
        S[k] = summarize(L[k])
        r = S[k]
        lines.append(f"| {names[k]} | {r['mean']:.1f} | {r['p95']:.1f} | {r['p99']:.1f} | {r['worst']:.0f} | {r['comp']:.2f} |")

    # ---- split by difficulty
    lines += ["\n## 2. Compliance split by decision difficulty (baseline congestion)\n",
              "| Architecture | easy: compliance [%] | hard: compliance [%] | hard: p99 [ms] |", "|---|---|---|---|"]
    for k in ("edge", "cloud", "hybrid", "hedged"):
        easy = [x for x, e in zip(L[k], ev) if not e.hard]
        hard = [x for x, e in zip(L[k], ev) if e.hard]
        lines.append(f"| {names[k]} | {summarize(easy)['comp']:.2f} | {summarize(hard)['comp']:.2f} | "
                     f"{pct(sorted(hard), 99):.0f} |")

    # ---- congestion sweep
    cs = [i / 10 for i in range(0, 11)]
    sweep = {k: [] for k in ("edge", "cloud", "hybrid", "hedged")}
    p99 = {k: [] for k in sweep}
    mean = {k: [] for k in sweep}
    for c in cs:
        Lc = latencies(ev, c)
        for k in sweep:
            r = summarize(Lc[k]); sweep[k].append(r["comp"]); p99[k].append(r["p99"]); mean[k].append(r["mean"])
    lines += ["\n## 3. Deadline compliance [%] versus congestion level (deadline 100 ms)\n",
              "| congestion c | Edge | Cloud | Hybrid | Hybrid-hedged | Cloud mean [ms] | Cloud p99 [ms] |", "|---|---|---|---|---|---|---|"]
    for i, c in enumerate(cs):
        lines.append(f"| {c:.1f} | {sweep['edge'][i]:.2f} | {sweep['cloud'][i]:.2f} | {sweep['hybrid'][i]:.2f} | "
                     f"{sweep['hedged'][i]:.2f} | {mean['cloud'][i]:.1f} | {p99['cloud'][i]:.0f} |")

    # ---- deadline sweep at c=0 and baseline
    lines += ["\n## 4. Compliance [%] versus deadline (cloud shown at c = 0 and at baseline c = 0.2)\n",
              "| deadline [ms] | Edge | Cloud c=0 | Cloud c=0.2 | Hybrid c=0.2 | Hedged c=0.2 |", "|---|---|---|---|---|---|"]
    L0 = latencies(ev, 0.0)
    for d in (40, 50, 75, 100, 150, 200, 300):
        f = lambda xs: 100.0 * sum(1 for x in xs if x <= d) / len(xs)
        lines.append(f"| {d} | {f(L['edge']):.2f} | {f(L0['cloud']):.2f} | {f(L['cloud']):.2f} | {f(L['hybrid']):.2f} | {f(L['hedged']):.2f} |")

    # ---- where does the cloud stay compliant?
    thr = {}
    for target in (99.0, 95.0):
        ok = [c for c, v in zip(cs, sweep["cloud"]) if v >= target]
        thr[target] = max(ok) if ok else None
    lines += ["\n## 5. Cloud-only operating envelope\n",
              f"- Highest swept congestion with cloud compliance >= 99 %: {thr[99.0]}",
              f"- Highest swept congestion with cloud compliance >= 95 %: {thr[95.0]}",
              f"- Edge compliance (independent of congestion): {sweep['edge'][0]:.2f} %"]

    with open(os.path.join(OUT, "results_4_3.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))

    # ---- Figure 1: overlaid latency distributions with the deadline marked
    col = {"edge": "tab:blue", "cloud": "tab:red", "hybrid": "tab:green"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.6))
    bins = [i * 5 for i in range(0, 61)]
    for k in ("edge", "cloud", "hybrid"):
        a1.hist([min(x, 299.9) for x in L[k]], bins=bins, histtype="step", lw=1.8, color=col[k], label=names[k], density=True)
    a1.axvline(DEADLINE, color="k", ls="--", lw=1.5, label=f"deadline {DEADLINE:.0f} ms")
    a1.set_xlabel("end-to-end latency [ms]  (values >300 ms piled into the last bin)")
    a1.set_ylabel("density"); a1.set_title("Latency histograms"); a1.legend(fontsize=8)
    for k in ("edge", "cloud", "hybrid"):
        s = sorted(L[k]); y = [(i + 1) / len(s) for i in range(len(s))]
        a2.plot(s, y, color=col[k], label=names[k])
    a2.axvline(DEADLINE, color="k", ls="--", lw=1.5); a2.set_xscale("log")
    a2.set_ylim(0.8, 1.002); a2.set_xlabel("latency [ms] (log scale)"); a2.set_ylabel("empirical CDF (top 20 % shown)")
    a2.set_title("Tail behaviour"); a2.legend(fontsize=8, loc="lower right"); a2.grid(alpha=0.3)
    fig.suptitle(f"Figure 1 - edge vs cloud vs hybrid latency (baseline congestion {BASE_CONGESTION})")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig1_latency_distributions.png"), dpi=130); plt.close(fig)

    # ---- Figure 2: compliance vs congestion
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.6))
    a1.plot(cs, sweep["cloud"], "o-", color="tab:red", label="Cloud only")
    a1.plot(cs, sweep["hybrid"], "s-", color="tab:green", label="Hybrid (hard -> cloud)")
    a1.plot(cs, sweep["hedged"], "^-", color="tab:purple", label="Hybrid-hedged")
    a1.axhline(sweep["edge"][0], color="tab:blue", ls="--", label="Edge only (flat reference)")
    a1.set_xlabel("congestion level c"); a1.set_ylabel(f"decisions meeting {DEADLINE:.0f} ms deadline [%]")
    a1.set_title("Compliance vs congestion"); a1.legend(fontsize=8); a1.grid(alpha=0.3)
    a2.plot(cs, p99["cloud"], "o-", color="tab:red", label="Cloud p99")
    a2.plot(cs, mean["cloud"], "o--", color="tab:red", alpha=0.5, label="Cloud mean")
    a2.axhline(p99["edge"][0], color="tab:blue", ls="--", label="Edge p99")
    a2.axhline(DEADLINE, color="k", ls=":", label="deadline"); a2.set_yscale("log")
    a2.set_xlabel("congestion level c"); a2.set_ylabel("latency [ms] (log)"); a2.set_title("Mean hides the tail")
    a2.legend(fontsize=8); a2.grid(alpha=0.3)
    fig.suptitle("Figure 2 - deadline compliance as cloud congestion is swept")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_compliance_vs_congestion.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
