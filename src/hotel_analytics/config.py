from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "hotel_bookings.csv"
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
REPORTS = ROOT / "reports"
SITE = ROOT / "site"

# Time split. Everything is decided with data that existed at the decision point:
# fit on arrivals before VALID_START, tune on VALID_START..TEST_START, report on TEST_START onwards.
VALID_START = date(2016, 9, 1)
TEST_START = date(2017, 1, 1)

RANDOM_SEED = 7
