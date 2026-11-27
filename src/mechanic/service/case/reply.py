"""What every handler returns. A service subclasses Reply with its own fields, the
way a web handler returns its own Response subclass; generic code only reads the
fields declared here. Whether a reply settles the request (found, triaged, out of
scope) is the service's own field: it means something different per service."""

from pydantic import BaseModel, ConfigDict

from mechanic.service.case.facts import Fact


class Reply(BaseModel):
    """The base of every service's reply. A service that cites nothing leaves facts
    empty; any facts it has must cite evidence in the case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    facts: tuple[Fact, ...] = ()
