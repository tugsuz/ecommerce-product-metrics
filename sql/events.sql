-- Raw log to a clean events table.
-- Timestamps are milliseconds since 1970 in UTC. Exact duplicate rows are dropped.
CREATE OR REPLACE TABLE events AS
SELECT DISTINCT
    to_timestamp(timestamp / 1000.0) AT TIME ZONE 'UTC' AS ts,
    visitorid       AS visitor_id,
    event           AS event,
    itemid          AS item_id,
    transactionid   AS transaction_id
FROM raw_events
WHERE event IN ('view', 'addtocart', 'transaction');
