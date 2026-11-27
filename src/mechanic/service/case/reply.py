"""What every handler returns. A service subclasses Reply with its own fields, the
way a web handler returns its own Response subclass; generic code only reads the
fields declared here."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from mechanic.service.case.facts import Fact


class Outcome(StrEnum):
    """How a handler's run ended. RunFinished takes its status from this."""

    CONCLUDED = "concluded"  # reached a conclusion grounded in evidence
    INCONCLUSIVE = "inconclusive"  # looked, couldn't establish enough
    DECLINED = "declined"  # out of this service's scope


class Reply(BaseModel):
    """The base of every service's reply. A bot that cites nothing leaves facts
    empty; any facts it has must cite evidence in the case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: Outcome
    facts: tuple[Fact, ...] = ()
