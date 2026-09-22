from src.common.context import build_context
from src.common.feeds import get_feed
from src.generate.calendar import date_spine
from src.generate.fx import fx_rates


def test_fx_rates_contract():
    ctx = build_context("2026-09-11", seed=42)
    fx = fx_rates(ctx, date_spine(ctx))
    key = list(get_feed("fx_rates").business_key)
    assert not fx.duplicated(key).any()
    assert set(fx.currency) == {"USD", "GBP"}
    assert (fx.rate_date.dt.dayofweek < 5).all()
    assert (fx.rate > 0).all()
