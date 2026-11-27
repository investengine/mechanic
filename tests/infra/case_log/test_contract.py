"""What every CaseLog store guarantees. The PostgreSQL store adds itself to the
`case_log` fixture's params and must pass the same tests.

The fixture gives each test an empty store, and run IDs are fresh UUIDs, as the
dispatcher makes them. The concurrent tests can't fail on the in-memory store,
which never awaits while it holds its lock; they prove something only on a store
whose writers really overlap, such as PostgreSQL with more than one connection."""

import asyncio

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from mechanic.infra.case_log.memory import InMemoryCaseLog
from mechanic.service.case.errors import Duplicate, InvalidEntry, RunSealed
from mechanic.service.case.events import EvidenceRecorded, RunStatus
from mechanic.service.case.ports import CaseLog
from tests.case_builders import case_id, evidence, finished, open_run, received, started


CASE = case_id()


@pytest.fixture(params=["memory"])
def case_log(request: pytest.FixtureRequest) -> CaseLog:
    assert request.param == "memory"
    return InMemoryCaseLog()


async def test_entries_read_back_in_order_numbered_from_one(case_log: CaseLog) -> None:
    run = await open_run(case_log)
    await case_log.append(CASE, run, started())
    await case_log.append(CASE, run, finished(RunStatus.INCONCLUSIVE))

    entries = await case_log.read(CASE)

    assert [(e.seq, e.event.type_name) for e in entries] == [
        (1, "message_received"),
        (2, "run_started"),
        (3, "run_finished"),
    ]
    assert entries[2].event == finished(RunStatus.INCONCLUSIVE)
    assert {(e.case_id, e.run_id) for e in entries} == {(CASE, run)}


async def test_append_returns_the_entry_as_read_returns_it(case_log: CaseLog) -> None:
    run = await open_run(case_log)

    stored = await case_log.append(CASE, run, evidence([17, "settled"]))

    assert (await case_log.read(CASE))[-1] == stored


async def test_the_store_stamps_utc_time(case_log: CaseLog) -> None:
    before = datetime.now(UTC)
    await open_run(case_log)

    (entry,) = await case_log.read(CASE)

    assert entry.at.utcoffset() == timedelta(0)
    assert before <= entry.at <= datetime.now(UTC)


async def test_read_after_returns_only_later_entries(case_log: CaseLog) -> None:
    run = await open_run(case_log)
    await case_log.append(CASE, run, started())
    await case_log.append(CASE, run, evidence())

    assert [e.seq for e in await case_log.read(CASE, after=1)] == [2, 3]


async def test_cases_are_numbered_and_read_separately(case_log: CaseLog) -> None:
    await open_run(case_log, "C1/100.1")
    other = await open_run(case_log, "C1/200.2")

    entries = await case_log.read(case_id("C1/200.2"))

    assert [(e.run_id, e.seq) for e in entries] == [(other, 1)]


async def test_concurrent_appends_get_every_number_once(case_log: CaseLog) -> None:
    run = await open_run(case_log)

    await asyncio.gather(*(case_log.append(CASE, run, evidence()) for _ in range(20)))

    assert [e.seq for e in await case_log.read(CASE)] == list(range(1, 22))


async def test_a_finished_run_takes_no_more_entries(case_log: CaseLog) -> None:
    run = await open_run(case_log)
    await case_log.append(CASE, run, finished())

    with pytest.raises(RunSealed):
        await case_log.append(CASE, run, evidence())


async def test_sealing_one_run_leaves_the_next_run_in_the_case_open(
    case_log: CaseLog,
) -> None:
    first = await open_run(case_log)
    await case_log.append(CASE, first, finished())
    second = await open_run(case_log)

    await case_log.append(CASE, second, started())

    assert (await case_log.read(CASE))[-1].run_id == second


async def test_a_redelivered_message_is_a_duplicate_even_if_its_run_never_finished(
    case_log: CaseLog,
) -> None:
    await case_log.append(CASE, uuid4().hex, received(ts="100.1"))

    with pytest.raises(Duplicate):
        await case_log.append(CASE, uuid4().hex, received(ts="100.1"))


