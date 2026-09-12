# maj$q

**The agent that plans your night out, from inside your group chat.**

Deciding what to do tonight doesn't happen in an events app. It happens in a
group chat, in a ninety-second burst, and usually dies at "idk, you pick".
maj$q goes where that decision is made: add it to a Telegram group, say
"quoi faire ce soir?", and it comes back with three real events happening
tonight, a poll to settle it, and a map.

Built at the [AI Tinkerers "Agents, Everywhere" hackathon](https://montreal.aitinkerers.org/p/agents-everywhere-bots-channels-more-global-hackathon),
Montréal, 12 September 2026.

> **Agents, everywhere.** The same agent runs in three places — a Telegram
> group, a Telegram DM, and a web chat — with one brain and one set of tools.
> Each surface renders the same three steps in its own vocabulary: inline
> keyboards in Telegram, generative UI in the browser.

---

## How it works

```
  Telegram group  ─┐
  Telegram DM     ─┼─►  majsq-agent (Django)  ─►  Festro public catalog
  Web chat        ─┘         │                    live Montréal events
   (CopilotKit)              │
                             └─►  OpenAI  (tools: search, ask, rank)
```

**The flow**, same in every surface:

1. **When?** Tonight · Tomorrow · This weekend · This week, then optionally a
   part of day. Nothing downstream is a valid catalog query without a window.
2. **What kind?** Concerts, nightlife, theatre, dance, classical, comedy,
   festivals, free — or "surprise me".
3. **The agent reads the chat.** Constraints already stated in the
   conversation — budget, neighbourhood, how many people — are never asked
   again. It asks at most one more question, as tappable chips.
4. **Three picks**, each with the venue, the time, the price and a link to
   Festro. A poll to choose between them, and one button to open all three on
   a map.

Members who connect their Festro account get picks weighted by their own
history. That is opt-in per group, reversible, and group-facing reasons stay
aggregate: "2 sur 3 aiment le jazz", never "Sam booked X last month".

---

## The three repos

| Repo | What it is | Owner |
|---|---|---|
| **`majsq`** (this one) | The agent. Django: the brain, the conversation store, the only Festro caller, the HTTP contract, the AG-UI stream. | Agent |
| [`majsqweb`](https://github.com/festrodev/majsqweb) | The web surface. Next.js 16 + CopilotKit. Welcome, chat, the map share page. | Web |
| [`majsqbot`](https://github.com/festrodev/majsqbot) | The Telegram surface. FastAPI webhook + python-telegram-bot. | Bot |

The agent owns every decision about *what* to recommend. The two surfaces own
*how* it is shown, and talk to the agent only through
[`docs/CONTRACT.md`](docs/CONTRACT.md). Neither surface holds a model key or
calls Festro.

**In this repo**

| Path | What it is |
|---|---|
| `brain/` | Reading the chat, categories, time slots, search, ranking, the turn engine. |
| `festro/` | The catalog client and the offline mock. |
| `api/` | The HTTP contract the surfaces call. |
| `agui/` | The AG-UI stream for CopilotKit (returns 501 until it lands). |
| `core/` | Models: conversations, participants, per-group consent, links, pick sets. |
| `fixtures/` | 110 real Montréal events and the tag taxonomy, captured 2026-09-12, image fields removed. Used when `FESTRO_MOCK=1`. |
| `docs/` | Design system, contract, team rules, session prompts. |

---

## Run it

Python 3.12+. **No API keys are required** for a first run: `FESTRO_MOCK=1`
serves the bundled catalog and the agent falls back to deterministic phrasing
when there is no model key.

```bash
git clone https://github.com/festrodev/majsq.git
cd majsq
cp .env.example .env        # works as-is for the offline demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py migrate
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py runserver
```

Then, in a second terminal, one full conversation from the command line:

```bash
curl -s localhost:8000/api/turn/ -H 'Content-Type: application/json' -d '{"channel":"telegram","kind":"group","conversation_id":"-1","participant_id":"1","display_name":"Ali","locale":"fr","text":"quoi faire ce soir?"}'
curl -s localhost:8000/api/turn/ -H 'Content-Type: application/json' -d '{"channel":"telegram","kind":"group","conversation_id":"-1","participant_id":"1","locale":"fr","text":"","chosen":{"category":"theatre"}}'
```

The first answers with category chips; the second with three picks, a poll,
and a map share link. The web and Telegram surfaces are separate repos — see
the table above.

---

## About the Festro API

maj$q is built on [Festro](https://festro.com), a live events platform for
Montréal. It uses three **read-only** endpoints:

| Endpoint | What it gives |
|---|---|
| `GET /api/v1/events/` | The public catalog. Anonymous. Filters: `when`, `days`, `q`, `tags`, `price`, `market`. |
| `GET /api/v1/tags/` | The tag taxonomy behind the category chips. |
| `GET /api/v1/connect/profile/` | One member's minimized taste profile, with their own opaque connect credential. |

**If you fork this**, please: keep the `User-Agent` that identifies your build,
stay inside the 60 requests/minute anonymous rate limit, don't bulk-scrape or
mirror the catalog, and link back to festro.com for the event itself. Event
artwork is licensed to Festro for its own pages and is deliberately never
re-hosted here — maj$q sends text and links. The API may change without notice.

Run with `FESTRO_MOCK=1` while you are developing and you won't touch it at all.

---

## Building on this, in parallel

Four people, four agent sessions, one afternoon. Read these first, in order:

| Doc | What it settles |
|---|---|
| [`docs/DESIGN.md`](docs/DESIGN.md) | How it looks and sounds: tokens, canonical strings, emoji, the five components, voice. |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | The API between the agent and the surfaces. The only thing to agree on. |
| [`docs/TEAM.md`](docs/TEAM.md) | Who owns which repo, and the rules that stop parallel builds colliding. |
| [`docs/prompts/`](docs/prompts/) | One ready-to-paste prompt per person, for their own agent session. |

## Design notes

Two decisions are worth reading before you change anything:

- **Categories are not tags.** Tag coverage on any real event feed is uneven,
  and the vocabulary is narrower than the catalog. So a category is a
  *definition* — tags plus keyword queries plus venues — merged across several
  catalog calls. See [`brain/categories.py`](brain/categories.py).
- **A connected account is not an access token.** maj$q never holds a Festro
  session credential. It holds an opaque credential accepted by exactly one
  endpoint, which carries no authority over the account at all. See
  [`docs/connect.md`](docs/connect.md).

---

## Built with

OpenAI · [CopilotKit](https://copilotkit.ai) + [AG-UI](https://ag-ui.com) ·
Next.js · Django · MapLibre · Telegram Bot API · [Festro](https://festro.com)

MIT licensed.
