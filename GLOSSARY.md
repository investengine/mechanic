# Glossary

The words Mechanic's shared code uses. Every service, whoever owns it, uses them with
these meanings. A service's own words (an investigation's "findings", a triage's
"severity") stay in that service's package and its own `GLOSSARY.md`; they never
appear in shared code.

Each entry says what the word means, where it lives in code, and which words not to
use instead.

## Platform

Every service has these, even one with no model and no evidence.

**Mechanic**:
InvestEngine's internal AI assistant: one repository and one deployment that many
services share.

**Service**:
One use case, such as answering #help-dev-en questions or triaging Sentry errors. In
code, a handler and its reply type, in its own package under `service/`.
_Avoid_: bot, agent, workflow

**Handler**:
The function a service gives the router: it takes a message and returns a reply.
_Avoid_: controller, processor

**Origin**:
Where a message came from, such as a Slack channel or the command line. The router
picks the handler by origin. `Message.origin`
_Avoid_: source (that word is for data sources), channel (outside the Slack adapter)

**Message**:
One request submitted by an adapter: its text, who sent it and where. `Message`
_Avoid_: request, enquiry, question

**Requester**:
The person who sent a message, as the adapter authenticated them; never taken from the
message text. `Message.requester`
_Avoid_: user, author

**Conversation**:
An adapter's own grouping of messages, such as a Slack thread, unique within its
origin. `Message.conversation_ref`
_Avoid_: thread (outside the Slack adapter)

**Adapter**:
What lets people reach Mechanic, such as the Slack listener or the command line. It
submits messages and shows replies; it never reads the case log.
_Avoid_: client, frontend, integration

**Case**:
Mechanic's record of one conversation, for any service: every run in it and what
each recorded. It is the unit that is kept, deleted 30 days after its last activity
and erased on request. Its ID is the origin and the conversation.
`StoredEvent.case_id`
_Avoid_: ticket, thread, session, investigation

**Run**:
One handler call for one message, from arrival to a run status. `StoredEvent.run_id`
_Avoid_: job, task, execution

**Run status**:
How a run ended, the same for every service: replied, timed out, failed or
cancelled. It never says what the reply concluded; that is the service's business.
`RunStatus`
_Avoid_: outcome, result

**Reply**:
What a handler returns, and what the requester sees once an adapter renders it. Each
service subclasses it with its own fields. `Reply`
_Avoid_: answer, response, result

**Spend**:
Model requests and their cost, for a stage or a run. `Spend`
_Avoid_: usage, cost (alone)

**Case log**:
The append-only record of every case: one entry per thing that happened, in order.
`CaseLog`
_Avoid_: history (that is the model history), journal, audit log

**Entry**:
One record in the case log, such as "run started" or "evidence recorded". Types and
fields are only ever added. `Entry`, stored as `StoredEvent`
_Avoid_: event (outside code names), record, row

**Sealed**:
A run whose "run finished" entry is written; the case log takes nothing more for it.
`RunSealed`

**Duplicate**:
A message whose source message is already in the case log: a redelivery, refused.
`Duplicate`

## Grounding

For services that use a model, call tools and must back what they say with evidence.
A service that does none of this ignores the section.

**Stage**:
One step in which a model works with tools towards a structured output, ending with a
submit that passes the stage's checks or with a stage status saying why not.
_Avoid_: phase, step, agent

**Stage status**:
How a stage ended: done, no submit, limit reached, gave up or refused.
`StageFinished.status`
_Avoid_: outcome

**Output**:
A stage's submit that passed its checks. The service owns its shape.
`StageFinished.output`
_Avoid_: result, findings (an investigation's word)

**Check**:
A plain function that returns the problems with a submitted output, which go back to
the model as a retry.
_Avoid_: validator, guard

**Tool**:
A function the model may call, such as a replica query.
_Avoid_: action, function call

**Evidence**:
The result of one successful data-tool call, recorded before anything reads it. Each
piece gets an ID in its case: E1, E2… `EvidenceRecorded`
_Avoid_: data, observation, source

**Result**:
One citable part of a piece of evidence: a row, a log line. "E4/2" is the second
result of E4. `EvidenceRecorded.results`
_Avoid_: row (outside the replica tool), item

**Fact**:
One claim and the evidence it cites. `Fact`
_Avoid_: finding, statement, assertion

**Citation**:
A fact's reference to evidence: "E4" for a whole piece, "E4/2" for one result.
`Fact.cites`
_Avoid_: source, link, reference (alone)

**Case file**:
A case's evidence by ID, read from the case log, to look citations up. `CaseFile`

**Citation check**:
The check that every citation names evidence the case holds. `check_citations`
_Avoid_: verification (model-based Verify is a different, later thing)

**Model history**:
What the model said and did during a stage, kept by the engine in its own format.
Not part of the case log.
_Avoid_: transcript, conversation, case log
