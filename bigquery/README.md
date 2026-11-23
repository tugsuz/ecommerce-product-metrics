# The same pipeline on BigQuery

`build.sql` is the pipeline in GoogleSQL. It builds the same tables as the DuckDB
version (`events`, `session_events`, `sessions`, `funnel`, `weekly_metrics`,
`retention`) and ends with a check query whose expected values are in the comments.

## Run it (free BigQuery sandbox, no billing account)

1. Open https://console.cloud.google.com/bigquery and create a project.
2. In the Explorer pane, create a dataset named `shop` (location US).
3. In the dataset, choose Create table, source Upload, file `events.csv`, table name
   `raw_events`. Enter the schema as text:
   `timestamp:INTEGER,visitorid:INTEGER,event:STRING,itemid:INTEGER,transactionid:INTEGER`
   and set "Header rows to skip" to 1.
4. Open a new query tab, paste `build.sql`, and run it.
5. The last result should read 2,755,641 events, 1,761,675 sessions, 10,495 funnel
   purchases and 19 complete weeks.

Sandbox tables expire after 60 days. Rerun the script to rebuild them.

## Dashboard

The tables `shop.weekly_metrics`, `shop.funnel` and `shop.retention` are shaped for a
dashboard tool. In Looker Studio, add each as a BigQuery data source and build:

- a time series of `active_visitors` and one of `session_conversion` by `week`,
  filtered to `complete = true`
- a bar chart of `sessions` by `step` from `funnel`, sorted by `step_no`
- a pivot table of `retention` with `cohort_week` in rows and `week_no` in columns,
  with a control for `bought_in_first_week`
