-- Units for the A/A test. One row per visitor active in the test window.
-- y = product views in the test window, x = product views in the weeks before it.
-- $test_start, $test_end and $pre_start are set by the caller.
CREATE OR REPLACE TABLE experiment_units AS
SELECT visitor_id,
       COUNT(*) FILTER (WHERE event = 'view' AND ts >= $test_start AND ts < $test_end)  AS y_views,
       MAX(CASE WHEN event = 'transaction' AND ts >= $test_start AND ts < $test_end
                THEN 1 ELSE 0 END)                                                     AS y_bought,
       COUNT(*) FILTER (WHERE event = 'view' AND ts >= $pre_start AND ts < $test_start) AS x_views,
       MAX(CASE WHEN ts < $test_start THEN 1 ELSE 0 END)                               AS seen_before,
       -- fixed 50/50 split from a hash of the visitor id
       CASE WHEN hash(visitor_id, 'aa-test-1') % 2 = 0 THEN 'A' ELSE 'B' END           AS arm
FROM events
WHERE ts >= $pre_start AND ts < $test_end
GROUP BY visitor_id
HAVING COUNT(*) FILTER (WHERE ts >= $test_start AND ts < $test_end) > 0;
