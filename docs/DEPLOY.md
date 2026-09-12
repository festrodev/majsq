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

### 1. Let the three repos use the existing Workload Identity pool

Festro already deploys from GitHub without any long-lived key, using Workload
Identity Federation. The provider has an attribute condition listing which
repositories may borrow the service account, and the three new repos are not in
it yet.

Find the provider, then widen the condition:

```bash
gcloud iam workload-identity-pools providers list \
  --project festro-app --location global --workload-identity-pool github
```

```bash
gcloud iam workload-identity-pools providers update-oidc github \
  --project festro-app --location global --workload-identity-pool github \
  --attribute-condition="assertion.repository_owner=='festrodev'"
```

That condition trusts every repo in the `festrodev` org. It is the simple
version and it is what makes one setup cover all three. If you would rather
name them explicitly:

```bash
--attribute-condition="assertion.repository in ['festrodev/festro','festrodev/festroweb','festrodev/festroapp','festrodev/infrastructure','festrodev/majsq','festrodev/majsqweb','festrodev/majsqbot']"
```

> The trade is real. The org-wide condition means **any repo anyone creates
> under `festrodev` can deploy**. That is fine while the org is five people and
> every repo is ours; it stops being fine the moment an outside contributor can
> create one. Revisit it then.

### 2. Give the CI service account what it needs

The existing service account deploys to GKE, not Cloud Run:

```bash
SA=$(gh secret list -R festrodev/festro >/dev/null && echo "<the GCP_CI_SERVICE_ACCOUNT value>")

for role in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding festro-app \
    --member "serviceAccount:$SA" --role "$role"
done
```

`iam.serviceAccountUser` is the one people forget. Cloud Run deploys *as* a
runtime service account, and deploying as one counts as using it.

### 3. Copy the two secrets onto the three repos

```bash
WIP='<GCP_WORKLOAD_IDENTITY_PROVIDER value>'
SA='<GCP_CI_SERVICE_ACCOUNT value>'

for repo in majsq majsqweb majsqbot; do
  gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER -R "festrodev/$repo" --body "$WIP"
  gh secret set GCP_CI_SERVICE_ACCOUNT        -R "festrodev/$repo" --body "$SA"
done
```

You cannot read the existing values back out of GitHub — secrets are
write-only. Take them from the GCP console, or from wherever you stored them
when you set up festro's deploy.

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
