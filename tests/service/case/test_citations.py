from mechanic.service.case.case_file import CaseFile
from mechanic.service.case.citations import check_citations
from mechanic.service.case.facts import Fact
from tests.case_builders import evidence


CASE_FILE = CaseFile(
    evidence={
        "E1": evidence([17, "settled"]).model_copy(update={"evidence_id": "E1"}),
        "E2": evidence([9, "failed"], [10, "settled"]).model_copy(
            update={"evidence_id": "E2"}
        ),
    }
)


def fact(*cites: str, claim: str = "Order 17 settled") -> Fact:
    return Fact(claim=claim, cites=cites)


def test_facts_citing_evidence_and_results_in_the_case_pass() -> None:
    assert check_citations([fact("E1"), fact("E2/2", "E1/1")], CASE_FILE) == []


def test_a_citation_of_evidence_not_in_the_case_is_a_problem_of_that_fact() -> None:
    (problem,) = check_citations([fact("E1"), fact("E2", "E9")], CASE_FILE)

    assert "fact 2" in problem
    assert "E9" in problem


def test_a_citation_of_a_result_the_evidence_does_not_have_is_a_problem() -> None:
    (problem,) = check_citations([fact("E2/3")], CASE_FILE)

    assert "fact 1" in problem
    assert "E2/3" in problem


def test_every_bad_citation_is_reported_in_fact_order() -> None:
    problems = check_citations([fact("E7"), fact("E1"), fact("E2/9", "E8")], CASE_FILE)

    assert [("fact 1" in p, "fact 3" in p) for p in problems] == [
        (True, False),
        (False, True),
        (False, True),
    ]


def test_a_problem_never_quotes_the_claim() -> None:
    problems = check_citations(
        [fact("E9", claim="Client 4417 at jane@example.com was charged")], CASE_FILE
    )

    assert problems
    assert not any("4417" in p or "jane@" in p for p in problems)
