"""A case folded from its entries: what the citation check and the reply need."""

import re

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Self

from pydantic import JsonValue

from mechanic.service.case.events import CaseEvent, EvidenceRecorded, StoredEvent
from mechanic.service.case.facts import EVIDENCE_REF_PATTERN


_REF = re.compile(EVIDENCE_REF_PATTERN)


@dataclass(frozen=True)
class CitedResult:
    """One result of a piece of evidence, as "E4/2" cites it."""

    evidence_id: str
    index: int  # from 1
    value: JsonValue  # may be null: a result that is null is still a result


@dataclass(frozen=True)
class CaseFile:
    """Every piece of evidence in the case, from all of its runs, by ID."""

    evidence: Mapping[str, EvidenceRecorded]

    @classmethod
    def from_events(cls, entries: Iterable[StoredEvent[CaseEvent]]) -> Self:
        return cls(
            evidence={
                entry.event.evidence_id: entry.event
                for entry in entries
                if isinstance(entry.event, EvidenceRecorded)
                and entry.event.evidence_id is not None
            }
        )

    def resolve(self, ref: str) -> EvidenceRecorded | CitedResult | None:
        """The evidence "E4" names or the result "E4/2" names, or None when the case
        has no such thing."""
        match = _REF.fullmatch(ref)  # match() lets "$" pass a trailing newline
        if match is None:
            return None
        evidence_id, index = match.group(1), match.group(2)
        evidence = self.evidence.get(evidence_id)
        if evidence is None or index is None:
            return evidence
        n = int(index)
        if n > len(evidence.results):
            return None
        return CitedResult(evidence_id, n, evidence.results[n - 1])
