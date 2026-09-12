<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsqbot repo. -->

# Your part: the Telegram surface (`majsqbot`)

You own how maj$q behaves in Telegram. The bot is written and runnable; your
job is to prove it in a **real group on a real phone**, then harden it, then
build the Festro-connect handoff so it is ready when Ali's side lands.

## What exists

- `majsq_bot/app.py` — FastAPI webhook. Refuses updates without the secret header Telegram echoes; de-duplicates `update_id` so a Telegram retry cannot post a second set of picks.
- `majsq_bot/handlers.py` — `/start`, messages, callback queries. In a group: silent unless mentioned, replied to, or asked ("quoi faire", "ce soir", "what should we do").
- `majsq_bot/render.py` — replies → one message + inline keyboard, questions → chips two per row, native poll. Honours `start_time_known`. Never `sendPhoto`.
- `majsq_bot/agent.py` — the only module that knows the agent exists.
- `scripts_set_webhook.sh` — points Telegram at a public URL.

## Build, in this order

### 1. Run it against the agent, offline

```bash
# in a clone of majsq
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py migrate && FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py runserver
# here
cp .env.example .env && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn majsq_bot.app:app --reload --port 8080
```

Create a bot with @BotFather. **`/setprivacy` → Disable** — without it the bot
cannot read group messages and nothing works in a group. Put the token, a
random `TELEGRAM_WEBHOOK_SECRET`, and `TELEGRAM_BOT_USERNAME` in `.env`.
Expose port 8080 (`cloudflared tunnel --url http://localhost:8080` or ngrok)
and run `./scripts_set_webhook.sh https://<tunnel>`.

### 2. The real-group test — this is the demo, do it first

Make a Telegram group with two phones. Add the bot. Walk this exact script and
fix whatever breaks:

1. Bot added → welcome message (HTML renders, no raw tags).
2. Someone writes "salut ça va" → **bot says nothing**.
3. Someone writes "quoi faire ce soir ?" → category chips, two per row.
4. Tap 🎭 Théâtre → one message, three picks, bold titles, meta lines, a `🗺 Ouvrir sur la carte` button, a `🙋 Utiliser mes goûts ici` button, then a native poll.
5. Tap 🙋 → "✅ Tes goûts comptent dans ce groupe." Tap again → it should turn **off** (see step 3 below — today it only turns on).
6. Tap the map button → opens the web map (the web owner's page; if it is not up yet, the URL is still correct).
7. Reply to the bot's message with "et demain ?" → it answers (reply-to counts as addressed).
8. Two people vote in the poll.

Send me screenshots of each step.

### 3. Consent toggle, both directions

`render.py` always sends `consent:on`. Make the button reflect state: the
agent's `POST /api/consent/` returns the new value; after a tap, edit the
original message's keyboard (`edit_message_reply_markup`) so the button reads
`btn.consent.off` when on and vice versa. Labels verbatim from `DESIGN.md`.

### 4. Edge cases that break demos

- A message that is only `@botname` with nothing else → treat as "quoi faire ce soir ?".
- A group of 200 people where two people ask within 5 seconds → one answer, not two (debounce per chat, 8 s).
- Telegram sends `edited_message` → ignore.
- The agent is down → the `error.agent` string, once, not on every message.
- A pick title with `<` or `&` → still renders (escaping is in `render.py`; confirm).
- `/start` in a group by a member → the group welcome, not the DM one.

### 5. The Festro-connect handoff (build it now, it lights up when Ali's side lands)

In a DM, the welcome gets an inline keyboard: `btn.connect` and `btn.guest`.
`btn.connect` is a `login_url` button (`LoginUrl(url=f"{MAJSQ_WEB_URL}/tg/login", request_write_access=True)`).
Telegram will only show it after Ali runs `/setdomain` in BotFather with the
web domain; until then, fall back to a plain URL button to
`{MAJSQ_WEB_URL}/connect?tg={signed}` where `signed` is a 10-minute HMAC nonce
over the Telegram user id using `TELEGRAM_WEBHOOK_SECRET`. Add `agent.py`
support for `POST /api/link/` if the agent owner adds it to the contract;
otherwise leave a clear TODO with the payload you would send.

### 6. `Dockerfile`

`python:3.12-slim`, `uvicorn majsq_bot.app:app --host 0.0.0.0 --port $PORT`.
Build and run it locally against the tunnel.

## Do not

- Never `sendPhoto` or `sendMediaGroup`. Picks are text and a link.
- No ranking, no Festro calls, no chip list of your own in this repo.
- Do not widen the intent regex casually. A false positive is a bot barging into a conversation; test any change against "salut ça va", "on se voit à 8", "t'es où".
