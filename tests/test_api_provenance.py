"""Every number the API returns carries a provenance label."""

from typing import Any

from control_plane.auth import FIXTURE_HEADER
from control_plane.contracts import Provenance
from tests.conftest import make_client

LABELS = {p.value for p in Provenance}
H = {FIXTURE_HEADER: "admin@example.com"}


def _bare_numbers(node: Any, path: str = "") -> list[str]:
    """Paths of numbers that are not the ``value`` of a provenance-labelled metric."""
    found: list[str] = []
    if isinstance(node, dict):
        is_metric = {"value", "unit", "provenance", "source"} <= node.keys()
        if is_metric:
            assert node["provenance"] in LABELS, path
            return found
        for key, child in node.items():
            found += _bare_numbers(child, f"{path}.{key}")
    elif isinstance(node, list):
        for i, child in enumerate(node):
            found += _bare_numbers(child, f"{path}[{i}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        found.append(path)
    return found


def test_portfolio_summary_numbers_are_labelled() -> None:
    body = make_client().get("/api/portfolio/summary", headers=H).json()
    assert _bare_numbers(body) == []
    assert body["total_apps"]["provenance"] == "FIXTURE"


def test_app_cards_numbers_are_labelled() -> None:
    body = make_client().get("/api/apps", headers=H).json()
    assert body, "fixture apps should be present"
    assert _bare_numbers(body) == []


def test_mode_reports_fixture() -> None:
    body = make_client().get("/api/mode").json()
    assert body["data_mode"] == "FIXTURE"
