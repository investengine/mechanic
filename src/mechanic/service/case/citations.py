"""The citation check: every fact cites evidence the case holds."""

from collections.abc import Sequence

from mechanic.service.case.case_file import CaseFile
from mechanic.service.case.facts import Fact


def check_citations(facts: Sequence[Fact], case_file: CaseFile) -> list[str]:
    """One problem per citation the case can't back, in fact order. A stage check:
    the problems go back to the model, and when a stage gives up they can end up in
    a reply's gaps, so they name the fact by number and never quote its claim. A
    fact citing nothing can't be built, so it never reaches here."""
    return [
        f"fact {number} cites {ref}, which isn't in the case: cite evidence by the "
        "ID it was given, or one of its results as E4/2"
        for number, fact in enumerate(facts, start=1)
        for ref in fact.cites
        if case_file.resolve(ref) is None
    ]
