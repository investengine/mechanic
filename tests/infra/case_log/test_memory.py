"""What only the in-memory store can show: an entry a newer version wrote, put in
place directly since no current writer can produce one."""

import logging

from datetime import UTC, datetime

import pytest

from mechanic.infra.case_log.memory import InMemoryCaseLog, _Row
from tests.case_builders import case_id, evidence, open_run


CASE = case_id()


async def put_raw(log: InMemoryCaseLog, run: str, type_name: str, body: str) -> None:
    rows = log._rows[CASE]
    rows.append(_Row(run, len(rows) + 1, datetime.now(UTC), type_name, body))


@pytest.mark.parametrize(
    ("type_name", "body"),
    [
        ("run_paused", '{"note": "client 4417 asked to wait"}'),
        (
            "run_finished",
            '{"status": "paused for client 4417", "reason": "", "spent": {}}',
        ),
    ],
    ids=["unknown type", "unknown value"],
)
async def test_an_entry_this_version_cannot_read_is_skipped_without_its_values(
    caplog: pytest.LogCaptureFixture, type_name: str, body: str
) -> None:
    log = InMemoryCaseLog()
    run = await open_run(log)
    await put_raw(log, run, type_name, body)
    await log.append(CASE, run, evidence())

    with caplog.at_level(logging.WARNING):
        entries = await log.read(CASE)

    assert [e.seq for e in entries] == [1, 3]
    assert type_name in caplog.text
    assert "4417" not in caplog.text
