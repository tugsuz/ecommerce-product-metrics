"""Build all tables from the event log and write the results.

    python run_all.py data/events.csv
"""
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

from shopmetrics import build, experiment

RESULTS = Path(__file__).resolve().parent / "results"
TEST_WEEKS = 4
PRE_WEEKS = 4


def pct(x, digits=1):
    return f"{100 * x:.{digits}f}%"


def main(path):
    RESULTS.mkdir(exist_ok=True)
    con = build.build_from_csv(path)
    out = []

    raw_n = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    n, visitors, first_ts, last_ts = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT visitor_id), MIN(ts), MAX(ts) FROM events"
    ).fetchone()
    by_event = dict(con.execute("SELECT event, COUNT(*) FROM events GROUP BY 1").fetchall())
    n_sessions = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    out += [
        "# Results",
        "",
        "## Data",
        f"- Events: {n:,} after dropping {raw_n - n:,} exact duplicate rows",
        f"- Views {by_event.get('view', 0):,}, add to carts {by_event.get('addtocart', 0):,}, "
        f"purchased items {by_event.get('transaction', 0):,}",
        f"- Visitors: {visitors:,}. Sessions: {n_sessions:,}",
        f"- Period: {first_ts:%Y-%m-%d} to {last_ts:%Y-%m-%d} (UTC)",
        "",
    ]

    funnel = con.execute("SELECT * FROM funnel ORDER BY step_no").df()
    funnel.to_csv(RESULTS / "funnel.csv", index=False)
    out += ["## Session funnel", "", "| Step | Sessions | From previous step | From start |", "|---|---:|---:|---:|"]
    for r in funnel.itertuples():
        prev = "" if np.isnan(r.rate_from_previous) else pct(r.rate_from_previous, 2)
        out.append(f"| {r.step} | {int(r.sessions):,} | {prev} | {pct(r.rate_from_start, 2)} |")
    exc = con.execute("SELECT * FROM funnel_exceptions").fetchone()
    out += [
        "",
        f"- Sessions with an add to cart but no earlier view: {exc[0]:,}",
        f"- Sessions with a purchase but no add to cart in the same session: {exc[1]:,} of {exc[2]:,}",
        "",
    ]

    weekly = con.execute("SELECT * FROM weekly_metrics ORDER BY week").df()
    weekly.to_csv(RESULTS / "weekly_metrics.csv", index=False)
    full = weekly[weekly.complete]
    out += [
        "## Weekly metrics (complete weeks)",
        "",
        f"- Weeks: {len(full)} complete of {len(weekly)}",
        f"- Active visitors per week: median {int(full.active_visitors.median()):,} "
        f"(min {int(full.active_visitors.min()):,}, max {int(full.active_visitors.max()):,})",
        f"- Sessions per visitor: {full.sessions_per_visitor.median():.2f}",
        f"- Sessions with an add to cart: {pct(full.cart_rate.median(), 2)}",
        f"- Session conversion: {pct(full.session_conversion.median(), 2)} "
        f"(min {pct(full.session_conversion.min(), 2)}, max {pct(full.session_conversion.max(), 2)})",
        f"- Visitor conversion: {pct(full.visitor_conversion.median(), 2)}",
        f"- Items per order: {full.items_per_order.median():.2f}",
        "",
    ]

    con.execute("COPY retention TO ? (HEADER, DELIMITER ',')", [str(RESULTS / "retention.csv")])
    curve = con.execute("SELECT * FROM retention_curve ORDER BY 1, 2").df()
    curve.to_csv(RESULTS / "retention_curve.csv", index=False)
    out += ["## Weekly retention", "", "| Weeks after first visit | Did not buy in first week | Bought in first week |", "|---:|---:|---:|"]
    for k in (1, 2, 4, 8, 12):
        cells = []
        for flag in (False, True):
            row = curve[(curve.bought_in_first_week == flag) & (curve.week_no == k)]
            cells.append(pct(row.retention.iloc[0], 2) if len(row) else "")
        if any(cells):
            out.append(f"| {k} | {cells[0]} | {cells[1]} |")
    sizes = curve[curve.week_no == 0].set_index("bought_in_first_week").visitors
    out += ["", f"- Cohort sizes: {int(sizes.get(False, 0)):,} did not buy in their first week, {int(sizes.get(True, 0)):,} did", ""]

    last_week = full.week.max()
    test_end = last_week + timedelta(days=7)
    test_start = test_end - timedelta(weeks=TEST_WEEKS)
    pre_start = test_start - timedelta(weeks=PRE_WEEKS)
    build.run_sql(con, "experiment_units",
                  {"test_start": test_start, "test_end": test_end, "pre_start": pre_start})
    units = con.execute("SELECT * FROM experiment_units").df()
    y = units.y_views.to_numpy(float)
    x = units.x_views.to_numpy(float)
    in_b = (units.arm == "B").to_numpy()
    n_a, n_b = int((~in_b).sum()), int(in_b.sum())
    y_adj, theta = experiment.cuped_adjust(y, x)
    d_raw, se_raw, p_raw = experiment.welch(y, in_b)
    d_adj, se_adj, p_adj = experiment.welch(y_adj, in_b)
    sim = experiment.simulate_aa(y, x, n_splits=2000, seed=0)
    back = units.seen_before.to_numpy() == 1
    sim_back = experiment.simulate_aa(y[back], x[back], n_splits=2000, seed=1) if back.sum() > 100 else None
    mde_raw = experiment.mde(y.std(ddof=1), y.size / 2) / y.mean()
    mde_adj = experiment.mde(y_adj.std(ddof=1), y.size / 2) / y.mean()
    out += [
        "## A/A test",
        "",
        f"- Test window: {test_start:%Y-%m-%d} to {test_end:%Y-%m-%d}. Covariate window: the {PRE_WEEKS} weeks before",
        f"- Visitors in the test: {y.size:,} ({pct(back.mean())} seen before the window)",
        f"- Split by hash: A {n_a:,}, B {n_b:,}, sample ratio p = {experiment.srm_pvalue(n_a, n_b):.2f}",
        f"- Views per visitor: mean {y.mean():.3f}",
        f"- Difference B minus A: {d_raw:+.4f} (SE {se_raw:.4f}, p = {p_raw:.2f}); "
        f"adjusted {d_adj:+.4f} (SE {se_adj:.4f}, p = {p_adj:.2f})",
        f"- Correlation of test-window views with pre-period views: {sim['correlation']:.2f}",
        f"- Variance removed by the adjustment: {pct(sim['variance_reduction'])}",
        f"- False positive rate over {sim['n_splits']:,} random splits at the 5% level: "
        f"{pct(sim['false_positive_raw'])} raw, {pct(sim['false_positive_adjusted'])} adjusted",
        f"- Smallest detectable lift in views per visitor (80% power): {pct(mde_raw)} raw, {pct(mde_adj)} adjusted",
    ]
    if sim_back:
        out.append(
            f"- Returning visitors only ({int(back.sum()):,}): correlation {sim_back['correlation']:.2f}, "
            f"variance removed {pct(sim_back['variance_reduction'])}, false positive rate "
            f"{pct(sim_back['false_positive_raw'])} raw, {pct(sim_back['false_positive_adjusted'])} adjusted"
        )
    text = "\n".join(out) + "\n"
    (RESULTS / "summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/events.csv")
