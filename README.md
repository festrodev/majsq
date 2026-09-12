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
  Web chat        ─┘         │                    3,400+ live Montréal events
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

## Repo layout

| Path | What it is |
|---|---|
| `agent/` | Django. The brain, the conversation store, and both transports: an AG-UI SSE endpoint for the web and a Telegram webhook. |
| `web/` | Next.js 16 + CopilotKit. Welcome, chat, and the map share page. |
| `fixtures/` | 60 real Montréal events and the tag taxonomy, captured 2026-09-12. Used when `FESTRO_MOCK=1`. |
| `docs/` | Design notes. |

Three logical apps, **two deployed services** — the Telegram bot is a package
inside the agent, not a third thing to keep alive.

---

## Run it

You need Python 3.12+ and Node 20+. **No API keys are required** for a first
run: `FESTRO_MOCK=1` serves the bundled catalog and the agent falls back to a
deterministic composer when there is no model key.

```bash
git clone https://github.com/festrodev/majsq.git
cd majsq
cp .env.example .env        # works as-is for the offline demo
```

**The agent:**

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
FESTRO_MOCK=1 python manage.py migrate
FESTRO_MOCK=1 python manage.py runserver
```

**The web app**, in a second terminal:

```bash
cd web
npm install
npm run dev            # http://localhost:3000
```

**Telegram**, optional: create a bot with [@BotFather](https://t.me/botfather),
turn **privacy mode off** so it can read group messages, put the token in
`.env`, then point Telegram at your webhook (use a tunnel in development):

```bash
curl -F "url=https://<your-tunnel>/tg/webhook/" -F "secret_token=$TELEGRAM_WEBHOOK_SECRET" \
  "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook"
```

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

## Design notes

Two decisions are worth reading before you change anything:

- **Categories are not tags.** Only ~13% of live events carry a tag, and the
  taxonomy is almost entirely music genre. A category is a *definition* —
  tags plus keyword queries plus venues — merged across several catalog calls.
  See [`agent/brain/categories.py`](agent/brain/categories.py).
- **A connected account is not an access token.** maj$q never holds a Festro
  user token. It holds an opaque credential that is accepted by exactly one
  endpoint and carries no account authority. See [`docs/connect.md`](docs/connect.md).

---

## Built with

OpenAI · [CopilotKit](https://copilotkit.ai) + [AG-UI](https://ag-ui.com) ·
Next.js · Django · MapLibre · Telegram Bot API · [Festro](https://festro.com)

MIT licensed.
