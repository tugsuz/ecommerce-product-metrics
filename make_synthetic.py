"""Write a small synthetic event log with the same columns as the real one.

Used by the tests and for trying the code without the data. Numbers from this
file say nothing about real shoppers.
"""
import sys

import numpy as np
import pandas as pd

DAY = 24 * 3600 * 1000
START = 1430697600000  # Monday 4 May 2015, 00:00 UTC


def make(n_visitors=20000, n_days=70, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    tx = 0
    intensity = rng.gamma(2.0, 1.5, n_visitors)      # how much a visitor browses
    comes_back = rng.random(n_visitors) < 0.25
    first_day = rng.integers(0, n_days, n_visitors)
    for v in range(n_visitors):
        days = [first_day[v]]
        if comes_back[v]:
            extra = rng.integers(1, 6)
            days += list(first_day[v] + rng.integers(1, 40, extra))
        for d in sorted(set(int(x) for x in days if x < n_days)):
            t = START + d * DAY + int(rng.integers(0, DAY - 3600 * 1000))
            for _ in range(1 + rng.poisson(intensity[v])):
                item = int(rng.integers(1, 2000))
                t += int(rng.integers(5, 300)) * 1000
                rows.append((t, v, "view", item, None))
                if rng.random() < 0.04:
                    t += int(rng.integers(5, 120)) * 1000
                    rows.append((t, v, "addtocart", item, None))
                    if rng.random() < 0.3:
                        t += int(rng.integers(30, 600)) * 1000
                        tx += 1
                        rows.append((t, v, "transaction", item, tx))
    df = pd.DataFrame(rows, columns=["timestamp", "visitorid", "event", "itemid", "transactionid"])
    df["transactionid"] = df["transactionid"].astype("Int64")
    return df.sort_values("timestamp").reset_index(drop=True)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/events_synthetic.csv"
    make().to_csv(out, index=False)
    print("wrote", out)
