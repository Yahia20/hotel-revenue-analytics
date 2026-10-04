"""Backtest of a risk-based deposit policy.

Rule under test: a "No Deposit" booking whose cancellation risk is at or above a threshold must pay the
first night up front, non-refundable. Everything else keeps today's terms.

Per flagged booking, against today's terms:
  * it would have cancelled -> the hotel keeps the first night, unless the guest walks away at the
    deposit request (then nothing changes: no booking, no cancellation).
      gain = (1 - walkaway) * first_night
  * it would have stayed    -> some guests walk away at the deposit request; the hotel loses the stay,
    minus what it recovers by reselling the room.
      loss = walkaway * stay_revenue * (1 - resale)

Two inputs are business assumptions, not data, so every result is shown across a grid of them:
  walkaway - share of guests asked for a deposit who book elsewhere instead
  resale   - share of lost stay revenue the hotel recovers by selling the room to someone else
The threshold is chosen on Sep-Dec 2016 bookings and then applied unchanged to Jan-Aug 2017.
"""

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import REPORTS

BASE = {"walkaway": 0.20, "resale": 0.30}  # conservative middle of the grid
WALKAWAY_GRID = [0.05, 0.10, 0.20, 0.30]
RESALE_GRID = [0.0, 0.30, 0.60]
THRESHOLDS = np.round(np.arange(0.0, 1.0001, 0.01), 2)


@dataclass(frozen=True)
class Outcome:
    threshold: float
    flagged: int
    flagged_share: float
    cancellations_caught: int
    catch_rate: float
    gain_eur: float
    loss_eur: float
    net_eur: float


def evaluate(df: pd.DataFrame, threshold: float, walkaway: float, resale: float) -> Outcome:
    """Net effect of the rule at one threshold. `df` holds eligible bookings only."""
    flagged = df.p_cancel >= threshold
    first_night = df.adr_eur * np.minimum(df.nights, 1)
    gain = ((1 - walkaway) * first_night)[flagged & df.is_canceled].sum()
    loss = (walkaway * df.room_revenue_eur * (1 - resale))[flagged & ~df.is_canceled].sum()
    caught = int((flagged & df.is_canceled).sum())
    return Outcome(
        threshold=float(threshold),
        flagged=int(flagged.sum()),
        flagged_share=round(float(flagged.mean()), 4),
        cancellations_caught=caught,
        catch_rate=round(caught / max(int(df.is_canceled.sum()), 1), 4),
        gain_eur=round(float(gain), 2),
        loss_eur=round(float(loss), 2),
        net_eur=round(float(gain - loss), 2),
    )


def best_threshold(df: pd.DataFrame, walkaway: float, resale: float) -> float:
    nets = [evaluate(df, t, walkaway, resale).net_eur for t in THRESHOLDS]
    return float(THRESHOLDS[int(np.argmax(nets))])


def eligible(scored: pd.DataFrame) -> pd.DataFrame:
    """Bookings the rule could change: they carry no deposit today."""
    df = scored[scored.deposit_type == "No Deposit"].copy()
    df["is_canceled"] = df.is_canceled.astype(bool)
    return df


def run() -> dict:
    scored = pd.read_parquet(REPORTS / "scored_bookings.parquet")
    valid = eligible(scored[scored.split == "valid"])
    test = eligible(scored[scored.split == "test"])

    grid = []
    for walkaway in WALKAWAY_GRID:
        for resale in RESALE_GRID:
            t = best_threshold(valid, walkaway, resale)
            grid.append({
                "walkaway": walkaway,
                "resale": resale,
                "threshold_from_2016": t,
                "net_eur_2017": evaluate(test, t, walkaway, resale).net_eur,
                "blanket_deposit_net_eur_2017": evaluate(test, 0.0, walkaway, resale).net_eur,
            })

    t_base = best_threshold(valid, **BASE)
    base = evaluate(test, t_base, **BASE)
    curve = [evaluate(test, t, **BASE).__dict__ for t in THRESHOLDS]
    per_hotel = {
        hotel: evaluate(group, t_base, **BASE).__dict__ for hotel, group in test.groupby("hotel")
    }

    result = {
        "period": "arrivals 2017-01-01 to 2017-08-31",
        "currency": "EUR",
        "assumptions_base": BASE,
        "eligible_bookings_2017": int(len(test)),
        "eligible_cancellations_2017": int(test.is_canceled.sum()),
        "eligible_cancelled_revenue_eur_2017": round(float(test.room_revenue_eur[test.is_canceled].sum()), 2),
        "chosen_threshold": t_base,
        "base_case": base.__dict__,
        "blanket_deposit_base_case": evaluate(test, 0.0, **BASE).__dict__,
        "per_hotel_base_case": per_hotel,
        "sensitivity": grid,
        "threshold_curve_base_case": curve,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "policy_backtest.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: r[k] for k in ["chosen_threshold", "base_case", "blanket_deposit_base_case", "per_hotel_base_case"]}, indent=2))
    print(pd.DataFrame(r["sensitivity"]).to_string(index=False))
