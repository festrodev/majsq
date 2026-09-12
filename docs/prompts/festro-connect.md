<!-- Ali's session. Rooted in festro-dev/ (not inside a repo) so EnterWorktree fans out. Paste _preamble.md first. -->

# Ali's part: the Festro side, then the demo

You are the only one with the private repos, so you own the piece that makes
"connect your Festro account" real, and the credentials that let the deployed
agent call Festro once App Check enforcement flips on. Everything else can be
demoed without you; this cannot.

Full design, already reviewed and approved by Codex (round 3):
`festro-hq/decisions/codex-consults/2026-09-12-majsq-agent.md`. Build exactly
that. The short version:

## 1. Register maj$q as a third-party application (10 min)

In `festro`, `apiclients.ApiApplication`: `client_id=majsq`, `kind=third_party`,
`rate_limit_tier=standard`, `scopes=["profile:read"]`. Add a `redirect_uris`
JSON list field (exact-match callbacks; `allowed_origins` are origins, not
callbacks) with `https://majsq.festro.com/connect/callback` and
`http://localhost:3000/connect/callback`. Print the secret once; put it in the
agent's `.env` as `FESTRO_CLIENT_ID` / `FESTRO_CLIENT_SECRET`. Verify a
catalog call from the agent carries both headers.

## 2. The connect grant — `festro` (the part Codex was strict about)

New in `apiclients`:

- `ConnectGrant`: application FK, user FK, `code_hash`, `redirect_uri`, `code_challenge` (S256), `expires_at` (5 min), `consumed_at`.
- `ConnectedCredential`: application FK, user FK, `key_hash`, `label`, `created_at`, `last_used_at`, `expires_at` (90 d), `revoked_at`. **Not an `AuthToken`. `DeviceTokenAuthentication` must never recognize it.**
- `POST /api/v1/connect/authorize/` — IsAuthenticated. Validates application active, `redirect_uri` ∈ `redirect_uris`, creates the grant, returns `{redirect_to}`.
- `POST /api/v1/connect/token/` — **requires `request.api_application`** from the secret-checked client middleware, explicitly (App Check is an OR gate, `festro/middleware/app_check.py:62`). Verifies S256 + exact redirect + same application + not expired + **user.is_active**; consumes and issues in one transaction. Throttle scope `connect_token`.
- `GET /api/v1/connect/profile/` — auth = client credential + `Authorization: Connect <key>`. Checks application match, not revoked/expired, application active, **user.is_active**. Returns the minimized taste profile (shape in `majsq/docs/CONTRACT.md §Festro`) computed from saved events, reservations and following. No email, no rows.
- `DELETE /api/v1/connect/credential/`. And `delete_me` revokes credentials + unconsumed grants in its transaction (it anonymizes, it does not delete the row — `account/api/views.py:1606` — so a FK cascade never fires).

Tests: the authorization matrix in the consult record, with
`FIREBASE_APP_CHECK_ENFORCE` off and on, including the deactivated-user case.

## 3. The approve page — `festroweb`

`app/[locale]/connect/authorize/page.tsx`: if not logged in, the existing
login with `next=`; then an approve card that lists exactly what
`profile:read` returns, in fr/en, a server action calling authorize, redirect
to `redirect_uri?code&state`. Copy the state-nonce pattern from
`lib/actions/calendar.ts`.

## 4. Hand the pieces over

- Give the **web owner** the flow: `/connect` on majsqweb generates PKCE + state bound to the `majsq_session`, redirects to `festro.com/connect/authorize?client_id=majsq&redirect_uri=…&state=…&code_challenge=…`, receives `?code&state` on `/connect/callback`, and POSTs `{code, code_verifier}` to a new agent endpoint.
- Give the **agent owner** the contract addition: `POST /api/link/` `{channel, kind, conversation_id, participant_id, code, code_verifier, redirect_uri}` → the agent exchanges with Festro using its client secret and stores the credential on `FestroLink`. Add it to `CONTRACT.md` via the agent owner.
- Run `/setdomain` in BotFather with the web domain so the **bot owner**'s `login_url` button appears.

## 5. Deploy, only if the three repos run locally by 14:00

Agent + bot → Cloud Run in `festro-app` via `gcloud run deploy` from Artifact
Registry `festro` (the `festro-staging-api` pattern; no Terraform today).
Web → Firebase App Hosting backend `majsq` (the festroqa recipe), host
`majsq.festro.com` via the `cf` CLI. Otherwise: everything local, one
`cloudflared` tunnel per service, and the video is shot on that.

## 6. The video and the submission (15:00 hard stop)

Two minutes. Laptop: welcome → chips → three picks in the web chat. Then two
phones in a real Telegram group: "quoi faire ce soir ?" → chips → picks →
poll → map. One sentence on why the group chat is where the decision is made.
Description, public repo links (all three), sponsor post tagging OpenAI and
CopilotKit. A clean clone of each repo runs from its README before you submit.

## Do not

- Do not mint an `AuthToken` for maj$q under any circumstances.
- Do not publish `festro-designs` tokens into the public repos unless you decide to; the neutral palette in `DESIGN.md` is the default.
- Worktree before the first edit in any Festro repo. CI is dispatch-only; run checks locally.
