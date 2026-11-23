-- Sessions: a visitor's events with no gap longer than 30 minutes.
CREATE OR REPLACE TABLE session_events AS
WITH gaps AS (
    SELECT *,
           ts - LAG(ts) OVER (PARTITION BY visitor_id ORDER BY ts, event, item_id) AS gap
    FROM events
),
marked AS (
    SELECT *,
           CASE WHEN gap IS NULL OR gap > INTERVAL 30 MINUTE THEN 1 ELSE 0 END AS new_session
    FROM gaps
)
SELECT ts, visitor_id, event, item_id, transaction_id,
       SUM(new_session) OVER (
           PARTITION BY visitor_id ORDER BY ts, event, item_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS session_no
FROM marked;

CREATE OR REPLACE TABLE sessions AS
SELECT visitor_id,
       session_no,
       MIN(ts)                                          AS started_at,
       MAX(ts)                                          AS ended_at,
       COUNT(*) FILTER (WHERE event = 'view')           AS views,
       COUNT(*) FILTER (WHERE event = 'addtocart')      AS carts,
       COUNT(DISTINCT transaction_id)                   AS orders,
       COUNT(*) FILTER (WHERE event = 'transaction')    AS items_bought,
       MIN(ts) FILTER (WHERE event = 'view')            AS first_view,
       MIN(ts) FILTER (WHERE event = 'addtocart')       AS first_cart,
       MAX(ts) FILTER (WHERE event = 'transaction')     AS last_purchase
FROM session_events
GROUP BY visitor_id, session_no;
