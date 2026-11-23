-- Weekly metrics. Weeks start on Monday (UTC).
-- A week is complete when the log covers all seven days of it.
CREATE OR REPLACE TABLE weekly_metrics AS
WITH bounds AS (
    SELECT MIN(ts) AS first_ts, MAX(ts) AS last_ts FROM events
),
by_week AS (
    SELECT date_trunc('week', started_at)::DATE          AS week,
           COUNT(DISTINCT visitor_id)                    AS active_visitors,
           COUNT(*)                                      AS sessions,
           SUM(views)                                    AS views,
           SUM(orders)                                   AS orders,
           SUM(items_bought)                             AS items_bought,
           COUNT(*) FILTER (WHERE carts > 0)             AS sessions_with_cart,
           COUNT(*) FILTER (WHERE orders > 0)            AS sessions_with_order,
           COUNT(DISTINCT visitor_id) FILTER (WHERE orders > 0) AS buyers
    FROM sessions
    GROUP BY 1
)
SELECT w.week,
       (w.week >= date_trunc('week', b.first_ts + INTERVAL 6 DAY)::DATE
        AND w.week + 7 <= date_trunc('day', b.last_ts)::DATE)         AS complete,
       w.active_visitors,
       w.sessions,
       w.sessions / w.active_visitors            AS sessions_per_visitor,
       w.views / w.sessions                      AS views_per_session,
       w.sessions_with_cart / w.sessions         AS cart_rate,
       w.sessions_with_order / w.sessions        AS session_conversion,
       w.buyers / w.active_visitors              AS visitor_conversion,
       w.orders,
       w.items_bought / NULLIF(w.orders, 0)      AS items_per_order,
       w.active_visitors / LAG(w.active_visitors) OVER (ORDER BY w.week) - 1 AS visitors_wow
FROM by_week w CROSS JOIN bounds b
ORDER BY w.week;
