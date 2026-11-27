"""Entries for tests, with realistic defaults. Case IDs follow the Slack adapter's
shape: origin, then channel and thread ts."""

from decimal import Decimal
from uuid import uuid4

from pydantic import JsonValue

from mechanic.service.case.events import (
    EvidenceRecorded,
    FindingsRecorded,
    Message,
    MessageReceived,
    RunFinished,
    RunStarted,
    RunStatus,
    Spend,
)
from mechanic.service.case.facts import Fact
from mechanic.service.case.ports import CaseLog


ORIGIN = "slack:help-dev-en"


def case_id(thread: str = "C1/100.1") -> str:
    return f"{ORIGIN}/{thread}"


def received(thread: str = "C1/100.1", ts: str | None = None) -> MessageReceived:
    channel = thread.split("/")[0]
    return MessageReceived(
        message=Message(
            origin=ORIGIN,
            origin_ref=f"{channel}/{ts or uuid4().hex}",
            conversation_ref=thread,
            requester="slack:U012AB3CD",
            text="Why did order 17 not settle?",
        )
    )


def started() -> RunStarted:
    return RunStarted(
        service="investigation",
        version="dev",
        models={"investigate": "model-a", "report": "model-b"},
    )


def finished(status: RunStatus = RunStatus.CONCLUDED) -> RunFinished:
    return RunFinished(
        status=status,
        reason="",
        spent=Spend(model_requests=3, cost_usd=Decimal("0.02")),
    )


def evidence(*rows: list[JsonValue]) -> EvidenceRecorded:
    return EvidenceRecorded(
        stage="investigate",
        tool="replica_query",
        request="SELECT id, status FROM orders WHERE id = 17 LIMIT 200",
        results=tuple(rows) or ([17, "settled"],),
        metadata={"columns": ["id", "status"], "truncated": False},
    )


def findings(*facts: Fact) -> FindingsRecorded:
    return FindingsRecorded(stage="investigate", facts=facts, gaps=())


async def open_run(log: CaseLog, thread: str = "C1/100.1") -> str:
    """A run with its message received, as the dispatcher starts one. Returns its ID."""
    run_id = uuid4().hex
    await log.append(case_id(thread), run_id, received(thread))
    return run_id
