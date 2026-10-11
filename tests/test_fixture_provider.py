from control_plane.contracts import Provenance
from control_plane.providers.fixture import FixtureProvider

SCHEMA = {"properties": {"intent": {"enum": ["a", "b", "c", "out_of_scope"]}}}


def test_fixture_provider_is_deterministic_and_labelled() -> None:
    p = FixtureProvider()
    first = p.generate_structured("m", "prompt", SCHEMA, 1024, 30)
    second = p.generate_structured("m", "prompt", SCHEMA, 1024, 30)
    assert first == second
    assert first.provenance is Provenance.FIXTURE
    assert first.output["intent"] in SCHEMA["properties"]["intent"]["enum"]
    assert first.output_tokens <= 1024


def test_fixture_provider_varies_with_input() -> None:
    p = FixtureProvider()
    outs = {
        p.generate_structured("m", f"case {i}", SCHEMA, 64, 30).output["intent"] for i in range(40)
    }
    assert len(outs) > 1
