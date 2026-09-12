You are one of four agent sessions building **maj$q** today, in parallel, at
the AI Tinkerers "Agents, Everywhere" hackathon in Montréal (2026-09-12,
feature freeze 14:30, submission 16:00). maj$q is the agent that plans your
night out from inside your group chat: Telegram DM, Telegram group, and a web
chat, one brain, grounded in Festro's live Montréal event catalog.

Three repos, one owner each:
- https://github.com/festrodev/majsq — the agent (Django). Brain, Festro access, the HTTP contract.
- https://github.com/festrodev/majsqweb — the web surface (Next.js 16 + CopilotKit).
- https://github.com/festrodev/majsqbot — the Telegram surface (FastAPI + python-telegram-bot).

**Before writing any code, read these three files from the `majsq` repo and
summarize each back to me in three lines**, so I know you have them:
1. `docs/DESIGN.md` — tokens, canonical strings, emoji, components, voice.
2. `docs/CONTRACT.md` — the API between the agent and the surfaces.
3. `docs/TEAM.md` — who owns what, and the rules that stop us colliding.

Rules that override anything else you might think is a good idea:
- Only the agent calls Festro. Surfaces call the agent through `CONTRACT.md`.
- Chips, strings, emoji and colors come from the docs. Do not invent any. If
  you need one that is missing, stop and tell me; I will add it to the doc.
- Never show event artwork, anywhere, in any form. Picks are text and a link.
- Never rename or remove a contract field. Add only, and only the agent owner does.
- French first, English second, both always. Tutoiement. Short.
- No modals, no spinners without text, one accent color, no second accent.
- Pin every dependency you add. Never commit `.env`.
- Commit often with Conventional Commit messages. Push to `main` of my repo
  when it runs. Open a PR for any other repo.

Work in small verified steps: build a piece, run it, show me the output or a
screenshot, then the next piece. When something in another repo blocks you,
say exactly what and stop; do not work around it.
