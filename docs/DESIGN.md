# maj$q design system

One product, three surfaces, four people building in parallel. This file is
what keeps it looking and sounding like one thing. **Every agent session
working on any maj$q repo reads this first.** If you need something that is
not here, add it here in a PR before you use it, so the others get it too.

## The idea in one line

> The "what are we doing tonight?" decision happens in the group chat, not in
> an events app. maj$q goes where the decision is made.

Everything below serves that: fast, low-friction, at home in a chat, never
louder than the friends talking.

---

## 1. Voice

**French first, English second, both always.** Montréal. Every string exists
in `fr` and `en`; French is the default locale and the one you write first.

**Tutoiement.** maj$q says *tu*, never *vous* to one person. To a group it
says *vous* because it is addressing several people ("Vous avez envie de
quoi ?"). It is a friend who knows the city, not a service.

**Short.** A reply fits on one phone screen without scrolling. Three picks,
one line of metadata each, one optional line of reason. No paragraphs.

**Plain.** No exclamation marks in a row, no "Super !", no "Great choice!".
One emoji per message at most, and only the canonical ones below. Never
emoji as decoration in prose.

**Honest.** If it widened the search because a category was empty, it says
so: "Rien en humour ce soir, mais il y a ça :". If it does not know the start
time, it shows the date only. It never invents a fact the catalog did not give.

### Canonical strings

Use these verbatim. Do not paraphrase them per surface.

| Key | FR | EN |
|---|---|---|
| `welcome.title` | Salut 👋 Je suis **maj$q**. | Hi 👋 I'm **maj$q**. |
| `ask.when` | C'est pour quand ? | When is this for? |
| `ask.category` | Vous avez envie de quoi ? | What are you in the mood for? |
| `ask.area` | Un coin en particulier ? | Any particular area? |
| `ask.budget` | Quel budget ? | What's the budget? |
| `picks.headline` | {n} idées pour {what} {when} : | {n} picks for {when}: |
| `picks.widened` | Rien en {category} {when}, mais il y a ça : | Nothing in {category} {when}, but here's what's on: |
| `picks.none` | Je ne trouve rien {when}. On essaie un autre moment ? | I can't find anything {when}. Try another time? |
| `poll.question` | On fait lequel ? | Which one? |
| `btn.map` | 🗺 Ouvrir sur la carte | 🗺 Open the map |
| `btn.consent.on` | 🙋 Utiliser mes goûts ici | 🙋 Use my taste here |
| `btn.consent.off` | Ne plus utiliser mes goûts ici | Stop using my taste here |
| `btn.connect` | Connecter Festro | Connect Festro |
| `btn.guest` | Continuer sans compte | Continue without an account |
| `btn.calendar` | 📅 Ajouter au calendrier | 📅 Add to calendar |
| `nudge.connect` | 💡 Connecte ton compte Festro pour des choix qui te ressemblent. | 💡 Connect your Festro account for picks that fit you. |
| `consent.on.ack` | ✅ Tes goûts comptent dans ce groupe. | ✅ Your taste counts here. |
| `consent.off.ack` | Tes goûts ne comptent plus ici. | Your taste no longer counts here. |
| `error.agent` | Je n'arrive pas à joindre mon cerveau 🧠 Réessaie dans une minute. | I can't reach my brain 🧠 Try again in a minute. |
| `reason.aggregate` | {k} sur {n} aiment {tag} | {k} of {n} like {tag} |
| `reason.private` | tu aimes {tag} | you like {tag} |

The consent button label says **taste**, never attendance. Attendance is the
poll. Do not write "Compte sur moi" or "I'm in" on that button.

### Time and price

- Date + time: `samedi 13 sept. · 20:00` (FR) / `Sat 13 Sep · 20:00` (EN).
  24-hour clock in both languages.
- Unknown start time (`start_time_known=false`): date only, no hour. Never
  show `00:00`.
- Free: `Gratuit` / `Free`. Paid: show nothing — the catalog does not expose
  prices, and a made-up "$$" is a lie.

---

## 2. Categories and their emoji

The chip set is defined once, in `brain/categories.py` in the agent, and
served by `GET /api/categories/`. Surfaces render what the agent sends; they
do not keep their own list. The emoji is part of the identity of each
category and is the same everywhere:

| key | emoji | FR | EN |
|---|---|---|---|
| `live` | 🎤 | Concerts | Live music |
| `nightlife` | 🪩 | Sortir danser | Nightlife |
| `theatre` | 🎭 | Théâtre | Theatre |
| `dance` | 🩰 | Danse | Dance |
| `classical` | 🎻 | Classique & opéra | Classical & opera |
| `comedy` | 😂 | Humour | Comedy |
| `festival` | 🎪 | Festivals | Festivals |
| `free` | 🆓 | Gratuit | Free tonight |
| `surprise` | 🎲 | Surprends-moi | Surprise me |

Time slots: 🌙 Ce soir · 🌤 Demain · 🎉 Ce week-end · 🗓 Cette semaine.

---

## 3. Visual tokens (web)

Dark-first. The product is about going out at night, and a group chat on a
phone at 21:00 is the primary context. Light theme exists and is tested, but
the design decisions were made on the dark ground.

### Color

```css
:root {
  /* ground */
  --majsq-night:      #0E1116;   /* page background, dark */
  --majsq-surface:    #171C23;   /* cards, sheets */
  --majsq-surface-2:  #1F2630;   /* hover, nested */
  --majsq-line:       #2A323D;   /* borders, dividers */

  /* text */
  --majsq-ink:        #EEF1F5;   /* primary text on dark */
  --majsq-ink-2:      #A3ADBA;   /* secondary */
  --majsq-ink-3:      #6B7684;   /* tertiary, placeholders */

  /* accent — one, used sparingly */
  --majsq-lamp:       #F2A93B;   /* "lampadaire": buttons, active chip, marker */
  --majsq-lamp-ink:   #1A1200;   /* text on lamp */

  /* semantic — never as decoration */
  --majsq-ok:         #3CCB7F;
  --majsq-warn:       #FF7A52;
  --majsq-error:      #F04E5B;
  --majsq-link:       #7FD6D6;
}

[data-theme="light"], .light {
  --majsq-night:      #F4F5F7;
  --majsq-surface:    #FFFFFF;
  --majsq-surface-2:  #EDF0F4;
  --majsq-line:       #D6DBE3;
  --majsq-ink:        #151A21;
  --majsq-ink-2:      #4A5464;
  --majsq-ink-3:      #8A94A3;
  --majsq-lamp:       #D98F1F;
  --majsq-lamp-ink:   #FFFFFF;
  --majsq-link:       #0B6D6F;
}
```

The accent is amber, one value, used for: the primary button, the selected
chip, the map marker, the poll winner. Nothing else. If you want a second
accent you are wrong; use a neutral.

Neutrals are blue-biased greys on purpose. A pure `#888` reads as unfinished.

### Type

```css
--majsq-font-display: "Bricolage Grotesque", "Source Sans 3", system-ui, sans-serif;
--majsq-font-body:    "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
--majsq-font-mono:    "JetBrains Mono", ui-monospace, Menlo, monospace;
```

Google Fonts link (the only allowed font host):

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
```

Scale (rem): `3xl 2.25 · 2xl 1.75 · xl 1.375 · lg 1.125 · md 1 · sm 0.875 · xs 0.75`.
Display face for `xl` and above only. Body 17px on desktop, 16px on mobile,
line-height 1.55. Mono for event short ids and anything code-shaped.

### Spacing and shape

- 4px base. Use `4 8 12 16 24 32 48`.
- Radius: `--majsq-r-card: 12px`, `--majsq-r-chip: 999px`, `--majsq-r-input: 8px`.
- Borders 1px `--majsq-line`. No drop shadows on dark; one soft shadow
  (`0 1px 2px rgba(0,0,0,.06)`) allowed on light cards.
- Content column max 680px. Chat column max 720px.

### Components

Every surface has these five things. Build them once each, name them exactly
this, and reuse.

**Chip** — a tappable answer. Pill, `surface-2` ground, `ink` text, 1px
`line`. Selected: `lamp` ground, `lamp-ink` text. Emoji + label. Min height
40px, horizontal padding 14px. Chips wrap; never horizontally scroll a row of
answers.

**PickCard** — one event. Left: number (1/2/3) in display face. Body: title
(`lg`, 600), one meta line in `ink-2` (`when · venue · Gratuit`), optional
reason line in italic `ink-2`. Right or bottom: link to festro.com. No image.
Not a clickable card — the link is the affordance.

**QuestionBlock** — the agent asks. The question in `lg`, then chips. Appears
inline in the chat, never as a modal.

**MapMarker** — number badge, `lamp` ground, `lamp-ink` text, 28px circle.
Tapping shows the PickCard in a popover.

**ConsentToggle** — the 🙋 button. Same size and place whether on or off; the
label changes (`btn.consent.on` / `btn.consent.off`). It is never a checkbox.

### Map

MapLibre GL with OpenStreetMap raster tiles, no API key. Style the base
map to the theme (a dark raster style on dark). Markers only, no artwork.
Fit bounds to the picks with 48px padding; if one pick, zoom 15 centered.

### What is deliberately absent

- **No event artwork anywhere.** Festro's cover images are signed, expiring,
  and licensed for Festro's own pages. A pick is text and a link.
- No avatars, no member names next to picks in a group.
- No loading spinners longer than 300ms without text; say what is happening
  ("Je cherche ce soir…").
- No modals. Everything happens inline in the conversation.

---

## 4. Telegram rendering

Telegram has no CSS, so the tokens above become **structure**:

- One message per answer. Never three messages for three picks.
- Bold title, one metadata line indented with three spaces, optional
  italic reason line. Blank line between picks.
- Inline keyboard, in this order: one row per pick (link), then `btn.map`,
  then `btn.consent.*`. Never more than 2 buttons in a row.
- Questions: chips as inline keyboard, two per row.
- Poll: native Telegram poll, non-anonymous, options are pick titles
  truncated to 100 chars.
- `parse_mode=HTML`; escape `& < >` in every user-facing string.
- Never `sendPhoto`. See "What is deliberately absent".

---

## 5. Accessibility floor

- Text contrast ≥ 4.5:1 on both grounds (the tokens above pass; check yours).
- Every chip and button reachable by keyboard with a visible focus ring
  (2px `lamp` outline, 2px offset).
- `prefers-reduced-motion`: no animation beyond opacity.
- Touch targets ≥ 40px.
