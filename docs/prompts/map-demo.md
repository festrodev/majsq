<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsqweb repo. -->

# Your part: the map page, then the submission (`majsqweb` + all three repos)

You own two things: the page everyone lands on from Telegram, and the package
we actually submit at 16:00. The second one is why we don't lose.

You work in `majsqweb` alongside the web owner. **Your files are disjoint from
theirs** — keep it that way and there are no conflicts:

| Yours | Theirs |
|---|---|
| `src/app/m/[share_id]/**` | `src/app/page.tsx`, `src/app/chat/**` |
| `src/components/Map*.tsx` | `src/components/Chip.tsx`, `PickCard.tsx`, `QuestionBlock.tsx`, `ConsentToggle.tsx` |
| `src/lib/share.ts` | `src/lib/turn.ts`, `src/app/api/**` |

`PickCard` is **theirs** — you import it, you don't edit it. If it needs a
change for the map, ask them in the group chat. Pull from `main` before every
push. Branch `feat/map`, PR into `main`.

## 1. `/m/[share_id]` — the map (do this first, it is on the critical path)

This is what a Telegram user taps. It must work with no cookie, no login, and
on a phone on venue wifi.

- Server component. Fetch `GET {MAJSQ_AGENT_URL}/api/shares/{share_id}/` — **no
  service secret needed**, the unguessable id is the credential
  (`CONTRACT.md §shares`). 404 → a real "ce lien n'existe plus" page, not a crash.
- MapLibre GL (already installed) with OpenStreetMap raster tiles, **no API
  key** — a fork has to be able to run this. Dark raster style on dark theme.
- Three `MapMarker`s numbered 1–3: 28px circle, `--majsq-lamp` ground,
  `--majsq-lamp-ink` number. Fit bounds to the picks with 48px padding; a
  single pick zooms to 15 and centers.
- Tapping a marker opens a popover with that pick's `PickCard`.
- **Under the map, the three `PickCard`s again**, in order. Not everyone can
  use a map, and this is also what renders if MapLibre fails to load.
- Some events have `latitude`/`longitude` of `null`. Do not drop them — show
  them in the list below with a "lieu à confirmer" note, and fit bounds to
  whatever does have coordinates.
- Both themes, 375px wide, and check it over a phone hotspot if you can.

Tokens and strings: `DESIGN.md §3` and `§1`. No event images, ever.

## 2. Calendar links

Each `PickCard` on your page gets `btn.calendar` (📅 Ajouter au calendrier).
Build a Google Calendar template URL from `title`, `start_datetime`,
`end_datetime`, `venue_name` and `url`. No OAuth. If `start_time_known` is
false, make it an all-day event rather than inventing an hour.

Put the builder in `src/lib/share.ts` and tell the web owner it exists — they
need the same thing in `/chat`.

## 3. From 14:30: the submission package — you own this, nobody else touches it

The freeze is at 14:30. From then you are the only person whose work still
changes, and these five things are what the judges see.

**Clean-clone check, all three repos.** On a machine that has never run this:
clone, follow the README exactly, and confirm it runs. Any step that fails is
a PR to that repo's README, immediately. Do this at 14:30, not at 15:25.

**The two-minute video.** Shoot it in this order — it is the story:
1. 10s: the problem, in the group chat. Someone types "on fait quoi ce soir?" and nobody answers.
2. 40s: two phones, a real Telegram group. Add the bot, ask, chips, three picks, the poll, people voting.
3. 40s: tap the map button, land on your page, three markers in Montréal.
4. 20s: the same agent in the browser chat, to show it is one brain in three places.
5. 10s: one sentence — the agent goes where the decision is made, not where the listings are.

Shoot vertical if it's phone-heavy. Real events, real venue names on screen.

**The written description.** What we built, and *why the context matters* —
that is the hackathon's actual question. Lead with: the decision happens in the
group chat, so the agent lives there. Mention: three surfaces one brain, real
catalog of 3,400+ Montréal events, and that a connected member's history is
opt-in per group with aggregate-only reasons.

**The social post.** Tag the sponsors — OpenAI and CopilotKit at minimum. One
screenshot or the video.

**Submit by 15:45.** Title, description, the three repo links, video, social
post. Do not wait for 16:00.

## If the web owner is behind at 14:00

Say so in the group chat and take `/chat` from them rather than polishing the
map. A working chat beats a beautiful map.

## Do not

- No event artwork. No second accent color. No Mapbox (it needs a key).
- Do not edit the web owner's files. Ask in the chat instead.
- Do not start the video before 14:30 — you will shoot it twice.
