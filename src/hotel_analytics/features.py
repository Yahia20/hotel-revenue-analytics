"""Which columns the model may see.

A column is allowed only if its value is known when the booking is made. The source records every
field as of arrival or cancellation, so some fields are filled in later and give the outcome away.
"""

import pandas as pd

NUMERIC = [
    "lead_time_days",
    "weekend_nights",
    "week_nights",
    "adults",
    "children",
    "babies",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "days_in_waiting_list",
    "adr_eur",
    "special_requests",
    "arrival_weekday_num",
    "is_repeated_guest",
    "has_company",
]

CATEGORICAL = [
    "hotel",
    "meal_plan",
    "market_segment",
    "distribution_channel",
    "customer_type",
    "deposit_type",
    "reserved_room_type",
    "agent",
]

FEATURES = NUMERIC + CATEGORICAL

# Arrival month and week are left out on purpose: with about 18 months of history the model learns the
# quirks of one particular year from them, and 2017 accuracy drops (ROC AUC 0.842 without, 0.838 with).

# Filled in at check-in or later. Each one alone separates cancelled from kept bookings far too well.
LEAKY = {
    "parking_spaces": "recorded on arrival; no cancelled booking has one",
    "assigned_room_type": "assigned at check-in; a mismatch means the guest showed up",
    "booking_changes": "counts changes up to arrival, so kept bookings accumulate more",
    "country_code": "corrected at check-in; cancelled bookings keep the default (PRT)",
    "reservation_status": "is the outcome",
    "reservation_status_date": "is the outcome date",
}

TOP_AGENTS = 30  # agents outside the busiest 30 are pooled, so rare IDs cannot be memorised


def build_frame(bookings: pd.DataFrame, agent_vocab: list[int] | None = None) -> tuple[pd.DataFrame, list[int]]:
    """Return the model matrix and the agent vocabulary used (fit it on training rows only)."""
    df = bookings.copy()
    arrival = pd.to_datetime(df["arrival_date"])
    df["arrival_weekday_num"] = arrival.dt.weekday
    df["is_repeated_guest"] = df["is_repeated_guest"].astype(int)
    df["has_company"] = df["company_id"].notna().astype(int)

    if agent_vocab is None:
        agent_vocab = df["agent_id"].dropna().astype(int).value_counts().head(TOP_AGENTS).index.tolist()
    agent = df["agent_id"].astype("Int64")
    df["agent"] = agent.where(agent.isin(agent_vocab)).astype(str).replace("<NA>", "other")
    df.loc[df["agent_id"].isna(), "agent"] = "none"

    X = df[FEATURES].copy()
    for col in CATEGORICAL:
        X[col] = X[col].astype("category")
    return X, agent_vocab


def align_categories(X: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Give X the same category levels as the training matrix, so codes mean the same thing."""
    X = X.copy()
    for col in CATEGORICAL:
        X[col] = pd.Categorical(X[col].astype(str), categories=reference[col].cat.categories)
    return X
