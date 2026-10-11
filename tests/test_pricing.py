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
