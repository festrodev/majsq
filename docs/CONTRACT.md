# The maj$q contract

The agent (this repo) owns every decision about **what** to recommend. The
surfaces — `majsqweb`, `majsqbot` — own **how** it is shown. This file is the
line between them. It is the only thing the four of us have to agree on, so:

- **Only the agent owner changes this file**, in a PR titled `contract: …`.
- A surface that needs something new asks for it here first, then builds
  against it. Do not invent a field on one side and hope.
- Fields are added, never renamed or removed, during the hackathon.

Base URL: `MAJSQ_AGENT_URL` (default `http://localhost:8000`).

---

## Authentication

Every `/api/` call except `shares` carries the service secret:

```
X-Majsq-Service-Secret: <MAJSQ_SERVICE_SECRET>
```

The callers are our own servers. **A browser never holds this.** The web
app's route handlers add it server-side. Missing or wrong → `403`.

For local development with no secret configured, set `MAJSQ_OPEN_AGUI=1` on
the agent and the check is skipped. Never in a deployed environment.

---

## Identity — the rule that matters most

A surface sends **which transport** and **which external ids**. The agent
resolves them to its own rows. A surface never sends an internal participant
id of its own choosing, and the agent never trusts a display name as identity.

| Surface | `channel` | `kind` | `conversation_id` | `participant_id` |
|---|---|---|---|---|
| Telegram DM | `telegram` | `dm` | Telegram chat id | Telegram user id |
| Telegram group | `telegram` | `group` | Telegram chat id (negative) | Telegram user id |
| Web | `web` | `web` | the `majsq_session` cookie value | the same cookie value |

Telegram ids come from the signed update, never from message text. The web
session id comes from an httpOnly cookie the Next.js server set, never from
the request body a browser could edit.

---

## `POST /api/turn/` — advance a conversation

The one call every surface makes.

**Request**

```json
{
  "channel": "telegram",
  "kind": "group",
  "conversation_id": "-1001234567890",
  "participant_id": "42",
  "display_name": "Ali",
  "locale": "fr",
  "title": "Les amis du jeudi",
  "text": "quoi faire ce soir?",
  "chosen": { "category": "theatre" }
}
```

- `text` — what the person wrote. May be empty when `chosen` is set.
- `chosen` — the answer to the previous question: one of
  `{"time_slot": "tonight"|"tomorrow"|"weekend"|"week"|"YYYY-MM-DD"}`,
  `{"band": "afternoon"|"evening"|"late"}`,
  `{"category": "<key>"}`, `{"area": "<label>"}`,
  `{"budget": "free"|"20"|"50"|""}`. An explicit tap always beats an
  inference from prose.
- `locale` — `fr` or `en`. Defaults to `fr`.

**Response** — exactly one of `question` or `picks` is meaningful.

```json
{
  "text": "Vous avez envie de quoi ?",
  "question": {
    "name": "category",
    "question": "Vous avez envie de quoi ?",
    "options": [
      { "value": "live", "label": "🎤 Concerts" },
      { "value": "nightlife", "label": "🪩 Sortir danser" }
    ]
  },
  "picks": [],
  "share_id": "",
  "map_url": "",
  "state": { "time_slot": "tonight", "band": "evening", "category": null, "area": null,
             "budget_max": null, "free_only": false, "party_size": null, "stated_tags": [] },
  "suggest_connect": false,
  "poll": null
}
```

or

```json
{
  "text": "3 idées pour du théâtre ce soir :",
  "question": null,
  "picks": [
    {
      "short_id": "r9e340uq",
      "title": "Lady Chatterley",
      "venue_name": "Les Grands Ballets Canadiens",
      "city": "Montreal",
      "latitude": 45.5089,
      "longitude": -73.5617,
      "start_datetime": "2026-09-12T23:30:00+00:00",
      "start_time_known": true,
      "end_datetime": "2026-09-13T02:00:00+00:00",
      "is_free": false,
      "tags": [],
      "organizer_name": "Les Grands Ballets",
      "url": "https://festro.com/e/r9e340uq",
      "why": "2 sur 3 aiment le jazz"
    }
  ],
  "share_id": "ZfsY_bQ5okciRtW2iZh5Tw",
  "map_url": "http://localhost:3000/m/ZfsY_bQ5okciRtW2iZh5Tw",
  "state": { "...": "as above" },
  "suggest_connect": true,
  "poll": { "question": "On fait lequel ?", "options": ["Lady Chatterley", "…", "…"] }
}
```

- `picks` has at most 3 entries and contains **public event fields only**.
  There is no image field and there never will be.
- `why` is already aggregate in a group and personal in a DM. Render it as
  is; do not add member names.
- `suggest_connect` is `true` at most once per 24 h per conversation. Render
  `nudge.connect` from DESIGN.md.
- `poll` is non-null only in a group. Render it as a native poll where the
  surface has one.
- `state` is what the agent understood. The web binds its chip pickers to it.

---

## `GET /api/slots/?locale=fr`

```json
{
  "slots": [ { "key": "tonight", "label": "Ce soir", "emoji": "🌙" }, "…" ],
  "bands": [ { "key": "evening", "label": "Soirée" }, "…" ]
}
```

## `GET /api/categories/?locale=fr&counts=1&time_slot=tonight&band=evening`

```json
{ "categories": [ { "key": "live", "label": "Concerts", "emoji": "🎤", "count": 3 }, "…" ] }
```

`count` is present only with `counts=1` (runs one catalog query per category,
a few seconds). **Hide a chip whose count is 0**, except `surprise`, which
never has a count. A chip that promises picks and returns none is worse than
no chip.

