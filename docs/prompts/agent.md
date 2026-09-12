<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsq repo. -->

# Your part: the agent (`majsq`)

You own the brain. It already runs end to end offline. Your job is to make it
stream to the web, phrase with the model, and be deployable — in that order.

## What exists and works (verified with the Django test client)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py migrate
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py runserver
```

- `POST /api/turn/` — ask → question chips → tapped chip → three picks + poll + map share id. Reads the conversation first and never re-asks what was already said. Widens to the ranked feed when a category is empty and says so.
- `brain/reading.py` — regex extraction of constraints (window, band, category, area, budget, party size), and the `required()` / `optional()` question gates.
- `brain/categories.py` — categories as *definitions* (tags + keyword queries + venues). Read its docstring: only ~13% of live events carry a tag, so tag-only chips were dead on arrival.
- `brain/search.py` — runs a category's strategies against the catalog, merges, drops started events, applies the part-of-day band.
- `brain/ranking.py` — group score `0.7·mean + 0.3·min` over member affinities, one venue per pick, never the same title twice.
- `brain/engine.py` — one turn. Consent is checked live on every turn before any cached profile.
- `festro/client.py` — the only Festro caller. Images stripped, 60 s cache, identifying User-Agent.
- `festro/mock.py` + `fixtures/` — 110 real events re-dated onto the current week, quota per category.
- `api/` — the contract, with service-secret auth.
- `agui/` — **returns 501.** This is your first job.

## Build, in this order

### 1. The AG-UI stream (`POST /agui/`) — the web is waiting on this

CopilotKit's runtime in `majsqweb` will register this URL as a remote agent
(`HttpAgent` from `@ag-ui/client`). It POSTs an AG-UI `RunAgentInput` and
expects Server-Sent Events back.

Use the `ag-ui-protocol` package already in `requirements.txt`:
`from ag_ui.core import RunAgentInput, EventType, RunStartedEvent, TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent, StateSnapshotEvent, RunFinishedEvent, RunErrorEvent` and `from ag_ui.encoder import EventEncoder`.

Do it as a Django `StreamingHttpResponse` with `content_type="text/event-stream"`. Identity: the web session id arrives in `RunAgentInput.thread_id`
(the web sets it to the `majsq_session` cookie value); treat it as both
`conversation_id` and `participant_id` with `channel="web", kind="web"`. The
last user message in `RunAgentInput.messages` is `text`. If the web sends a
tapped chip it will be in `RunAgentInput.state["chosen"]`.

Then call **the same `brain.engine.respond`** the HTTP API calls — do not
write a second brain — and emit:

1. `RUN_STARTED`
2. `TEXT_MESSAGE_START/CONTENT/END` with `reply.text`
3. `STATE_SNAPSHOT` with exactly the shape in `CONTRACT.md §AG-UI` (same field names as `/api/turn/`, on purpose)
4. `RUN_FINISHED`

Require the service secret header exactly like `api/auth.py` does (`MAJSQ_OPEN_AGUI=1` skips it locally). Verify with:

```bash
curl -N -X POST localhost:8000/agui/ -H 'Content-Type: application/json' -H 'Accept: text/event-stream' \
  -d '{"threadId":"t1","runId":"r1","messages":[{"id":"m1","role":"user","content":"quoi faire ce soir?"}],"tools":[],"context":[],"state":{},"forwardedProps":{}}'
```

Tell the web owner the moment it streams. Remove the 501 note from `CONTRACT.md` in a `contract:` commit.

### 2. Model phrasing (OpenAI), with the deterministic path as the floor

`OPENAI_API_KEY` set → the model phrases `reply.text` and each pick's `why`,
given the picks and the constraints. **It does not choose the picks** — the
ranker did — and it must not add facts (no prices, no "sold out", no times
the catalog did not give). Unset key, or any error, or any output that names
an event not in the picks → the deterministic text ships. Use the Responses
API, `MAJSQ_MODEL` from settings, a 6-second timeout, one call per turn.
Keep the group rule: in a group the `why` is aggregate; pass the model only
the aggregate reasons, never member names.

### 3. `python manage.py check_categories --when tonight`

Prints the live count behind every chip for a window (uses
`brain.search.category_counts`). This is how Ali tunes `categories.py`.

### 4. Tests

`pytest` with `pytest-django` (pin them). Cover: `reading.extract` on the six
sentences in `brain/reading.py`'s own docstrings, `required()`/`optional()`,
`ranking.choose` never repeating a title, the consent-off-excludes-on-next-turn
rule, the share payload containing no `score`, and `403` without the secret.

### 5. `Dockerfile` + `gunicorn`

`python:3.12-slim`, `gunicorn majsq_agent.wsgi --bind 0.0.0.0:$PORT`,
`collectstatic` not needed. Build locally and run it with `FESTRO_MOCK=1`.

## Do not

- Do not add Postgres back today. SQLite is the decision.
- Do not touch `brain/categories.py`'s keyword lists — that is Ali's call.
- Do not put the model in the decision path. It phrases; the ranker decides.
