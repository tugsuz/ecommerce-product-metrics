import duckdb
import pytest

from shopmetrics import build

MIN = 60 * 1000
DAY = 24 * 60 * MIN
MON = 1430697600000  # Monday 4 May 2015, 00:00 UTC


def make_con(rows):
    con = build.connect()
    con.execute(
        "CREATE TABLE raw_events (timestamp BIGINT, visitorid BIGINT, event VARCHAR, "
        "itemid BIGINT, transactionid BIGINT)"
    )
    con.executemany("INSERT INTO raw_events VALUES (?, ?, ?, ?, ?)", rows)
    return build.build(con)


@pytest.fixture
def con():
    rows = [
        # visitor 1: one session that goes view, cart, purchase
        (MON + 0 * MIN, 1, "view", 10, None),
        (MON + 5 * MIN, 1, "addtocart", 10, None),
        (MON + 9 * MIN, 1, "transaction", 10, 500),
        (MON + 9 * MIN, 1, "transaction", 10, 500),      # exact duplicate row
        # visitor 1 again 31 minutes later: a new session, view only
        (MON + 40 * MIN, 1, "view", 11, None),
        # visitor 2: view, then a view 29 minutes later (same session), then next week
        (MON + 1 * DAY, 2, "view", 10, None),
        (MON + 1 * DAY + 29 * MIN, 2, "view", 12, None),
        (MON + 8 * DAY, 2, "view", 12, None),
        # visitor 3: cart before any view, no purchase
        (MON + 2 * DAY, 3, "addtocart", 13, None),
        (MON + 2 * DAY + MIN, 3, "view", 13, None),
        # visitor 4: first seen in week 2
        (MON + 9 * DAY, 4, "view", 10, None),
        # padding so that weeks 1 and 2 are complete and week 3 is partial
        (MON + 15 * DAY, 5, "view", 10, None),
    ]
    return make_con(rows)


def test_duplicates_dropped(con):
    assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 11


def test_sessions_split_on_30_minute_gap(con):
    got = dict(con.execute("SELECT visitor_id, COUNT(*) FROM sessions GROUP BY 1").fetchall())
    assert got == {1: 2, 2: 2, 3: 1, 4: 1, 5: 1}


def test_funnel_counts_ordered_steps(con):
    got = dict(con.execute("SELECT step, sessions FROM funnel").fetchall())
    assert got == {"session": 7, "product view": 7 - 0, "add to cart": 1, "purchase": 1}
    exc = con.execute("SELECT * FROM funnel_exceptions").fetchone()
    assert exc == (1, 0, 1)


def test_weekly_metrics_flag_partial_week(con):
    rows = con.execute("SELECT week::VARCHAR, complete, active_visitors FROM weekly_metrics ORDER BY 1").fetchall()
    assert rows == [("2015-05-04", True, 3), ("2015-05-11", True, 2), ("2015-05-18", False, 1)]


def test_retention(con):
    rows = con.execute(
        "SELECT cohort_week::VARCHAR, bought_in_first_week, week_no, cohort_size, active "
        "FROM retention ORDER BY 1, 2, 3"
    ).fetchall()
    assert rows == [
        ("2015-05-04", False, 0, 2, 2),
        ("2015-05-04", False, 1, 2, 1),
        ("2015-05-04", True, 0, 1, 1),
        ("2015-05-11", False, 0, 1, 1),
    ]
    curve = con.execute(
        "SELECT week_no, visitors, active FROM retention_curve "
        "WHERE NOT bought_in_first_week ORDER BY 1"
    ).fetchall()
    # week 1 uses only the first cohort, the second has no later complete week
    assert curve == [(0, 3, 3), (1, 2, 1)]


def test_experiment_units(con):
    from datetime import datetime
    build.run_sql(con, "experiment_units", {
        "pre_start": datetime(2015, 5, 4), "test_start": datetime(2015, 5, 11),
        "test_end": datetime(2015, 5, 18)})
    rows = con.execute(
        "SELECT visitor_id, y_views, x_views, seen_before FROM experiment_units ORDER BY 1"
    ).fetchall()
    assert rows == [(2, 1, 2, 1), (4, 1, 0, 0)]
