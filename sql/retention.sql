-- Weekly retention cohorts.
-- Cohort = week of a visitor's first event. Retained in week k = any event k weeks later.
-- Only complete weeks are used, on both the cohort side and the activity side.
CREATE OR REPLACE TABLE visitor_weeks AS
SELECT DISTINCT visitor_id, date_trunc('week', ts)::DATE AS week
FROM events;

CREATE OR REPLACE TABLE visitors AS
SELECT v.visitor_id,
       MIN(v.week) AS cohort_week,
       COALESCE(BOOL_OR(s.orders > 0 AND date_trunc('week', s.started_at)::DATE = f.first_week), FALSE)
           AS bought_in_first_week
FROM visitor_weeks v
JOIN (SELECT visitor_id, MIN(week) AS first_week FROM visitor_weeks GROUP BY 1) f USING (visitor_id)
LEFT JOIN sessions s USING (visitor_id)
GROUP BY v.visitor_id;

CREATE OR REPLACE TABLE retention AS
WITH complete_weeks AS (
    SELECT week FROM weekly_metrics WHERE complete
),
cohorts AS (
    SELECT cohort_week, bought_in_first_week, COUNT(*) AS cohort_size
    FROM visitors
    WHERE cohort_week IN (SELECT week FROM complete_weeks)
    GROUP BY 1, 2
),
activity AS (
    SELECT c.cohort_week, c.bought_in_first_week,
           date_diff('week', c.cohort_week, w.week) AS week_no,
           COUNT(DISTINCT w.visitor_id) AS active
    FROM visitors c
    JOIN visitor_weeks w USING (visitor_id)
    WHERE c.cohort_week IN (SELECT week FROM complete_weeks)
      AND w.week IN (SELECT week FROM complete_weeks)
    GROUP BY 1, 2, 3
)
SELECT a.cohort_week, a.bought_in_first_week, a.week_no,
       c.cohort_size, a.active,
       a.active / c.cohort_size AS retention
FROM activity a
JOIN cohorts c USING (cohort_week, bought_in_first_week)
ORDER BY 1, 2, 3;

-- One curve per segment: cohorts pooled, each week_no using only cohorts old enough to reach it.
CREATE OR REPLACE TABLE retention_curve AS
WITH last_week AS (SELECT MAX(week) AS w FROM weekly_metrics WHERE complete),
grid AS (
    SELECT c.cohort_week, c.bought_in_first_week, c.cohort_size, k.week_no
    FROM (SELECT DISTINCT cohort_week, bought_in_first_week, cohort_size FROM retention) c
    CROSS JOIN (SELECT DISTINCT week_no FROM retention) k
    CROSS JOIN last_week l
    WHERE c.cohort_week + CAST(7 * k.week_no AS INTEGER) <= l.w
)
SELECT g.bought_in_first_week, g.week_no,
       COUNT(*)                    AS cohorts,
       SUM(g.cohort_size)          AS visitors,
       SUM(COALESCE(r.active, 0))  AS active,
       SUM(COALESCE(r.active, 0)) / SUM(g.cohort_size) AS retention
FROM grid g
LEFT JOIN retention r USING (cohort_week, bought_in_first_week, week_no)
GROUP BY 1, 2
ORDER BY 1, 2;
