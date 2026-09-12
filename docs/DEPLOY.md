# Deploying maj$q

**Nothing here is needed to submit the hackathon.** The submission wants a
public repo, a video and a description; the demo runs locally with a tunnel for
the Telegram webhook. Deploy when you want the thing to outlive the afternoon.

## What runs where

| Repo | Where | How |
|---|---|---|
| `majsq` | Cloud Run service `majsq-agent` | Actions → **Deploy agent** |
| `majsqbot` | Cloud Run service `majsq-bot` | Actions → **Deploy bot** |
| `majsqweb` | Firebase App Hosting backend `majsq` | Actions → **Deploy web** |

All three are `workflow_dispatch`: Actions tab → pick the workflow → **Run
workflow**. Anyone with write access can run them. None of them fires on a
merge, because merging is not shipping.

Deploy order the first time: **agent → web → bot**. The bot needs the agent's
URL as an input, and the web's map links want a real domain.

---

## One-time setup — Ali only

Everything below touches cloud identity and secrets. It has to be done once,
by the person who owns the GCP project. Until it is, the deploy workflows fail
immediately with a message saying so, which is the intended behaviour: a
missing secret should not look like a Google outage.

### 1–3. Identity and secrets — DONE (2026-09-12)

Already set up; recorded here so nobody redoes it or copies the wrong pattern.

The Workload Identity pool's own condition was **already** org-wide
(`assertion.repository_owner == 'festrodev'`), so nothing needed widening. The
real gate is the per-service-account binding, which names repositories one by
one.

maj$q deploys as its **own** service account, `majsq-deployer@festro-app`, with
exactly three roles: `run.admin`, `artifactregistry.writer`,
`iam.serviceAccountUser`. Only `festrodev/majsq`, `majsqweb` and `majsqbot` may
impersonate it.

> **Do not reuse `festro-ci-releaser` here.** That is the account the private
> repos deploy with, and it holds `container.developer` — production GKE. The
> maj$q repos are **public**: GitHub withholds secrets from fork pull requests
> today, but one `pull_request_target` workflow added later would turn an
> outside contributor's PR into production deploy access. A separate identity
> with no GKE role is what keeps that impossible rather than merely unlikely.

`GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_CI_SERVICE_ACCOUNT` are set on all
three repos.

### 4. Create the runtime secrets in Secret Manager

The workflows mount these into the containers. Create only the ones you have; a
missing secret fails the deploy loudly rather than starting a half-configured
service.

```bash
create() { printf '%s' "$2" | gcloud secrets create "$1" --data-file=- --project festro-app 2>/dev/null \
  || printf '%s' "$2" | gcloud secrets versions add "$1" --data-file=- --project festro-app; }

create majsq-django-secret          "$(python3 -c 'import secrets;print(secrets.token_urlsafe(50))')"
create majsq-service-secret         "$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
create majsq-openai-key             "sk-..."
create majsq-festro-client-id       "fc_majsq"
create majsq-festro-client-secret   "fcsk_..."      # from register_connect_app
create majsq-telegram-token         "123456:ABC..."  # from @BotFather
create majsq-telegram-webhook-secret "$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
create majsq-telegram-username      "majsq_bot"
```

`majsq-service-secret` must be the **same value** in the agent and the bot —
it is how they recognize each other. Grant the runtime service account read
access:

```bash
for s in majsq-django-secret majsq-service-secret majsq-openai-key \
         majsq-festro-client-id majsq-festro-client-secret \
         majsq-telegram-token majsq-telegram-webhook-secret majsq-telegram-username; do
  gcloud secrets add-iam-policy-binding "$s" --project festro-app \
    --member "serviceAccount:$(gcloud projects describe festro-app --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
    --role roles/secretmanager.secretAccessor
done
```

### 5. Create the App Hosting backend and the subdomain

Same recipe as `festroqa` and `festrolabs`:

```bash
npx firebase-tools@13 apphosting:backends:create --project festro-app \
  --location us-east4 --backend majsq
```

Then DNS, with the Cloudflare CLI:

```bash
cf dns records create --zone festro.com --type CNAME --name majsq --content <apphosting-target>
cf dns records create --zone festro.com --type CNAME --name _acme-challenge.majsq --content <challenge-target>
```

Leave both **DNS-only** until the certificate issues, then flip `majsq` to
Proxied. Flipping early is why a cert can sit pending for an hour.

---

## After the first deploy

1. Run **Deploy agent**. The summary prints the service URL.
2. Run **Deploy bot** with that URL as `agent_url`.
3. Point Telegram at the bot once:

```bash
curl -F "url=https://<bot-url>/tg/webhook/" \
     -F "secret_token=$TELEGRAM_WEBHOOK_SECRET" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook"
```

4. Run **Deploy web**.
5. Add `https://majsq.festro.com/connect/callback` to maj$q's registered
   redirect URIs on Festro, or the connect flow refuses it:

```bash
python manage.py register_connect_app majsq \
  --redirect-uri https://majsq.festro.com/connect/callback \
  --redirect-uri http://localhost:3000/connect/callback
```

---

## The one thing that will bite you

The agent's Dockerfile puts SQLite in `/tmp`. Cloud Run's filesystem is
per-instance and ephemeral, so **every conversation is lost on restart** and two
instances never see the same data. `--max-instances 2` in the workflow makes
that second problem real, not theoretical.

For a demo this is fine and it is why it ships this way. Before anyone relies on
it: add `psycopg[binary]` and `dj-database-url` to requirements, set
`DATABASE_URL` to a Cloud SQL instance, and drop max-instances back to whatever
you like.
