"""CaseLog in memory, for tests and local runs. Keeps each entry as JSON text, as
the PostgreSQL store does, so both accept and return exactly the same values."""

import asyncio
import logging

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from mechanic.service.case.errors import Duplicate, InvalidEntry, RunSealed
from mechanic.service.case.events import (
    CaseEvent,
    EvidenceRecorded,
    MessageReceived,
    RunFinished,
    StoredEvent,
    decode,
    encode,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Row:
    run_id: str
    seq: int
    at: datetime
    type_name: str
    body: str


class InMemoryCaseLog:
    def __init__(self) -> None:
        # One writer at a time. Nothing awaits inside it, so a number is chosen
        # and stored in one step and a rejected entry never takes one
        self._lock = asyncio.Lock()
        self._rows: dict[str, list[_Row]] = defaultdict(list)
        self._run_cases: dict[str, str] = {}
        self._sealed_runs: set[str] = set()
        self._origin_refs: set[str] = set()
        self._evidence_counts: dict[str, int] = defaultdict(int)

    async def append[
        E: CaseEvent
    ](self, case_id: str, run_id: str, event: E) -> StoredEvent[E]:
        async with self._lock:
            self._check(case_id, run_id, event)
            if isinstance(event, EvidenceRecorded):
                next_id = f"E{self._evidence_counts[case_id] + 1}"
                event = event.model_copy(update={"evidence_id": next_id})
            body = encode(event)
            # Same type_name, so decode gives back the type that came in
            stored = cast("E", decode(event.type_name, body))

            rows = self._rows[case_id]
            row = _Row(run_id, len(rows) + 1, datetime.now(UTC), event.type_name, body)
            rows.append(row)
            self._run_cases[run_id] = case_id
            if isinstance(event, MessageReceived):
                self._origin_refs.add(event.message.origin_ref)
            elif isinstance(event, RunFinished):
                self._sealed_runs.add(run_id)
            elif isinstance(event, EvidenceRecorded):
                self._evidence_counts[case_id] += 1
            return StoredEvent(case_id, run_id, row.seq, row.at, stored)

    async def read(self, case_id: str, after: int = 0) -> list[StoredEvent[CaseEvent]]:
        entries = []
        for row in self._rows.get(case_id, ()):
            if row.seq <= after:
                continue
            try:
                event = decode(row.type_name, row.body)
            except InvalidEntry as error:
                # Type, position and error type only: the cause's message echoes
                # the stored values
                cause = type(error.__cause__).__name__ if error.__cause__ else "unknown"
                logger.warning(
                    "Skipped a case log entry this version can't read: "
                    "type %s, seq %d, %s",
                    row.type_name,
                    row.seq,
                    cause,
                )
                continue
            entries.append(StoredEvent(case_id, row.run_id, row.seq, row.at, event))
        return entries

    def _check(self, case_id: str, run_id: str, event: CaseEvent) -> None:
        if isinstance(event, EvidenceRecorded) and event.evidence_id is not None:
            raise InvalidEntry("evidence IDs are assigned by the store")
        run_case = self._run_cases.get(run_id)
        if isinstance(event, MessageReceived):
            if event.message.case_id != case_id:
                raise InvalidEntry("the message belongs to another case")
            if run_case not in (None, case_id):
                raise InvalidEntry("the run belongs to another case")
        elif run_case != case_id:
            raise InvalidEntry("the run has no message received in this case")
        if run_id in self._sealed_runs:
            raise RunSealed(run_id)
        if (
            isinstance(event, MessageReceived)
            and event.message.origin_ref in self._origin_refs
        ):
            raise Duplicate(event.message.origin_ref)
