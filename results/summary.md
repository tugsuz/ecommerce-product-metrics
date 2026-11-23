# Results

## Data
- Events: 2,755,641 after dropping 460 exact duplicate rows
- Views 2,664,218, add to carts 68,966, purchased items 22,457
- Visitors: 1,407,580. Sessions: 1,761,675
- Period: 2015-05-03 to 2015-09-18 (UTC)

## Session funnel

| Step | Sessions | From previous step | From start |
|---|---:|---:|---:|
| session | 1,761,675 |  | 100.00% |
| product view | 1,755,781 | 99.67% | 99.67% |
| add to cart | 35,832 | 2.04% | 2.03% |
| purchase | 10,495 | 29.29% | 0.60% |

- Sessions with an add to cart but no earlier view: 8,092
- Sessions with a purchase but no add to cart in the same session: 2,365 of 14,297

## Weekly metrics (complete weeks)

- Weeks: 19 complete of 21
- Active visitors per week: median 76,983 (min 70,733, max 97,599)
- Sessions per visitor: 1.14
- Sessions with an add to cart: 2.48%
- Session conversion: 0.82% (min 0.71%, max 0.93%)
- Visitor conversion: 0.81%
- Items per order: 1.27

## Weekly retention

| Weeks after first visit | Did not buy in first week | Bought in first week |
|---:|---:|---:|
| 1 | 3.22% | 11.14% |
| 2 | 1.59% | 5.03% |
| 4 | 0.96% | 2.58% |
| 8 | 0.65% | 1.66% |
| 12 | 0.52% | 1.58% |

- Cohort sizes: 1,357,009 did not buy in their first week, 9,765 did

## A/A test

- Test window: 2015-08-17 to 2015-09-14. Covariate window: the 4 weeks before
- Visitors in the test: 287,442 (4.4% seen before the window)
- Split by hash: A 143,693, B 143,749, sample ratio p = 0.92
- Metric: product views per visitor, mean 1.722. The top 0.1% of visitors make 6.4% of all views
- Capped metric: views above 33 (the 99.9% quantile) count as 33
- Hash split on the capped metric, B minus A: -0.0007 (SE 0.0078, p = 0.92); adjusted -0.0007 (SE 0.0075, p = 0.93)

Over 2,000 random 50/50 splits, tests at the 5% level:

| Metric | Visitors | SD of the difference | Variance removed by adjustment | False positives, raw | False positives, adjusted | Detectable lift, raw | Detectable lift, adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|
| Views, uncapped | 287,442 | 0.0271 | 25.4% | 5.0% | 5.3% | 4.4% | 3.8% |
| Views, capped | 287,442 | 0.0078 | 5.7% | 5.2% | 5.9% | 1.3% | 1.3% |
| Views, capped, returning visitors | 12,605 | 0.0778 | 22.6% | 4.8% | 4.3% | 7.9% | 6.9% |
