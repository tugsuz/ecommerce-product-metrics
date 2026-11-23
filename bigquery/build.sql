-- BigQuery version of the pipeline (GoogleSQL).
-- Before running: create a dataset named `shop` and load events.csv into `shop.raw_events`
-- (columns: timestamp INT64, visitorid INT64, event STRING, itemid INT64, transactionid INT64).
-- Then run this whole script in the BigQuery console. It builds every table in order.

-- 1. Clean events. Timestamps are milliseconds since 1970 in UTC. Exact duplicates are dropped.
CREATE OR REPLACE TABLE shop.events AS
SELECT DISTINCT
  TIMESTAMP_MILLIS(timestamp) AS ts,
  visitorid AS visitor_id,
  event,
  itemid AS item_id,
  transactionid AS transaction_id
FROM shop.raw_events
WHERE event IN ('view', 'addtocart', 'transaction');

-- 2. Sessions: a visitor's events with no gap longer than 30 minutes.
CREATE OR REPLACE TABLE shop.session_events AS
WITH gaps AS (
  SELECT *,
    TIMESTAMP_DIFF(ts, LAG(ts) OVER (PARTITION BY visitor_id ORDER BY ts, event, item_id), MILLISECOND) AS gap_ms
  FROM shop.events
)
SELECT ts, visitor_id, event, item_id, transaction_id,
  SUM(CASE WHEN gap_ms IS NULL OR gap_ms > 1800000 THEN 1 ELSE 0 END) OVER (
    PARTITION BY visitor_id ORDER BY ts, event, item_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS session_no
FROM gaps;

CREATE OR REPLACE TABLE shop.sessions AS
SELECT visitor_id, session_no,
  MIN(ts) AS started_at,
  COUNTIF(event = 'view') AS views,
  COUNTIF(event = 'addtocart') AS carts,
  COUNT(DISTINCT transaction_id) AS orders,
  COUNTIF(event = 'transaction') AS items_bought,
  MIN(IF(event = 'view', ts, NULL)) AS first_view,
  MIN(IF(event = 'addtocart', ts, NULL)) AS first_cart,
  MAX(IF(event = 'transaction', ts, NULL)) AS last_purchase
FROM shop.session_events
GROUP BY visitor_id, session_no;

-- 3. Ordered session funnel: view, then add to cart, then purchase.
CREATE OR REPLACE TABLE shop.funnel AS
WITH counts AS (
  SELECT 1 AS step_no, 'Session' AS step, COUNT(*) AS sessions FROM shop.sessions
  UNION ALL
  SELECT 2, 'Product view', COUNTIF(first_view IS NOT NULL) FROM shop.sessions
  UNION ALL
  SELECT 3, 'Add to cart', COUNTIF(first_view IS NOT NULL AND first_cart >= first_view) FROM shop.sessions
  UNION ALL
  SELECT 4, 'Purchase', COUNTIF(first_view IS NOT NULL AND first_cart >= first_view AND last_purchase >= first_cart)
  FROM shop.sessions
)
SELECT step_no, step, sessions,
  SAFE_DIVIDE(sessions, LAG(sessions) OVER (ORDER BY step_no)) AS rate_from_previous,
  SAFE_DIVIDE(sessions, FIRST_VALUE(sessions) OVER (ORDER BY step_no)) AS rate_from_start
FROM counts;

-- 4. Weekly metrics. Weeks start on Monday (UTC). Partial weeks at both ends are flagged.
CREATE OR REPLACE TABLE shop.weekly_metrics AS
WITH bounds AS (
  SELECT MIN(ts) AS first_ts, MAX(ts) AS last_ts FROM shop.events
),
by_week AS (
  SELECT DATE_TRUNC(DATE(started_at), WEEK(MONDAY)) AS week,
    COUNT(DISTINCT visitor_id) AS active_visitors,
    COUNT(*) AS sessions,
    SUM(views) AS views,
    SUM(orders) AS orders,
    SUM(items_bought) AS items_bought,
    COUNTIF(carts > 0) AS sessions_with_cart,
    COUNTIF(orders > 0) AS sessions_with_order,
    COUNT(DISTINCT IF(orders > 0, visitor_id, NULL)) AS buyers
  FROM shop.sessions
  GROUP BY week
)
SELECT w.week,
  (w.week >= DATE_TRUNC(DATE_ADD(DATE(b.first_ts), INTERVAL 6 DAY), WEEK(MONDAY))
   AND DATE_ADD(w.week, INTERVAL 7 DAY) <= DATE(b.last_ts)) AS complete,
  w.active_visitors,
  w.sessions,
  SAFE_DIVIDE(w.sessions, w.active_visitors) AS sessions_per_visitor,
  SAFE_DIVIDE(w.sessions_with_cart, w.sessions) AS cart_rate,
  SAFE_DIVIDE(w.sessions_with_order, w.sessions) AS session_conversion,
  SAFE_DIVIDE(w.buyers, w.active_visitors) AS visitor_conversion,
  w.orders,
  SAFE_DIVIDE(w.items_bought, w.orders) AS items_per_order
FROM by_week AS w CROSS JOIN bounds AS b;

-- 5. Weekly retention by first-visit week, split by whether the visitor bought in that week.
CREATE OR REPLACE TABLE shop.retention AS
WITH visitor_weeks AS (
  SELECT DISTINCT visitor_id, DATE_TRUNC(DATE(ts), WEEK(MONDAY)) AS week FROM shop.events
),
first_week AS (
  SELECT visitor_id, MIN(week) AS cohort_week FROM visitor_weeks GROUP BY visitor_id
),
buyers AS (
  SELECT DISTINCT s.visitor_id
  FROM shop.sessions AS s JOIN first_week AS f ON s.visitor_id = f.visitor_id
  WHERE s.orders > 0 AND DATE_TRUNC(DATE(s.started_at), WEEK(MONDAY)) = f.cohort_week
),
visitors AS (
  SELECT f.visitor_id, f.cohort_week, b.visitor_id IS NOT NULL AS bought_in_first_week
  FROM first_week AS f LEFT JOIN buyers AS b ON f.visitor_id = b.visitor_id
),
complete_weeks AS (
  SELECT week FROM shop.weekly_metrics WHERE complete
),
cohorts AS (
  SELECT cohort_week, bought_in_first_week, COUNT(*) AS cohort_size
  FROM visitors
  WHERE cohort_week IN (SELECT week FROM complete_weeks)
  GROUP BY cohort_week, bought_in_first_week
),
activity AS (
  SELECT v.cohort_week, v.bought_in_first_week,
    DATE_DIFF(w.week, v.cohort_week, WEEK) AS week_no,
    COUNT(DISTINCT w.visitor_id) AS active
  FROM visitors AS v JOIN visitor_weeks AS w ON v.visitor_id = w.visitor_id
  WHERE v.cohort_week IN (SELECT week FROM complete_weeks)
    AND w.week IN (SELECT week FROM complete_weeks)
  GROUP BY v.cohort_week, v.bought_in_first_week, week_no
)
SELECT a.cohort_week, a.bought_in_first_week, a.week_no, c.cohort_size, a.active,
  SAFE_DIVIDE(a.active, c.cohort_size) AS retention
FROM activity AS a
JOIN cohorts AS c ON a.cohort_week = c.cohort_week AND a.bought_in_first_week = c.bought_in_first_week;

-- 6. Check: these numbers should match the README of the DuckDB version.
SELECT
  (SELECT COUNT(*) FROM shop.events) AS events,                                    -- 2,755,641
  (SELECT COUNT(*) FROM shop.sessions) AS sessions,                                -- 1,761,675
  (SELECT sessions FROM shop.funnel WHERE step_no = 4) AS funnel_purchases,        -- 10,495
  (SELECT COUNTIF(complete) FROM shop.weekly_metrics) AS complete_weeks;           -- 19
