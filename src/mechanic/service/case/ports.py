"""The case log port. Implementations live in infra; every one passes the contract
tests in tests/infra/case_log."""

from typing import Protocol

from mechanic.service.case.events import CaseEvent, StoredEvent


class CaseLog(Protocol):
    """Append-only store of case entries. Writers are the dispatcher (message
    received, run started, replied, run finished) and the stage runner (evidence,
    stage finished)."""

    async def append[
        E: CaseEvent
    ](self, case_id: str, run_id: str, event: E) -> StoredEvent[E]:
        """Store the entry and return it as read() would. Numbers it within the case
        and gives evidence its ID: E1, E2... per case, across runs.

        Raises RunSealed after the run's RunFinished, Duplicate for a MessageReceived
        whose origin_ref is already stored, InvalidEntry for an entry that doesn't
        encode, an evidence entry that brings its own ID, a MessageReceived filed
        under another case, or an entry for a run with no MessageReceived in this
        case. A rejected entry takes no number."""
        ...

    async def read(self, case_id: str, after: int = 0) -> list[StoredEvent[CaseEvent]]:
        """The case's entries after seq `after`, in order. Skips, with a warning,
        any entry this version can't decode."""
        ...
