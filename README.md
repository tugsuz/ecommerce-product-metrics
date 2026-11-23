# Product Metrics from an E-Commerce Event Log

Metric definitions, a purchase funnel, weekly retention cohorts and an A/A test,
built in SQL (DuckDB) and Python from 2.76 million raw events of a real online shop.

The data is the public Retailrocket event log: every product view, add to cart and
purchase by 1.4 million visitors over 4.5 months in 2015. It has three event types,
a visitor id, an item id and a timestamp. Nothing else: no sessions, no metrics,
no experiments. Everything below is built from that log.

## Results

**Funnel.** Of 1.76 million sessions, 2.0% reach an add to cart and 0.6% end in a
purchase. The large drop is from product view to add to cart. Once an item is in the
cart, 29% of sessions buy.

| Step | Sessions | From previous step | From start |
|---|---:|---:|---:|
| Session | 1,761,675 | | 100.00% |
| Product view | 1,755,781 | 99.67% | 99.67% |
| Add to cart (after a view) | 35,832 | 2.04% | 2.03% |
| Purchase (after the add to cart) | 10,495 | 29.29% | 0.60% |

**The strict funnel misses a quarter of purchases.** 14,297 sessions contain a
purchase, but only 10,495 follow the order view, add to cart, purchase inside one
session. 2,365 buying sessions have no add to cart in the same session (the item was
put in the cart on an earlier visit, or the step was not logged). In 1,366 the
add to cart is logged before any product view. A conversion metric
defined on the strict funnel reads 0.60%. Defined as "any purchase in the session"
it reads 0.81%. The definition has to be fixed before two teams compare numbers.

**Weekly metrics.** Over 19 complete weeks, the shop has a median of 76,983 active
visitors per week (range 70,733 to 97,599). Session conversion is 0.82% and stays
between 0.71% and 0.93%. Visitors make 1.14 sessions per week and orders hold
1.27 items.

**Retention.** Most visitors never come back: 87% have a single session. Visitors
who buy in their first week return at about three times the rate of the others.

| Weeks after first visit | Did not buy in first week | Bought in first week |
|---:|---:|---:|
| 1 | 3.22% | 11.14% |
| 2 | 1.59% | 5.03% |
| 4 | 0.96% | 2.58% |
| 8 | 0.65% | 1.66% |
| 12 | 0.52% | 1.58% |

This is a comparison of two groups, not an effect of buying. People who buy are
different from people who do not.

**A/A test.** The log has no experiments, so I ran one with no treatment: split
the visitors of the last four weeks 50/50 and test for a difference in product
views per visitor. A sound test should reject in about 5% of splits. Over 2,000
random splits:

| Metric | Visitors | SD of the difference | Variance removed by adjustment | False positives, raw | False positives, adjusted | Detectable lift, raw | Detectable lift, adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|
| Views, uncapped | 287,442 | 0.0271 | 25.4% | 5.0% | 5.3% | 4.4% | 3.8% |
| Views, capped | 287,442 | 0.0078 | 5.7% | 5.2% | 5.9% | 1.3% | 1.3% |
| Views, capped, returning visitors | 12,605 | 0.0778 | 22.6% | 4.8% | 4.3% | 7.9% | 6.9% |

Three things follow.

1. The test is sound. False positive rates sit near 5%, and the fixed hash split
   passes the sample ratio check (143,693 against 143,749, p = 0.92).
2. Capping matters more than covariate adjustment here. The top 0.1% of visitors
   make 6.4% of all views. A few accounts have thousands of events. Capping views at
   the 99.9% quantile (33 views) cuts the smallest detectable lift from 4.4% to 1.3%.
3. Adjusting for pre-period views (CUPED) helps only where there is a pre-period.
   It removes 23% of the variance among returning visitors, but only 4.4% of
   visitors in the test were seen before, so across all visitors it removes 6%.
   On a product with mostly new traffic, this adjustment buys little.

## How it is built

| File | What it does |
|---|---|
| `sql/events.sql` | Cleans the raw log, drops 460 exact duplicate rows |
| `sql/sessions.sql` | Builds sessions with a 30 minute gap rule (window functions) |
| `sql/funnel.sql` | Ordered session funnel, and counts of sessions that do not fit it |
| `sql/weekly_metrics.sql` | Weekly active visitors, conversion, cart rate, items per order; flags partial weeks |
| `sql/retention.sql` | Weekly retention cohorts by first-visit week, pooled into one curve per segment |
| `sql/experiment_units.sql` | One row per visitor for the A/A test, with a hash-based split |
| `shopmetrics/experiment.py` | Welch test, sample ratio check, CUPED adjustment, detectable lift, split simulation |
| `run_all.py` | Runs everything and writes `results/` |
| `tests/` | 11 tests on small hand-made logs with known answers |

## Run it

```
pip install -r requirements.txt
# download events.csv from https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset into data/
python run_all.py data/events.csv
pytest
```

Without the data, `python make_synthetic.py` writes a small synthetic log with the
same columns, and `python run_all.py data/events_synthetic.csv` runs on it.

## Definitions and limits

- A session is a visitor's run of events with no gap over 30 minutes. Times are UTC.
- A week runs Monday to Sunday. Partial weeks at both ends of the log are left out.
- Retention in week k means any event k weeks after the first-visit week.
- Visitor ids are cookies. One person on two devices counts as two visitors.
- The log has no prices, so there is no revenue metric.
- The A/A test uses a fixed sample. It says nothing about a test that is checked
  many times while it runs.
- The data is not in this repository. Retailrocket publishes it under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/). This project is non-commercial and reports only aggregate results.
