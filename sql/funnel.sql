-- Session funnel with ordered steps:
--   1. any event
--   2. a product view
--   3. an add to cart at or after the first view
--   4. a purchase at or after that add to cart
CREATE OR REPLACE TABLE funnel AS
WITH steps AS (
    SELECT
        1 AS s1,
        CASE WHEN first_view IS NOT NULL THEN 1 ELSE 0 END AS s2,
        CASE WHEN first_view IS NOT NULL AND first_cart >= first_view THEN 1 ELSE 0 END AS s3,
        CASE WHEN first_view IS NOT NULL AND first_cart >= first_view
                  AND last_purchase >= first_cart THEN 1 ELSE 0 END AS s4
    FROM sessions
),
counts AS (
    SELECT 1 AS step_no, 'session'      AS step, SUM(s1) AS sessions FROM steps UNION ALL
    SELECT 2,            'product view',          SUM(s2) FROM steps UNION ALL
    SELECT 3,            'add to cart',           SUM(s3) FROM steps UNION ALL
    SELECT 4,            'purchase',              SUM(s4) FROM steps
)
SELECT step_no, step, sessions,
       sessions / LAG(sessions) OVER (ORDER BY step_no)          AS rate_from_previous,
       sessions / FIRST_VALUE(sessions) OVER (ORDER BY step_no)  AS rate_from_start
FROM counts
ORDER BY step_no;

-- Sessions that do not fit the ordered funnel, for the data notes.
CREATE OR REPLACE TABLE funnel_exceptions AS
SELECT
    COUNT(*) FILTER (WHERE carts > 0 AND (first_view IS NULL OR first_cart < first_view))
        AS cart_without_earlier_view,
    COUNT(*) FILTER (WHERE orders > 0 AND carts = 0)
        AS purchase_without_cart,
    COUNT(*) FILTER (WHERE orders > 0) AS sessions_with_purchase
FROM sessions;
