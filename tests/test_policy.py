import pandas as pd
import pytest

from hotel_analytics.policy import best_threshold, eligible, evaluate


def bookings(rows):
    return pd.DataFrame(rows, columns=["p_cancel", "adr_eur", "nights", "room_revenue_eur", "is_canceled"])


def test_flagged_cancellation_keeps_first_night_minus_walkaways():
    df = bookings([(0.9, 100.0, 3, 300.0, True)])
    out = evaluate(df, threshold=0.5, walkaway=0.1, resale=0.3)
    assert out.gain_eur == pytest.approx(90.0)
    assert out.loss_eur == 0
    assert out.cancellations_caught == 1


def test_flagged_stay_costs_walkaway_share_of_unrecovered_revenue():
    df = bookings([(0.9, 100.0, 3, 300.0, False)])
    out = evaluate(df, threshold=0.5, walkaway=0.1, resale=0.3)
    assert out.loss_eur == pytest.approx(0.1 * 300 * 0.7)
    assert out.net_eur == pytest.approx(-21.0)


def test_bookings_below_threshold_are_untouched():
    df = bookings([(0.2, 100.0, 3, 300.0, True), (0.2, 100.0, 3, 300.0, False)])
    out = evaluate(df, threshold=0.5, walkaway=0.1, resale=0.3)
    assert (out.flagged, out.gain_eur, out.loss_eur) == (0, 0, 0)


def test_day_use_booking_has_no_first_night_to_keep():
    df = bookings([(0.9, 0.0, 0, 0.0, True)])
    assert evaluate(df, threshold=0.5, walkaway=0.1, resale=0.3).gain_eur == 0


def test_best_threshold_skips_low_risk_stays_that_would_cost_money():
    df = bookings([
        (0.95, 100.0, 1, 100.0, True),
        (0.30, 100.0, 10, 1000.0, False),
    ])
    assert best_threshold(df, walkaway=0.5, resale=0.0) > 0.30


def test_only_no_deposit_bookings_are_eligible():
    scored = pd.DataFrame({
        "deposit_type": ["No Deposit", "Non Refund", "Refundable"],
        "is_canceled": [1, 1, 0],
    })
    assert eligible(scored).deposit_type.tolist() == ["No Deposit"]