## `POST /api/consent/`

```json
{ "channel": "telegram", "kind": "group", "conversation_id": "-100…", "participant_id": "42",
  "display_name": "Ali", "use_my_taste": true }
```
→ `{ "use_my_taste": true }`

Persistent, reversible, per conversation. The agent reads it on every turn
before touching any cached profile, so switching it off takes effect on the
next message.

## `GET /api/shares/<share_id>/` — no secret

```json
{ "share_id": "…", "time_slot": "tonight", "category": "theatre",
  "picks": [ "…same shape as turn picks…" ], "created_at": "…" }
```

The unguessable id is the credential. The payload is public event fields
only. The web's `/m/[share_id]` page calls this directly.

## `GET /healthz`

`{ "ok": true, "service": "majsq-agent" }`

---

## `POST /agui/` — AG-UI stream for CopilotKit

Status: **implemented.** The web registers this URL as a remote AG-UI agent
and gets the same conversation engine and state shape as `/api/turn/`.

### What the agent reads out of `RunAgentInput`

This is the input half of the contract, and it is one-sided by nature — the
web is the only caller — which is exactly why it belongs here. A chip tap that
silently does nothing over AG-UI is a failure nobody notices until a demo.

| Agent uses | From | Notes |
|---|---|---|
| `conversation_id` and `participant_id` | `thread_id` | The web sets it to the `majsq_session` cookie value. Both fields, same value: on the web the conversation and the person are the same session. |
| `text` | the last `user` message in `messages` | |
| `chosen` | `state.chosen` | A tapped chip, same shape as `/api/turn/`'s `chosen`. Send `{"category": "theatre"}`, not a synthetic user message. |
| `channel` / `kind` | fixed `web` / `web` | Not read from the request. |
| `locale` | fixed `fr` today | The web cannot yet select a locale over AG-UI; use `/api/turn/` if you need `en`. |

It accepts AG-UI `RunAgentInput` and streams SSE events
(`RUN_STARTED`, `TEXT_MESSAGE_*`, `TOOL_CALL_*`, `STATE_SNAPSHOT`,
`RUN_FINISHED`). The shared state snapshot will be:

```json
{
  "time_slot": "tonight", "band": null, "category": "theatre",
  "constraints": { "area": null, "budget_max": null, "free_only": false, "party_size": null },
  "question": { "…same shape as turn.question…" },
  "picks": [ "…same shape as turn.picks…" ],
  "share_id": "…", "map_url": "…", "suggest_connect": false
}
```

Same field names as `/api/turn/` on purpose, so the web's components render
either.

---

## Environment variables

Names are fixed across repos. Copy from each repo's `.env.example`.

| Variable | Where | Meaning |
|---|---|---|
| `MAJSQ_AGENT_URL` | web, bot | The agent's base URL |
| `MAJSQ_SERVICE_SECRET` | agent, web, bot | Shared service secret, identical in all three |
| `MAJSQ_WEB_URL` | agent, bot | Public web URL, for map links |
| `MAJSQ_OPEN_AGUI` | agent | `1` skips the secret check locally |
| `FESTRO_MOCK` | agent | `1` serves the fixture catalog offline |
| `OPENAI_API_KEY` | agent, web | Model key; agent for phrasing, web for the CopilotKit runtime |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_WEBHOOK_SECRET` / `TELEGRAM_BOT_USERNAME` | bot | From BotFather |

---

## Festro, for reference

The agent is the only thing that talks to Festro, and only reads:

- `GET https://api.festro.com/api/v1/events/` — anonymous, 60 req/min/IP,
  filters `when` (`today`|`weekend`|`next-weekend`|`YYYY-MM-DD`|`a..b`),
  `q`, `tags` (verbatim label, e.g. `Hip Hop`), `price=free`, `market`.
- `GET /api/v1/tags/`
- `GET /api/v1/connect/profile/` — with a member's opaque connect credential.
  **Built and merged-pending on Festro's side** (festro#574). Returns aggregate
  preference only: weighted tags, organizers and venues, a price band, usual
  nights, and three counts. No email, no event rows, no reservations.
  `FESTRO_MOCK=1` still returns a fixture profile so the personalization path
  is demonstrable without credentials.

### Connecting a member's Festro account

The credential maj$q holds is **not** a Festro user token — it is accepted by
the profile endpoint alone and can do nothing else. Getting one:

1. The surface sends the member to
   `https://festro.com/connect/authorize?client_id=fc_majsq&redirect_uri=…&state=…&code_challenge=…`
   (PKCE S256; `state` and the verifier are held server-side, bound to the
   session or the verified Telegram id).
2. Festro redirects back to the registered callback with `?code&state`.
3. The surface posts the code to the agent, which exchanges it using maj$q's
   own client secret and stores the credential against the participant.

Agent endpoint for step 3 — **to be added by the agent owner**:

```
POST /api/link/
{ "channel": "telegram"|"web", "kind": "dm"|"group"|"web",
  "conversation_id": "…", "participant_id": "…",
  "code": "fcg_…", "code_verifier": "…", "redirect_uri": "…" }
→ { "connected": true, "display_name": "…" }
```

Registered redirect URIs today: `https://majsq.festro.com/connect/callback`
and `http://localhost:3000/connect/callback`. Ali holds
`FESTRO_CLIENT_ID` / `FESTRO_CLIENT_SECRET`; ask him privately, never commit them.

Surfaces never call Festro. If you find yourself adding `api.festro.com` to
a surface, stop and ask for the field in this file instead.
