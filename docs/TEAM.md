# How four people build one thing today

Four people, four AI-agent sessions, three repos, one afternoon. This is the
minimum that keeps the sessions from building four different products.

## Who owns what

| Person | Repo | Owns | Never touches |
|---|---|---|---|
| **Selene** | `majsq` | The brain, Festro access, the AG-UI stream, `docs/CONTRACT.md` | UI of any kind |
| **Manh** | `majsqweb` | Every page and every wired component: `/`, `/chat`, `/m/[share_id]`, the proxy routes, CopilotKit | Ranking, Festro calls, Jihoo's design files |
| **Quan** | `majsqbot` | Telegram behaviour, the login handoff, the real-group test | Ranking, Festro calls |
| **Jihoo** | design, across all three | Tokens, the five visual primitives, the screen layouts, the words, and from 14:30 the submission | Manh's pages and logic, the agent, the bot's code |
| **Ali** | Festro's private repos | The connect grant on festro.com, credentials, deploy | Surface code (unless asked) |

Manh and Jihoo share `majsqweb`. **Design and code are split by file**, so
neither ever waits on the other:

| Jihoo — how it looks | Manh — what it does |
|---|---|
| `src/app/globals.css` (all tokens) | `src/app/page.tsx`, `chat/**`, `m/**` |
| `src/app/dev/**` (token + component galleries) | `src/app/api/**` |
| `src/components/ui/**` (visual primitives) | `src/components/*.tsx` (wired components) |
| `public/**` (favicon, OG image) | `src/lib/**` |
| `majsq/docs/DESIGN.md` | |

The handoff is `/dev/components`, not a conversation: Jihoo renders every
component in every state there, and Manh builds against it. If Manh needs a
look that does not exist yet, they build the plainest version against the
tokens and swap it later — nobody blocks on design.

**Nobody writes a hex value in a component.** Tokens only. That single rule is
what lets two people work on the same screen without it looking like two
screens.

You push to `main` of **your** repo directly today — there is no time for
review — except in `majsqweb`, where Manh pushes to `main` and Jihoo opens a
PR from `design/<thing>`. You open a PR for anyone else's repo.

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

- **Selene (agent):** `/agui/` streams; `OPENAI_API_KEY` set → the headline and the
  reasons are phrased by the model, unset → deterministic text; `pytest`
  passes; `Dockerfile` builds.
- **Manh:** `/` welcome, `/chat` with chips → question → three PickCards, and
  `/m/[share_id]` with three markers on a phone. Works with `FESTRO_MOCK=1`.
- **Quan (bot):** In a real Telegram group on a real phone: welcome on add, silent
  until asked, question chips, three picks + poll + map button, consent
  toggle acknowledges. `Dockerfile` builds.
- **Jihoo:** tokens final, the five components rendered in every state at
  `/dev/components` in both themes at 375px, the three screen layouts handed
  over, the French strings read out loud and fixed. From 14:30: the video,
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
| 14:30 | Clean-clone check on all three repos — anyone free. A README that fails gets a PR now, not at 15:25. |
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
