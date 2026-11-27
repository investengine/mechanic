"""Facts and the evidence they cite: what every service's reply rests on."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# "E4" cites a whole piece of evidence, "E4/2" its second result. No zero, no
# leading zeros: one spelling per reference. Groups: the evidence ID, the result
EVIDENCE_REF_PATTERN = r"^(E[1-9][0-9]*)(?:/([1-9][0-9]*))?$"
EvidenceRef = Annotated[str, StringConstraints(pattern=EVIDENCE_REF_PATTERN)]


class Fact(BaseModel):
    """One claim and the evidence it rests on. Also the model's submit schema, so a
    malformed citation goes back to the model as a validation error."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim: str
    cites: tuple[EvidenceRef, ...] = Field(
        min_length=1,
        description='The evidence the claim rests on, whole or one result: "E4" or "E4/2".',
    )
    # When it happened, as the cited evidence shows it: "2026-11-12" or
    # "2026-11-12T10:05:00". Lets a reply lay dated facts out as a timeline
    when: str | None = None
