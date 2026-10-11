"""Price card parsing against saved copies of the official pricing pages (2026-10-11)."""

from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

from control_plane import pricing as p

FIX = Path(__file__).parent / "fixtures"
VERTEX = (FIX / "vertex_pricing_2026-10-11.txt").read_text()


@pytest.mark.parametrize(
    ("model", "on", "inp", "out", "cached"),
    [
        ("gemini-3.1-flash-lite", date(2026, 10, 11), "0.25", "1.5", "0.025"),
        ("gemini-3.8-flash", date(2026, 10, 11), "0.75", "3.75", "0.075"),
        ("gemini-3.8-flash", date(2027, 1, 2), "1.5", "7.5", "0.15"),
    ],
)
def test_vertex_standard_global_prices(
    model: str, on: date, inp: str, out: str, cached: str
) -> None:
    price, _ = p._vertex_section_prices(VERTEX, model, on)
    assert (price.input, price.output, price.cached_input) == (
        Fraction(inp),
        Fraction(out),
        Fraction(cached),
    )


def test_vertex_regional_is_dearer_than_global() -> None:
    glob, _ = p._vertex_section_prices(VERTEX, "gemini-3.8-flash", date(2026, 10, 11))
    regional, _ = p._vertex_section_prices(
        VERTEX, "gemini-3.8-flash", date(2026, 10, 11), "Non-global"
    )
    assert regional.input > glob.input


def test_unknown_model_or_broken_page_refuses() -> None:
    with pytest.raises(p.PriceCheckError):
        p._vertex_section_prices(VERTEX, "gemini-9-ultra", date(2026, 10, 11))
    with pytest.raises(p.PriceCheckError):
        p._vertex_section_prices("nothing here", "gemini-3.8-flash", date(2026, 10, 11))


def test_gemini_api_page_parses() -> None:
    text = p._page_text((FIX / "gemini_pricing_2026-10-11.html").read_text())
    price, _ = p._section_prices(text, "gemini-3.1-flash-lite", date(2026, 10, 11))
    assert price.input == Fraction("0.25")


def test_cached_reservation_and_storage_math() -> None:
    price = p.ModelPrice(Fraction(1), Fraction(2), Fraction(1, 10), Fraction(1, 1_000_000))
    # suffix 100 -> 110 at $1/M = 110; cached 3,000 -> 3,300 at $0.10/M = 330; 256 cap at $2 = 512
    assert price.reservation_micros(100, 256, cached_tokens=3000) == 110 + 330 + 512
    # 3,400 tokens for one hour at $0.000001 per token-hour = $0.0034 = 3,400 micros
    assert price.storage_micros(3400, 3600) == 3400
    assert price.storage_micros(3400, 1800) == 1700


def test_vertex_storage_price_parses() -> None:
    for model in ("gemini-3.1-flash-lite", "gemini-3.8-flash"):
        storage, _ = p._vertex_storage_price(VERTEX, model)
        assert storage == Fraction("0.000001")
