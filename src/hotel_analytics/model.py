"""Cancellation-risk model: one probability per booking, computed at booking time.

Scored the way it would run in a hotel: at the start of every month the model is retrained on every
arrival before that month (their outcomes are known by then) and scores that month's arrivals.
"""

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from .config import RANDOM_SEED, REPORTS, TEST_START, VALID_START
from .data import load_bookings, split
from .features import FEATURES, LEAKY, align_categories, build_frame

PARAMS = dict(
    objective="binary",
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=40,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=1.0,
    seed=RANDOM_SEED,
    verbose=-1,
)

# Columns handed to the model only in the leakage demonstration.
LEAKY_DEMO_COLS = ["parking_spaces", "assigned_room_type", "booking_changes", "country_code"]


def _matrices(train, score, extra_cols=(), drop_cols=()):
    """Model matrices for a training frame and a frame to score, with shared category levels."""
    X_train, vocab = build_frame(train)
    X_score, _ = build_frame(score, vocab)
    for col in extra_cols:
        if train[col].dtype == object:
            X_train[col] = train[col].astype("category")
            X_score[col] = score[col]
        else:
            X_train[col], X_score[col] = train[col].astype(float), score[col].astype(float)
    X_score = align_categories(X_score, X_train)
    for col in extra_cols:
        if isinstance(X_train[col].dtype, pd.CategoricalDtype):
            X_score[col] = pd.Categorical(X_score[col].astype(str), categories=X_train[col].cat.categories)
    return X_train.drop(columns=list(drop_cols)), X_score.drop(columns=list(drop_cols))


def choose_rounds(sets, extra_cols=(), drop_cols=()) -> int:
    """Number of trees, chosen once by early stopping on fit -> valid. Never looks at 2017."""
    X_fit, X_valid = _matrices(sets["fit"], sets["valid"], extra_cols, drop_cols)
    probe = lgb.train(
        PARAMS,
        lgb.Dataset(X_fit, sets["fit"].is_canceled.astype(int)),
        num_boost_round=3000,
        valid_sets=[lgb.Dataset(X_valid, sets["valid"].is_canceled.astype(int))],
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    return probe.best_iteration


def walk_forward(bookings, start, end, rounds, extra_cols=(), drop_cols=()):
    """Score arrivals in [start, end) month by month, each month with a model trained on all earlier
    arrivals. Returns (probabilities aligned to the scored rows, the last month's model)."""
    scored, model = [], None
    for month in pd.date_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="MS"):
        train = bookings[bookings.arrival_date < month]
        target = bookings[(bookings.arrival_date >= month) & (bookings.arrival_date < month + pd.offsets.MonthBegin(1))]
        X_train, X_target = _matrices(train, target, extra_cols, drop_cols)
        model = lgb.train(PARAMS, lgb.Dataset(X_train, train.is_canceled.astype(int)), num_boost_round=rounds)
        scored.append(pd.Series(model.predict(X_target), index=target.index))
    return pd.concat(scored), model


def score_period(bookings, sets, period, extra_cols=(), drop_cols=()):
    rounds = choose_rounds(sets, extra_cols, drop_cols)
    start, end = (VALID_START, TEST_START) if period == "valid" else (TEST_START, bookings.arrival_date.max() + pd.Timedelta(days=1))
    p, model = walk_forward(bookings, start, end, rounds, extra_cols, drop_cols)
    return p.reindex(sets[period].index).to_numpy(), model, rounds


def random_split_accuracy(bookings, extra_cols=()) -> dict:
    """The common notebook setup: shuffle all rows, hold out 25%. Shown only to explain inflated scores."""
    X, _ = build_frame(bookings)
    for col in extra_cols:
        X[col] = bookings[col].astype("category") if bookings[col].dtype == object else bookings[col].astype(float)
    X_a, X_b, y_a, y_b = train_test_split(X, bookings.is_canceled.astype(int), test_size=0.25, random_state=RANDOM_SEED)
    p = lgb.train(PARAMS, lgb.Dataset(X_a, y_a), num_boost_round=1500).predict(X_b)
    return scores(y_b, p)


