"""Build the static dashboard (site/index.html) from the warehouse and the report files.

Every number on the page is read from a file the pipeline wrote. Nothing is typed by hand.
"""

import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from .config import REPORTS, ROOT, SITE, WAREHOUSE

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
RUN_RESULTS = ROOT / "warehouse" / "target" / "run_results.json"


def _records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return json.loads(out.to_json(orient="records", double_precision=4))


def _dbt_summary() -> dict:
    results = json.loads(RUN_RESULTS.read_text())["results"]
    tests = [r for r in results if r["unique_id"].startswith("test.")]
    models = [r for r in results if r["unique_id"].startswith("model.")]
    status = pd.Series([r["status"] for r in tests]).value_counts().to_dict()
    warnings = [
        {"test": r["unique_id"].split(".")[2], "failures": r.get("failures")}
        for r in tests if r["status"] == "warn"
    ]
    return {
        "tests": len(tests),
        "passed": int(status.get("pass", 0)),
        "warned": int(status.get("warn", 0)),
        "failed": int(status.get("fail", 0) + status.get("error", 0)),
        "warnings": warnings,
        "models": len(models),
    }


def collect() -> dict:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        q = lambda sql: con.sql(sql).df()  # noqa: E731
        totals = q("""
            select count(*) as bookings, avg(is_canceled::int) as cancellation_rate,
                   sum(cancelled_revenue_eur) as cancelled_revenue, sum(realized_revenue_eur) as realized_revenue,
                   min(arrival_date) as first_arrival, max(arrival_date) as last_arrival
            from fct_bookings""").iloc[0]
        quality = q("""
            select count(*) as source_rows,
                   sum(dq_negative_adr::int) as negative_adr,
                   sum(dq_adr_outlier::int) as adr_outlier,
                   sum(dq_zero_guests::int) as zero_guests,
                   sum((dq_negative_adr or dq_adr_outlier or dq_zero_guests)::int) as excluded,
                   sum(dq_identical_to_another_row::int) as identical_rows,
                   sum((country_code = 'UNK')::int) as unknown_country
            from stg_bookings""").iloc[0]
        monthly = q("select * from mart_monthly_kpis order by hotel, arrival_month")
        drivers = q("select * from mart_cancellation_drivers order by dimension, value")
        cancel_timing = q("""
            select hotel,
                   quantile_cont(cancelled_days_before_arrival, 0.5) as median_days,
                   avg((cancelled_days_before_arrival <= 7)::int) as share_last_week
            from fct_bookings where reservation_status = 'Canceled' group by hotel order by hotel""")

    metrics = json.loads((REPORTS / "model_metrics.json").read_text())
    policy = json.loads((REPORTS / "policy_backtest.json").read_text())
    weekly = pd.read_csv(REPORTS / "weekly_forecast_2017.csv", parse_dates=["week"])

    return {
        "built": date.today().isoformat(),
        "totals": {k: (v.isoformat() if hasattr(v, "isoformat") else float(v)) for k, v in totals.items()},
        "quality": {k: int(v) for k, v in quality.items()},
        "dbt": _dbt_summary(),
        "monthly": _records(monthly),
        "drivers": _records(drivers),
        "cancel_timing": _records(cancel_timing),
        "model": metrics,
        "weekly": _records(weekly),
        "policy": policy,
    }


def build() -> Path:
    payload = json.dumps(collect(), separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    SITE.mkdir(exist_ok=True)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
