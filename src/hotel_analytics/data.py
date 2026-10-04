import duckdb
import pandas as pd

from .config import TEST_START, VALID_START, WAREHOUSE


def load_bookings() -> pd.DataFrame:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        df = con.sql("select * from fct_bookings order by booking_id").df()
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    return df


def split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split by arrival date into fit / valid / train (= fit + valid) / test.

    No random shuffling: identical group-booking rows and seasonality would leak between the sets.
    """
    valid_start, test_start = pd.Timestamp(VALID_START), pd.Timestamp(TEST_START)
    return {
        "fit": df[df.arrival_date < valid_start],
        "valid": df[(df.arrival_date >= valid_start) & (df.arrival_date < test_start)],
        "train": df[df.arrival_date < test_start],
        "test": df[df.arrival_date >= test_start],
    }
