import pytest

from pydantic import ValidationError

from mechanic.service.case.facts import Fact


def test_fact_without_citations_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Fact(claim="The order settled on 12 Nov", cites=())


@pytest.mark.parametrize("ref", ["E4", "E12", "E4/1", "E12/30"])
def test_fact_accepts_well_formed_citations(ref: str) -> None:
    assert Fact(claim="claim", cites=(ref,)).cites == (ref,)


@pytest.mark.parametrize(
    "ref", ["E0", "E04", "e4", "4", "E", "E4/", "E4/0", "E4/01", "E4/1/2", " E4"]
)
def test_fact_rejects_malformed_citations(ref: str) -> None:
    with pytest.raises(ValidationError):
        Fact(claim="claim", cites=("E1", ref))
