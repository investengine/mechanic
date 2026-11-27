import datetime

from decimal import Decimal

import pytest

from pydantic import ValidationError

from mechanic.service.case.errors import InvalidEntry
from mechanic.service.case.events import (
    Answered,
    EvidenceRecorded,
    FindingsRecorded,
    Message,
    RunFinished,
    RunStatus,
    Spend,
    decode,
    encode,
)
from mechanic.service.case.facts import Fact
from mechanic.service.case.reply import Outcome, Reply


def evidence(**overrides: object) -> EvidenceRecorded:
    fields: dict[str, object] = {
        "stage": "investigate",
        "tool": "replica_query",
        "request": "SELECT id, status FROM orders WHERE id = 17 LIMIT 200",
        "results": [[17, "settled"]],
        "metadata": {"columns": ["id", "status"], "truncated": False},
    }
    return EvidenceRecorded.model_validate(fields | overrides)


def test_case_id_is_origin_and_conversation() -> None:
    message = Message(
        origin="slack:help-dev-en",
        origin_ref="C02BQ102CLV/1700000000.123456",
        conversation_ref="C02BQ102CLV/1700000000.123456",
        requester="slack:U012AB3CD",
        text="Why did order 17 not settle?",
    )

    assert message.case_id == "slack:help-dev-en/C02BQ102CLV/1700000000.123456"


def test_spend_survives_the_round_trip_exactly() -> None:
    finished = RunFinished(
        status=RunStatus.CONCLUDED,
        reason="",
        spent=Spend(model_requests=7, cost_usd=Decimal("0.0421")),
    )

    decoded = decode("run_finished", encode(finished))

    assert decoded == finished
    assert isinstance(decoded, RunFinished)
    assert decoded.spent.cost_usd == Decimal("0.0421")


class TimelineReply(Reply):
    """A service's own reply type, as a handler would declare it."""

    summary: str
    happened_on: datetime.date


TIMELINE = TimelineReply(
    outcome=Outcome.CONCLUDED,
    facts=(Fact(claim="Payment 9 failed", cites=("E2/1",), when="2026-11-12"),),
    summary="The payment failed and was retried the next day",
    happened_on=datetime.date(2026, 11, 12),
)


def test_answered_keeps_every_field_of_the_reply_subclass() -> None:
    answered = Answered.of(TIMELINE)

    assert answered.reply_type == "TimelineReply"
    assert answered.reply == {
        "outcome": "concluded",
        "facts": [
            {"claim": "Payment 9 failed", "cites": ["E2/1"], "when": "2026-11-12"}
        ],
        "summary": "The payment failed and was retried the next day",
        "happened_on": "2026-11-12",
    }


def test_answered_types_what_generic_code_reads() -> None:
    answered = Answered.of(TIMELINE)

    assert answered.outcome == Outcome.CONCLUDED
    assert answered.facts == TIMELINE.facts


def test_the_service_reads_its_reply_back_from_the_log() -> None:
    decoded = decode("answered", encode(Answered.of(TIMELINE)))

    assert isinstance(decoded, Answered)
    assert TimelineReply.model_validate(decoded.reply) == TIMELINE


def test_a_reply_with_no_facts_is_a_plain_answer() -> None:
    answered = Answered.of(Reply(outcome=Outcome.DECLINED))

    assert answered.facts == ()
    assert answered.reply == {"outcome": "declined", "facts": []}


def test_evidence_results_must_be_json() -> None:
    with pytest.raises(ValidationError):
        evidence(results=[[17, datetime.date(2026, 11, 12)]])


def test_encoding_rejects_a_value_json_cannot_hold() -> None:
    with pytest.raises(InvalidEntry):
        encode(evidence(results=[[17, float("nan")]]))


@pytest.mark.parametrize(
    "value",
    [datetime.date(2026, 11, 12), Decimal("1.5"), b"\x00"],
    ids=["date", "decimal", "bytes"],
)
def test_encoding_rejects_a_value_that_skipped_validation(value: object) -> None:
    # model_copy doesn't validate, and the lists inside a frozen entry stay mutable
    copied = evidence().model_copy(update={"results": ([17, value],)})
    mutated = evidence()
    mutated.metadata["extra"] = value  # type: ignore[assignment]

    for entry in (copied, mutated):
        with pytest.raises(InvalidEntry):
            encode(entry)


def test_encoding_rejects_a_key_json_would_turn_into_a_string() -> None:
    entry = evidence()
    entry.metadata["by_id"] = {17: "settled"}  # type: ignore[dict-item]

    with pytest.raises(InvalidEntry):
        encode(entry)


def test_decoding_an_unknown_entry_type_is_invalid() -> None:
    with pytest.raises(InvalidEntry):
        decode("run_paused", "{}")


def test_decoding_a_value_this_version_does_not_know_is_invalid() -> None:
    body = '{"status": "interrupted", "reason": "", "spent": {}}'

    with pytest.raises(InvalidEntry):
        decode("run_finished", body)


def test_a_field_added_by_a_newer_version_is_ignored_when_reading() -> None:
    body = (
        '{"stage": "investigate", "tool": "replica_query", "request": "SELECT 1",'
        ' "results": [[1]], "evidence_id": "E4", "duration_ms": 120}'
    )

    decoded = decode("evidence_recorded", body)

    assert isinstance(decoded, EvidenceRecorded)
    assert decoded.evidence_id == "E4"


def test_a_field_added_inside_a_nested_value_is_ignored_when_reading() -> None:
    body = (
        '{"stage": "investigate", "gaps": [],'
        ' "facts": [{"claim": "Order 17 settled", "cites": ["E1"], "weight": 0.9}]}'
    )

    decoded = decode("findings_recorded", body)

    assert isinstance(decoded, FindingsRecorded)
    assert decoded.facts == (Fact(claim="Order 17 settled", cites=("E1",)),)


def test_an_unknown_field_is_still_refused_when_building_an_entry() -> None:
    with pytest.raises(ValidationError):
        evidence(duration_ms=120)