async def test_a_redelivered_message_is_a_duplicate_in_any_case(
    case_log: CaseLog,
) -> None:
    await case_log.append(CASE, uuid4().hex, received(ts="100.1"))

    with pytest.raises(Duplicate):
        await case_log.append(
            case_id("C1/200.2"), uuid4().hex, received("C1/200.2", ts="100.1")
        )


async def test_evidence_ids_count_up_per_case_across_runs(case_log: CaseLog) -> None:
    first = await open_run(case_log)
    await case_log.append(CASE, first, evidence())
    await case_log.append(CASE, first, started())
    await case_log.append(CASE, first, evidence())
    await case_log.append(CASE, first, finished())
    second = await open_run(case_log)
    other_case = await open_run(case_log, "C1/200.2")

    third = await case_log.append(CASE, second, evidence())
    elsewhere = await case_log.append(case_id("C1/200.2"), other_case, evidence())

    ids = [
        e.event.evidence_id
        for e in await case_log.read(CASE)
        if isinstance(e.event, EvidenceRecorded)
    ]
    assert ids == ["E1", "E2", "E3"]
    assert third.event.evidence_id == "E3"
    assert elsewhere.event.evidence_id == "E1"


async def test_concurrent_evidence_gets_distinct_ids_with_no_gaps(
    case_log: CaseLog,
) -> None:
    run = await open_run(case_log)

    stored = await asyncio.gather(
        *(case_log.append(CASE, run, evidence()) for _ in range(10))
    )

    ids = {e.event.evidence_id for e in stored}
    assert ids == {f"E{n}" for n in range(1, 11)}


async def test_evidence_that_brings_its_own_id_is_invalid(case_log: CaseLog) -> None:
    run = await open_run(case_log)

    with pytest.raises(InvalidEntry):
        await case_log.append(
            CASE, run, evidence().model_copy(update={"evidence_id": "E7"})
        )


async def test_an_entry_json_cannot_hold_is_invalid(case_log: CaseLog) -> None:
    run = await open_run(case_log)

    with pytest.raises(InvalidEntry):
        await case_log.append(CASE, run, evidence([17, float("nan")]))


async def test_a_value_that_skipped_validation_is_invalid(case_log: CaseLog) -> None:
    run = await open_run(case_log)
    unchecked = evidence().model_copy(update={"results": ([17, date(2026, 11, 12)],)})

    with pytest.raises(InvalidEntry):
        await case_log.append(CASE, run, unchecked)


async def test_a_message_filed_under_another_case_is_invalid(
    case_log: CaseLog,
) -> None:
    with pytest.raises(InvalidEntry):
        await case_log.append(case_id("C1/200.2"), uuid4().hex, received("C1/100.1"))


async def test_an_entry_for_a_run_with_no_message_in_the_case_is_invalid(
    case_log: CaseLog,
) -> None:
    await open_run(case_log)

    with pytest.raises(InvalidEntry):
        await case_log.append(CASE, uuid4().hex, started())


async def test_a_run_id_from_another_case_is_invalid(case_log: CaseLog) -> None:
    run = await open_run(case_log, "C1/200.2")

    with pytest.raises(InvalidEntry):
        await case_log.append(CASE, run, received("C1/100.1"))


async def test_a_rejected_entry_takes_no_number(case_log: CaseLog) -> None:
    sealed = await open_run(case_log)
    await case_log.append(CASE, sealed, finished())
    run = await open_run(case_log)
    await case_log.append(CASE, run, evidence())
    with pytest.raises(InvalidEntry):
        await case_log.append(CASE, run, evidence([float("nan")]))
    with pytest.raises(Duplicate):
        await case_log.append(CASE, run, (await case_log.read(CASE))[0].event)
    with pytest.raises(RunSealed):
        await case_log.append(CASE, sealed, evidence())

    stored = await case_log.append(CASE, run, evidence())

    assert stored.seq == 5
    assert stored.event.evidence_id == "E2"
