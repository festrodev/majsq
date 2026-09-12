<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsqweb repo. -->

# Your part: the web surface (`majsqweb`)

You build the whole web app: every page, every wired component, the data flow.
**Jihoo is the design lead** and works in this same repo on disjoint files —
`src/app/globals.css` (all tokens), `src/app/dev/**` (the galleries),
`src/components/ui/**` (visual primitives) and `public/**`. You never edit
those; they never edit yours. When you need to know what something looks like,
open `/dev/components` — that page is the handoff, not a conversation.

Already in the repo and working:

- `src/app/globals.css` — the design tokens, exposed to Tailwind. Write
  `bg-surface text-ink rounded-[var(--radius-card)]`. **Never a hex value.**
- `src/lib/agent.ts` — a typed server-only client for every contract endpoint
  (`turn`, `slots`, `categories`, `share`).
- `src/lib/session.ts` — `getSessionId()`, the httpOnly `majsq_session` cookie.
- `src/app/api/turn/route.ts` — the browser's only route to the agent.
- `layout.tsx` with the fonts. `/dev/tokens` to see the palette.

Stack: Next.js 16 App Router, React 19, Tailwind v4, with
`@copilotkit/react-core`, `@copilotkit/react-ui`, `@copilotkit/runtime`,
`@ag-ui/client` and `maplibre-gl` installed.

Run the agent first (offline is fine):

```bash
# in a clone of majsq
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py migrate && FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py runserver
# here
cp .env.example .env.local && npm install && npm run dev
```

## Build, in this order

### 1. The remaining proxy routes

`api/slots`, `api/categories`, `api/consent`, mirroring the existing
`api/turn/route.ts`: read the cookie with `getSessionId()`, call `lib/agent.ts`,
return the JSON. The browser never sees the secret or the agent URL.

### 2. Wire the components

Jihoo authors the look in `src/components/ui/`. You write the wired versions in
`src/components/` — `Chip`, `PickCard`, `QuestionBlock`, `MapMarker`,
`ConsentToggle` — that take contract types from `lib/agent.ts` and render
Jihoo's primitives. If a primitive is not ready yet, build the plainest
possible version against the tokens and swap it later; do not block on design
and do not invent a look of your own.

### 3. `/` — welcome

"Salut 👋 Je suis **maj$q**." + one line. Primary button `btn.connect`
(links to `/connect`, which for today is a placeholder page that says the
connect flow is coming — Ali owns the Festro side). Secondary `btn.guest` →
`/chat`. The window chips (from `/api/slots`) right on this page, so the first
tap is the first answer. Locale from `Accept-Language`, `fr` default, a small
FR/EN switch in the header.

### 4. `/chat` — the conversation

Drive it through `POST /api/turn/` first (the AG-UI stream returns 501 until
the agent owner ships it — see `CONTRACT.md`). One `useTurn()` hook wraps the
call; that is the one file that changes when the stream lands.

Render, top to bottom, as a conversation: the user's messages, then either a
`QuestionBlock` (chips from `reply.question.options`; tapping sends
`chosen: {name: value}`) or the headline + three `PickCard`s + a `btn.map`
link to `/m/{share_id}` + `btn.calendar` per pick (a Google Calendar template
URL built from `start_datetime`/`end_datetime`/`title`/`venue_name`, no OAuth).
Bind the window and category chips to `reply.state` so a tap and a typed
sentence end in the same place. Show `nudge.connect` when `suggest_connect`.
Text input at the bottom, `Enter` sends. Loading text, not a spinner:
"Je cherche…".

### 5. `/m/[share_id]` — the map

This is what a Telegram user taps, so it must work with **no cookie, no login**,
on a phone. Server component, `share()` from `lib/agent.ts`. MapLibre with
OpenStreetMap raster tiles and **no API key** (a fork has to run it). Three
numbered markers, fit bounds with 48px padding, popover shows the `PickCard`.
Under the map, the same three `PickCard`s for anyone who cannot use a map —
that is also what renders if MapLibre fails to load. Some events have `null`
coordinates: keep them in the list below with a "lieu à confirmer" note rather
than dropping them, and fit bounds to the ones that do have coordinates.

Each card gets `btn.calendar` — a Google Calendar template URL from `title`,
`start_datetime`, `end_datetime`, `venue_name`, `url`. No OAuth. When
`start_time_known` is false, make it an all-day event rather than inventing
an hour.

### 6. CopilotKit, once the stream exists

`src/app/api/copilotkit/[[...slug]]/route.ts` with `CopilotRuntime`, the
agent registered as `HttpAgent({ url: MAJSQ_AGENT_URL + "/agui/", headers: {"X-Majsq-Service-Secret": …} })`
under the name `majsq`. In `/chat`, `<CopilotKit runtimeUrl="/api/copilotkit" agent="majsq">`,
`useCoAgent` bound to the state snapshot in `CONTRACT.md §AG-UI`,
`useCoAgentStateRender` rendering the same `QuestionBlock` / `PickCard`s from
`state.question` / `state.picks`, and `useCopilotAction` with
`renderAndWaitForResponse` for the chips. Confirm the exact `HttpAgent`
registration shape against the installed `@copilotkit/runtime` version before
building on it; tell me what you find. If Ali gives you a Copilot Cloud
`publicApiKey`, it goes in `NEXT_PUBLIC_COPILOT_CLOUD_PUBLIC_API_KEY` and the
self-hosted route stays as the fallback.

### 7. Both themes, mobile first

Check every page at 375px and in both themes. Text contrast ≥ 4.5:1. Focus
rings visible.

## Do not

- No event images, no `<img>` of anything from Festro. Ever.
- No second accent color. No modals. No chip list of your own.
- No hex values or arbitrary colors in a component. Tokens only.
- Do not edit `globals.css`, `src/app/dev/**`, `src/components/ui/**` or
  `public/**` — those are Jihoo's. Ask in the group chat instead.
- Nothing that calls `api.festro.com` from this repo.
