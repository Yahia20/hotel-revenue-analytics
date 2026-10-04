import pandas as pd

from hotel_analytics.features import CATEGORICAL, FEATURES, LEAKY, align_categories, build_frame


def sample(agent_ids):
    n = len(agent_ids)
    return pd.DataFrame({
        "arrival_date": pd.to_datetime(["2016-03-14"] * n),
        "lead_time_days": [10] * n,
        "weekend_nights": [1] * n,
        "week_nights": [2] * n,
        "adults": [2] * n,
        "children": [0] * n,
        "babies": [0] * n,
        "previous_cancellations": [0] * n,
        "previous_bookings_not_canceled": [0] * n,
        "days_in_waiting_list": [0] * n,
        "adr_eur": [90.0] * n,
        "special_requests": [1] * n,
        "is_repeated_guest": [False] * n,
        "company_id": [None] * n,
        "agent_id": agent_ids,
        "hotel": ["City Hotel"] * n,
        "meal_plan": ["BB"] * n,
        "market_segment": ["Online TA"] * n,
        "distribution_channel": ["TA/TO"] * n,
        "customer_type": ["Transient"] * n,
        "deposit_type": ["No Deposit"] * n,
        "reserved_room_type": ["A"] * n,
    })


def test_no_post_booking_column_reaches_the_model():
    assert not set(FEATURES) & set(LEAKY)


def test_agent_outside_training_vocabulary_is_pooled():
    _, vocab = build_frame(sample([9, 9, 240]))
    X, _ = build_frame(sample([9, 777, None]), vocab)
    assert X["agent"].astype(str).tolist() == ["9", "other", "none"]


def test_arrival_weekday_is_monday_zero():
    X, _ = build_frame(sample([9]))
    assert X.arrival_weekday_num.iloc[0] == 0


def test_unseen_category_in_scoring_data_becomes_missing():
    train, _ = build_frame(sample([9]))
    new = sample([9]).assign(market_segment="Aviation")
    X, _ = build_frame(new)
    aligned = align_categories(X, train)
    assert aligned.market_segment.isna().all()
    assert all(aligned[c].dtype.categories.equals(train[c].dtype.categories) for c in CATEGORICAL)