def scores(y, p, threshold=0.5) -> dict:
    y, p = np.asarray(y).astype(int), np.asarray(p)
    pred = (p >= threshold).astype(int)
    return {
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred)), 4),
        "recall": round(float(recall_score(y, pred)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
        "log_loss": round(float(log_loss(y, p)), 4),
        "base_rate": round(float(y.mean()), 4),
        "majority_class_accuracy": round(float(max(y.mean(), 1 - y.mean())), 4),
        "n": int(len(y)),
    }


def weekly_forecast(test: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    """Predicted vs actual cancellations per hotel per arrival week: the number a revenue manager
    plans overbooking on."""
    df = test[["hotel", "arrival_date", "is_canceled"]].copy()
    df["p"] = p
    df["week"] = df.arrival_date.dt.to_period("W-SUN").dt.start_time
    return df.groupby(["hotel", "week"], as_index=False).agg(
        bookings=("p", "size"), predicted=("p", "sum"), actual=("is_canceled", "sum")
    )


def calibration_table(y, p, bins=10) -> list[dict]:
    df = pd.DataFrame({"y": np.asarray(y).astype(int), "p": np.asarray(p)})
    df["bin"] = pd.cut(df.p, np.linspace(0, 1, bins + 1), include_lowest=True)
    out = df.groupby("bin", observed=True).agg(n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"))
    return [
        {"bin": str(b), "n": int(r.n), "predicted": round(r.predicted, 4), "actual": round(r.actual, 4)}
        for b, r in out.iterrows()
    ]


def run() -> dict:
    bookings = load_bookings()
    sets = split(bookings)
    y_test = sets["test"].is_canceled.astype(int)

    p_test, last_model, rounds = score_period(bookings, sets, "test")
    p_valid, _, _ = score_period(bookings, sets, "valid")
    p_leaky, _, _ = score_period(bookings, sets, "test", extra_cols=LEAKY_DEMO_COLS)
    # Special requests can be added after booking; show what the model loses without them.
    p_no_requests, _, _ = score_period(bookings, sets, "test", drop_cols=["special_requests"])

    weekly = weekly_forecast(sets["test"], p_test)
    importance = pd.Series(last_model.feature_importance("gain"), index=last_model.feature_name())
    importance = (importance / importance.sum()).sort_values(ascending=False)

    metrics = {
        "split": {k: int(len(v)) for k, v in sets.items()},
        "scoring": "monthly walk-forward: each month scored by a model trained on all earlier arrivals",
        "boosting_rounds": int(rounds),
        "features": FEATURES,
        "excluded_as_leaky": LEAKY,
        "test": scores(y_test, p_test),
        "test_with_leaky_columns": scores(y_test, p_leaky),
        "test_without_special_requests": scores(y_test, p_no_requests),
        "random_split": random_split_accuracy(bookings),
        "random_split_with_leaky_columns": random_split_accuracy(bookings, LEAKY_DEMO_COLS),
        "valid": scores(sets["valid"].is_canceled, p_valid),
        "calibration_test": calibration_table(y_test, p_test),
        "weekly_forecast": {
            "weeks": int(len(weekly)),
            "weighted_abs_error": round(float((weekly.predicted - weekly.actual).abs().sum() / weekly.actual.sum()), 4),
            "total_predicted": round(float(weekly.predicted.sum()), 1),
            "total_actual": int(weekly.actual.sum()),
            "total_error": round(float((weekly.predicted.sum() - weekly.actual.sum()) / weekly.actual.sum()), 4),
        },
        "feature_importance_gain": {k: round(float(v), 4) for k, v in importance.head(15).items()},
    }

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "model_metrics.json").write_text(json.dumps(metrics, indent=2))
    weekly.to_csv(REPORTS / "weekly_forecast_2017.csv", index=False)
    scored = pd.concat([
        sets["valid"].assign(split="valid", p_cancel=p_valid),
        sets["test"].assign(split="test", p_cancel=p_test),
    ])
    keep = ["booking_id", "split", "hotel", "arrival_date", "deposit_type", "nights", "adr_eur",
            "room_revenue_eur", "is_canceled", "p_cancel"]
    scored[keep].to_parquet(REPORTS / "scored_bookings.parquet", index=False)
    return metrics


if __name__ == "__main__":
    m = run()
    keys = ["boosting_rounds", "test", "test_with_leaky_columns", "test_without_special_requests",
            "random_split", "random_split_with_leaky_columns", "valid", "weekly_forecast", "feature_importance_gain"]
    print(json.dumps({k: m[k] for k in keys}, indent=2))
