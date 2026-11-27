"""The case log's entries. Each is stored as JSON under its type_name; the case and
run it belongs to live on the StoredEvent, never inside the entry."""

import json

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Self, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from mechanic.service.case.errors import InvalidEntry
from mechanic.service.case.facts import Fact
from mechanic.service.case.reply import Reply


class Entry(BaseModel):
    """Every entry type. Types and fields are only ever added, and new fields get
    defaults, so entries written earlier still decode."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type_name: ClassVar[str]


class Message(BaseModel):
    """What an adapter submits."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: str  # where it came from, and the route key: "slack:help-dev-en", "cli"
    # Unique per message, such as the Slack channel and ts: a redelivery is a Duplicate
    origin_ref: str
    conversation_ref: str  # unique within the origin, such as a Slack thread
    requester: str  # an ID from the adapter's authentication, never from the text
    text: str
    metadata: dict[str, JsonValue] = {}  # what only the adapter knows

    @property
    def case_id(self) -> str:
        """One case per conversation."""
        return f"{self.origin}/{self.conversation_ref}"


class Spend(BaseModel):
    """Model requests and their cost, for a stage or a whole run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_requests: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal(0), ge=0)


class RunStatus(StrEnum):
    """How a run ended, the same for every service. What the reply says is the
    service's business, in its own Reply subclass."""

    REPLIED = "replied"  # the handler returned a reply
    TIMED_OUT = "timed_out"
    FAILED = "failed"  # the handler raised, or the run was stopped by a deploy
    CANCELLED = "cancelled"


class MessageReceived(Entry):
    """Written by the dispatcher when a message arrives, under the run it starts."""

    type_name = "message_received"

    message: Message


class RunStarted(Entry):
    """Written by the dispatcher when the run gets a slot. Says what ran it."""

    type_name = "run_started"

    service: str  # the handler's service name
    version: str  # image tag or git SHA
    models: dict[str, str] = {}  # stage -> model ID; empty for a service with none
    config: dict[str, JsonValue] = {}  # limits and anything else worth knowing


class RunFinished(Entry):
    """Written by the dispatcher, last. Seals the run: the log takes nothing more
    for it. A run closed before it started has spent nothing."""

    type_name = "run_finished"

    status: RunStatus
    reason: str  # for a failure: the error type and a fixed hint, never its message
    spent: Spend


class EvidenceRecorded(Entry):
    """One successful data-tool call, written before anything reads the result.
    Facts cite it as "E4", or one of its results as "E4/2"."""

    type_name = "evidence_recorded"

    stage: str | None = None  # the stage that called the tool, if any
    tool: str  # "replica_query"
    request: str  # what ran, as text: the SQL, a log query
    results: tuple[JsonValue, ...]  # "E4/n" is results[n - 1]: a row, a log line
    metadata: dict[str, JsonValue] = {}  # the tool's, not citable: columns, truncated
    call_ref: str | None = None  # the engine's ID for the call, to find it in history
    # Assigned by the store on append: E1, E2... per case. Writers leave it out
    evidence_id: str | None = None


class StageFinished(Entry):
    """Written by the stage runner for every stage that returns a status. A
    cancelled or failed stage writes none: RunFinished says how the run ended."""

    type_name = "stage_finished"

    stage: str
    status: str  # done, no_submit, usage_limit, gave_up, refused: the runner's list
    spent: Spend
    # The submit that passed the stage's checks, as JSON the service reads back
    # with the stage's output model. None unless the stage is done
    output: dict[str, JsonValue] | None = None
    facts: tuple[Fact, ...] = ()  # the output's facts, typed for the citation check
    metadata: dict[str, JsonValue] = {}


class Replied(Entry):
    """Written by the dispatcher for every run whose handler returned a reply. The
    facts are typed for the citation check; the whole reply is kept as JSON, which
    the service reads back with its own Reply subclass."""

    type_name = "replied"

    reply_type: str  # the Reply subclass's name, to pick the model that reads it
    facts: tuple[Fact, ...] = ()
    reply: dict[str, JsonValue]

    @classmethod
    def of(cls, reply: Reply) -> Self:
        # Dumped from the reply itself: a field typed as Reply would serialise as
        # the base class and drop the subclass's fields
        return cls(
            reply_type=type(reply).__name__,
            facts=reply.facts,
            reply=reply.model_dump(mode="json"),
        )


type CaseEvent = (
    MessageReceived
    | RunStarted
    | RunFinished
    | EvidenceRecorded
    | StageFinished
    | Replied
)


@dataclass(frozen=True)
class StoredEvent[E: CaseEvent]:
    """An entry as the log stores and returns it. append() keeps the entry's type,
    so a writer reads back fields such as the evidence ID without narrowing."""

    case_id: str
    run_id: str
    seq: int  # per case, from 1, no gaps
    at: datetime  # UTC, set by the store
    event: E


_ENTRY_TYPES: dict[str, type[Entry]] = {
    cls.type_name: cls
    for cls in (
        MessageReceived,
        RunStarted,
        RunFinished,
        EvidenceRecorded,
        StageFinished,
        Replied,
    )
}


def encode(event: CaseEvent) -> str:
    """The entry as JSON text, which every store keeps as is. Raises InvalidEntry for a
    value JSON can't hold, such as NaN, a date or a non-string key: dumping in JSON
    mode would quietly turn those into strings."""
    try:
        # Validated again: model_copy(update=...) skips validation, and the lists
        # and dicts inside a frozen entry can still be changed after it's built
        # warnings=False: pydantic's serializer warnings quote the offending value
        checked = type(event).model_validate(event.model_dump(warnings=False))
        return json.dumps(checked.model_dump(mode="json"), allow_nan=False)
    except (ValidationError, ValueError) as error:
        raise InvalidEntry(f"{event.type_name} doesn't encode to JSON") from error


def decode(type_name: str, body: str) -> CaseEvent:
    """Raises InvalidEntry for a type or a value this version doesn't know, such as an
    entry written by a newer version before a rollback. A field it doesn't know is
    dropped instead: fields are only ever added, so the rest of the entry still
    means what it meant."""
    entry_type = _ENTRY_TYPES.get(type_name)
    if entry_type is None:
        raise InvalidEntry(f"unknown entry type {type_name}")
    try:
        # extra="ignore" only here: building an entry still refuses unknown fields
        return cast("CaseEvent", entry_type.model_validate_json(body, extra="ignore"))
    except ValidationError as error:
        # The error type only: pydantic's message echoes the input values
        raise InvalidEntry(f"{type_name} doesn't decode") from error
