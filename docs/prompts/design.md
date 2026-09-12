<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsqweb repo. -->

# Your part: design — how maj$q looks, reads and feels

You are the design lead. Nobody else decides a color, a word, a spacing or a
screen layout; three engineers are building fast today and without you they
will each invent their own. Your output is not opinions in a chat — it is
**tokens, components and strings that they consume directly**.

Manh builds the web app's pages and logic. You own what they look like. In the
same repo, on disjoint files:

| Yours | Manh's |
|---|---|
| `src/app/globals.css` — every token | `src/app/page.tsx`, `chat/**`, `m/**`, `api/**` |
| `src/app/dev/**` — the gallery | `src/lib/**` |
| `src/components/ui/**` — the visual primitives you author | `src/components/*.tsx` — the wired components |
| `public/**` — favicon, OG image | |
| `majsq/docs/DESIGN.md` — the spec | |

Branch `design/<thing>`, PR into `main`, pull before every push. If you need a
change inside Manh's files, say so in the group chat with the exact class
string — do not edit their file.

## What already exists

```bash
npm install && npm run dev      # http://localhost:3000/dev/tokens
```

`src/app/globals.css` holds a working first pass: dark-first ground, ink,
**one** amber accent (`--majsq-lamp`, a Montréal street lamp at night),
semantic colors, radii, and the Bricolage Grotesque + Source Sans 3 pairing.
All three theme states are wired (explicit dark, explicit light, and the
un-stamped OS default). `/dev/tokens` renders all of it in both themes.

Treat that as a starting point that is yours to change, not a decision already
made. The spec it came from is `majsq/docs/DESIGN.md` §3.

## Build, in this order

### 1. Own the tokens (30 min)

Open `/dev/tokens`, switch your OS between light and dark, and make the palette
yours. Specifically decide:

- **Is amber right?** It has to work on both grounds, read as "night out"
  rather than "warning", and never fight the event titles. If you change it,
  change it in one place and everything follows.
- **The neutrals.** They are blue-biased greys on purpose — a pure `#888`
  reads as unfinished. Push the bias further or pull it back.
- **Contrast.** Every text token on its ground must clear 4.5:1. Check
  `ink-2` and `ink-3` on `surface` in both themes; those are the two that fail
  in practice.

Rule that does not move: **one accent**. If a screen needs a second, it needs
a neutral instead.

### 2. The five components, as visual primitives (this is the critical path)

`majsq/docs/DESIGN.md §3` names five. Manh wires them to data; you decide what
they look like. Build each in `src/components/ui/` as a presentational
component with no data fetching, and render every state in `/dev/components`:

- **`Chip`** — a tappable answer. Default, selected, disabled, with a count
  ("🎭 Théâtre · 26"). Min 40px tall. Chips **wrap**, never scroll sideways.
- **`PickCard`** — one event. Number, title, one metadata line
  (`samedi 13 sept. · 20:00 · Théâtre du Nouveau Monde · Gratuit`), an optional
  italic reason line, a link to festro.com, a calendar button. **No image** —
  this is the constraint that shapes the whole card, see below.
- **`QuestionBlock`** — the agent asking. Question, then chips. Inline in the
  conversation, never a modal.
- **`MapMarker`** — numbered circle, 28px, amber.
- **`ConsentToggle`** — the 🙋 button. Same size and position on and off; only
  the label changes.

Then a **`/dev/components` page** showing all five in every state, in both
themes, at 375px and at desktop width. That page is the handoff. When Manh
asks "what should this look like", the answer is a link to it.

### 3. The hard one: a beautiful card with no image

Every events product leans on artwork. We cannot — Festro's images are signed,
expiring and licensed for Festro's own pages, so a pick is text and a link.
That is a real design problem and solving it well is what will make this look
considered rather than unfinished. Typography, hierarchy, the metadata line,
the number, whitespace, maybe a generated color per venue or category. Make
three variants, put them side by side in `/dev/components`, pick one.

### 4. The three screens

Sketch them as static layouts (in `/dev/`, or in a tool and exported — your
call), and hand Manh the structure:

- **`/` welcome** — "Salut 👋 Je suis maj$q.", one line of what it does, the
  connect button emphasized but skippable, and the time-slot chips right there
  so the first tap is already the first answer.
- **`/chat`** — a conversation. User messages, question blocks, then the
  headline and three pick cards. Input at the bottom.
- **`/m/[share_id]`** — a map with three numbered markers, and the same three
  pick cards below it for anyone who cannot use a map.

Mobile first. Someone opens the map link from Telegram, standing outside, on
one bar of signal.

### 5. The words

`DESIGN.md §1` has the canonical FR/EN strings. You own them. Read them out
loud in French — if any of them sounds like a corporate chatbot rather than a
friend who knows the city, change it and tell everyone in the group chat.
Tutoiement to one person, *vous* to a group. French first, always both.

### 6. From 14:30 — the submission

After the feature freeze you are the only person whose work still changes.

- **The two-minute video**, shot in this order: the problem in a group chat
  (10s) → two phones, a real Telegram group, ask → chips → three picks → poll
  (40s) → tap the map, land on the map page (40s) → the same agent in the
  browser, to show it is one brain in three places (20s) → one sentence: the
  agent goes where the decision is made (10s).
- **The written description** — lead with *why the context matters*, which is
  the hackathon's actual question.
- **The social post**, tagging OpenAI and CopilotKit.
- Submit by **15:45**, not 16:00.

## Do not

- No event artwork, anywhere, ever. This is licensing, not taste.
- No second accent color. No modals. No spinner without text.
- Do not edit Manh's files. Give them the class string instead.
- Do not start the video before 14:30 — you will shoot it twice.
