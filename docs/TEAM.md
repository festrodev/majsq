# How four people build one thing today

Four people, four AI-agent sessions, three repos, one afternoon. This is the
minimum that keeps the sessions from building four different products.

## Who owns what

| Person | Repo | Owns | Never touches |
|---|---|---|---|
| **Quan** | `majsq` | The brain, Festro access, the AG-UI stream, `docs/CONTRACT.md` | UI of any kind |
| **Manh** | `majsqweb` | `/`, `/chat`, CopilotKit wiring, the shared components | Ranking, Festro calls, `src/app/m/**` |
| **Selene** | `majsqbot` | Telegram behaviour, the login handoff, the real-group test | Ranking, Festro calls |
| **Jihoo** | `majsqweb` (map) + all three | `/m/[share_id]`, calendar links, and from 14:30 the whole submission | Manh's files: `/`, `/chat`, `src/app/api/**`, the shared components |
| **Ali** | Festro's private repos | The connect grant on festro.com, credentials, deploy | Surface code (unless asked) |

One owner per repo, except `majsqweb`, where two people work on **disjoint
directories**:

| Manh | Jihoo |
|---|---|
| `src/app/page.tsx`, `src/app/chat/**`, `src/app/api/**` | `src/app/m/[share_id]/**` |
| `src/components/{Chip,PickCard,QuestionBlock,ConsentToggle}.tsx` | `src/components/Map*.tsx` |
| `src/lib/turn.ts` | `src/lib/share.ts` |

`PickCard` is Manh's. Jihoo imports it and never edits it; if the map needs a
change to it, ask in the group chat. Both pull from `main` before every push.

You push to `main` of **your** repo directly today — there is no time for
review — except in `majsqweb`, where Manh pushes to `main` and Jihoo opens a
PR from `feat/map`. You open a PR for anyone else's repo.

## The three documents

Every session starts by reading, in this order:

1. [`docs/DESIGN.md`](DESIGN.md) — how it looks and sounds. Tokens, strings, emoji, components.
2. [`docs/CONTRACT.md`](CONTRACT.md) — the API between the agent and the surfaces. The only thing we must agree on.
3. This file.

Your agent session should quote these back to you before it writes code. If it
proposes a color, a string, a field or an endpoint that is not in them, the
answer is "add it to the doc first, in a PR to `majsq`".

## What goes wrong in parallel builds, and the rule for each

**Two surfaces invent two different chip lists.** → Chips come from
`GET /api/categories/` and `GET /api/slots/`. A surface renders what it is
sent. It has no list of its own.

**A surface starts calling Festro.** → Only the agent calls Festro. A surface
that needs a field asks for it in `CONTRACT.md`.

**Someone renames a field to make their side cleaner.** → Fields are added,
never renamed or removed, today. The agent owner is the only one who edits
`CONTRACT.md`.

**The strings drift ("Ouvrir la carte" here, "Voir sur la carte" there).** →
Canonical strings live in `DESIGN.md §1`. Copy them verbatim.

**Someone ships a photo of the event.** → Never. Event artwork is licensed to
Festro for its own pages. Picks are text and a link. This is in every doc
because it is the mistake an eager agent session makes first.

**The web renders a member's name next to a pick in a group.** → `why` comes
from the agent already aggregated. Render it as is.

**Someone needs the AG-UI stream and it is not there yet.** → It returns 501
on purpose. Build against `POST /api/turn/`, in a way that swapping in the
stream is a one-file change. The agent owner will tell you when it lands.

**Two people edit the same file.** → They cannot; the repos are separate. The
one shared file is `CONTRACT.md`, and only one person edits it.

## Definition of done, per repo, by 14:30

- **Agent:** `/agui/` streams; `OPENAI_API_KEY` set → the headline and the
  reasons are phrased by the model, unset → deterministic text; `pytest`
  passes; `Dockerfile` builds.
- **Web:** `/` welcome, `/chat` with chips → question → three PickCards, and
  `/m/[share_id]` with three markers. Both themes. Works with `FESTRO_MOCK=1`.
- **Bot:** In a real Telegram group on a real phone: welcome on add, silent
  until asked, question chips, three picks + poll + map button, consent
  toggle acknowledges. `Dockerfile` builds.
- **Jihoo:** `/m/[share_id]` renders three numbered markers and three
  PickCards from a real share id, on a phone, in both themes. Calendar links
  work. From 14:30: clean-clone check on all three repos, then the video,
  description and social post.
- **Ali:** `majsq` registered as a third-party application on Festro; the
  connect grant endpoints and the approve page exist; the credential works
  against `GET /api/v1/connect/profile/`.

## Timeline

| Until | |
|---|---|
| 13:30 | Each repo demo-able on its own with `FESTRO_MOCK=1`. |
| 14:00 | The three connected: bot → agent → web map link, live on a phone. |
| 14:30 | **Feature freeze.** Only fixes after this. |
| 14:30 | Jihoo starts the clean-clone check on all three repos. Any README that fails gets a PR now. |
| 15:00 | Video shot, description written, sponsor post drafted. |
| 15:45 | **Submit.** Do not wait for 16:00. |

## Git

- Branch names: `feat/<thing>` in your own repo; push to `main` when it runs.
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`).
- Never force-push. Never commit `.env`. The `.gitignore` already blocks it;
  do not "fix" the gitignore.
- If your agent session wants to install a dependency, it pins the version.

## When you are stuck

Post in the group chat with the repo name and the exact error. The person
whose repo it is answers. Do not work around it in your own repo — the
workaround is the thing that breaks the demo at 15:40.
