"""What a CaseLog raises. Every store raises these, so callers catch one set."""


class CaseLogError(Exception):
    pass


class RunSealed(CaseLogError):
    """An entry for a run that already has its RunFinished."""


class Duplicate(CaseLogError):
    """A MessageReceived whose origin_ref is already in the log: a redelivery."""


class InvalidEntry(CaseLogError):
    """An entry the log refuses to store: it doesn't encode to JSON or decode back,
    breaks the case's integrity, or claims something only the store assigns."""
