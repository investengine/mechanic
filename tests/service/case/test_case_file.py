from datetime import UTC, datetime

import pytest

from pydantic import JsonValue

from mechanic.service.case.case_file import CaseFile, CitedResult
from mechanic.service.case.events import CaseEvent, EvidenceRecorded, StoredEvent
from tests.case_builders import case_id, evidence, received, started


def stored(seq: int, event: CaseEvent, run: str = "run-1") -> StoredEvent[CaseEvent]:
    return StoredEvent(case_id(), run, seq, datetime.now(UTC), event)


def numbered(evidence_id: str, *rows: JsonValue) -> EvidenceRecorded:
    return evidence().model_copy(
        update={"evidence_id": evidence_id, "results": rows or evidence().results}
    )


E1 = numbered("E1", [17, "settled"])
E2 = numbered("E2", [9, "failed"], [10, "settled"], None)

CASE_FILE = CaseFile.from_events(
    [
        stored(1, received()),
        stored(2, started()),
        stored(3, E1),
        stored(4, received(ts="200.2"), run="run-2"),
        stored(5, E2, run="run-2"),
    ]
)


def test_a_whole_piece_of_evidence_resolves_to_its_entry() -> None:
    assert CASE_FILE.resolve("E2") == E2


def test_evidence_from_an_earlier_run_of_the_case_resolves() -> None:
    assert CASE_FILE.resolve("E1") == E1


def test_a_result_resolves_by_its_number_from_one() -> None:
    assert CASE_FILE.resolve("E2/2") == CitedResult("E2", 2, [10, "settled"])


def test_a_null_result_is_still_a_result() -> None:
    assert CASE_FILE.resolve("E2/3") == CitedResult("E2", 3, None)


@pytest.mark.parametrize(
    "ref", ["E3", "E2/4", "E2/0", "E1/-1", "E0", "2", "E2/x", "E1\n", "E1/1\n"]
)
def test_a_reference_the_case_cannot_back_resolves_to_nothing(ref: str) -> None:
    assert CASE_FILE.resolve(ref) is None
