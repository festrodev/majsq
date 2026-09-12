<!-- Paste _preamble.md above this line, then this file. Session rooted in the majsqweb repo. -->

# Your part: the web surface (`majsqweb`)

You own `/`, `/chat`, the server-side proxy routes, and the shared components.
**Jihoo works in this same repo on `/m/[share_id]` and `src/components/Map*.tsx`
only** — those files are theirs, yours are listed in `TEAM.md`. `PickCard` is
yours: Jihoo imports it, so tell them when its props change. Pull from `main`
before every push. The scaffold is Next.js 16 (App Router), React 19,
Tailwind v4, with `@copilotkit/react-core`, `@copilotkit/react-ui`,
`@copilotkit/runtime`, `@ag-ui/client` and `maplibre-gl` installed. Nothing
else exists yet. `DESIGN.md` is your spec; build the five components it names
once and reuse them.

Run the agent first (offline is fine):

```bash
# in a clone of majsq
FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py migrate && FESTRO_MOCK=1 MAJSQ_OPEN_AGUI=1 python manage.py runserver
# here
cp .env.example .env.local && npm install && npm run dev
```

## Build, in this order

### 1. Tokens and the five components

`src/app/globals.css`: the exact CSS variables from `DESIGN.md §3`, dark-first,
with the light overrides under `[data-theme="light"]` and
`@media (prefers-color-scheme: light)`. The Google Fonts link from the doc in
`layout.tsx`. Then `src/components/`: `Chip`, `PickCard`, `QuestionBlock`,
`MapMarker`, `ConsentToggle`, named exactly that. Show me a Storybook-free
`/dev/components` page rendering all five in both themes before moving on.

### 2. Identity: the `majsq_session` cookie

A route handler or middleware sets an httpOnly, `SameSite=Lax`,
`Secure`-in-prod cookie `majsq_session` = 22 random url-safe chars on first
visit. Every call to the agent uses that value as both `conversation_id` and
`participant_id` with `channel: "web", kind: "web"` — from the server, never
from the browser (`CONTRACT.md §Identity`).

### 3. Server-side proxy routes

`src/app/api/turn/route.ts`, `api/slots`, `api/categories`, `api/consent`:
each reads the cookie, adds `X-Majsq-Service-Secret` from `process.env`
(never `NEXT_PUBLIC_`), forwards to `MAJSQ_AGENT_URL`, returns the JSON. The
browser never sees the secret or the agent URL.

### 4. `/` — welcome

"Salut 👋 Je suis **maj$q**." + one line. Primary button `btn.connect`
(links to `/connect`, which for today is a placeholder page that says the
connect flow is coming — Ali owns the Festro side). Secondary `btn.guest` →
`/chat`. The window chips (from `/api/slots`) right on this page, so the first
tap is the first answer. Locale from `Accept-Language`, `fr` default, a small
FR/EN switch in the header.

### 5. `/chat` — the conversation

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

### 6. `/m/[share_id]` — not yours

Jihoo is building it. Make sure `PickCard` is importable and self-contained
(no dependency on chat state or the session cookie) so their page can use it.

### 7. CopilotKit, once the stream exists

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

### 8. Both themes, mobile first

Check every page at 375px and in both themes. Text contrast ≥ 4.5:1. Focus
rings visible.

## Do not

- No event images, no `<img>` of anything from Festro. Ever.
- No second accent color. No modals. No chip list of your own.
- Nothing that calls `api.festro.com` from this repo.
