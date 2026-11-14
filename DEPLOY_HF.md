# Deploy VYAYAM to Hugging Face Spaces (Docker)

Push to the `deploy` branch on GitHub -> GitHub Action force-pushes to your Space -> HF builds the Dockerfile and starts it.

Replace `<USER>` with your HF username and `<SPACE>` with the Space name. Both are lowercase-safe: the live host is `<user>-<space>.hf.space` (lowercase, HF joins them with a dash).

> **NEVER run `seed_demo_patient` or `seed_therapist_demo` against the deployed database.** `seed_demo_patient` plants a fixed `demo1234` login. Anyone can guess it.

## 1. Create the Hugging Face Space

1. Go to https://huggingface.co/new-space and sign in.
2. Owner: your user. Space name: e.g. `vyayam`. License: your choice.
3. SDK: **Docker** (choose "Blank" template).
4. Hardware: **CPU basic** (free, 2 vCPU, 16 GB RAM).
5. Visibility: choose Private if you do not want the public to reach it. Create the Space.
6. Leave it empty. The GitHub Action fills it.

## 2. Create a free Postgres and get `DATABASE_URL`

The Space disk is wiped on every restart. SQLite would lose all data. Use Postgres.

1. Make a free Postgres (for example https://neon.tech or https://supabase.com).
2. Create a project and a database.
3. Copy the connection string. It looks like `postgres://USER:PASSWORD@HOST/DBNAME`.
4. It must allow SSL. The app forces SSL when `DJANGO_DEBUG=False` (`vyayam_project/settings.py:84`). Neon and Supabase both do.

## 3. Create a Hugging Face access token

1. https://huggingface.co/settings/tokens -> New token.
2. Type: **Write** (or fine-grained with write access to the Space).
3. Copy it. You see it once.

## 4. Add GitHub repository variables and secret

Repo `Pawan-PT/Vyayam` -> Settings -> Secrets and variables -> Actions.

Tab **Variables** -> New repository variable:

| Name | Value |
|---|---|
| `HF_USERNAME` | `<USER>` |
| `HF_SPACE` | `<SPACE>` |

Tab **Secrets** -> New repository secret:

| Name | Value |
|---|---|
| `HF_TOKEN` | the token from step 3 |

## 5. Add env vars to the Space

Space -> Settings -> "Variables and secrets".

Add as **Secret** (hidden):

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | 50+ random chars. Make one: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | from step 2 |
| `DJANGO_EMAIL_HOST_PASSWORD` | SMTP password (only if you send reset emails) |
| `SENTRY_DSN` | optional |

Add as **Variable** (plain):

| Name | Value |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `.hf.space` |
| `DJANGO_CSRF_ORIGINS` | `https://<user>-<space>.hf.space` |
| `DJANGO_SSL_REDIRECT` | `0` |
| `DJANGO_TRUSTED_PROXY` | `1` |
| `DJANGO_EMAIL_HOST` | e.g. `smtp.sendgrid.net` (password-reset emails do nothing without it) |
| `DJANGO_EMAIL_PORT` | `587` |
| `DJANGO_EMAIL_HOST_USER` | e.g. `apikey` |
| `DJANGO_EMAIL_USE_TLS` | `True` |
| `DJANGO_DEFAULT_FROM_EMAIL` | `VYAYAM <noreply@vyayam.app>` |

Why these values (checked in code):

- `DJANGO_ALLOWED_HOSTS` is split on commas and used as-is (`settings.py:18`). A leading dot matches the host and all subdomains, so `.hf.space` covers `<user>-<space>.hf.space`. If unset with DEBUG off, it falls back to `.onrender.com` (`settings.py:21-22`) and every request fails.
- `DJANGO_CSRF_ORIGINS` is split on commas and needs the scheme (`settings.py:24-26`). Use the exact host. Do not use `https://*.hf.space`: it would trust every other Space.
- `DJANGO_SSL_REDIRECT=0`: cookies are already Secure and HSTS is on when DEBUG is off (`settings.py:164-170`). Set `1` later if you confirm HF forwards `X-Forwarded-Proto: https`.
- `DJANGO_TRUSTED_PROXY=1` lets the rate limiter read `X-Forwarded-For` (`strength_app/rate_limiter.py:56`). Safe only behind a proxy. HF is one.

## 6. Make the first deploy

```
git checkout deploy
git push origin deploy
```

1. GitHub -> Actions -> "Deploy to Hugging Face Space". Wait for green.
2. Space page -> Logs. The first build takes several minutes.
3. Start-up is slow: the app loads 516 exercise modules (about 55 s, 450 MB). Wait for the gunicorn line.
4. Later deploys: merge `main` into `deploy`, then `git push origin deploy`.

## 7. Check it works

1. Open **https://`<user>-<space>`.hf.space/healthz/** directly. Expect `{"status":"ok"}`.
2. Use the direct `.hf.space` URL. Do not use the `huggingface.co/spaces/...` page. The app sends `X-Frame-Options: DENY` (`settings.py`), so the HF iframe stays blank. Camera access also needs the direct URL.
3. Create the admin user. Space has no shell, so run this once from your own machine against the same database:
   ```
   DJANGO_SECRET_KEY=x DJANGO_DEBUG=False DATABASE_URL='<your url>' python manage.py createsuperuser
   ```
   Use a strong password. Only `createsuperuser`. Never the seed commands.
4. Send a password-reset email to yourself to check SMTP.

## Limits you should know

- **One worker only.** Two would run out of memory (`entrypoint.sh`).
- Free Spaces sleep after inactivity. The next visit re-runs migrate and the slow start.
- `media/` uploads vanish on restart.
- The rate limiter keeps counts in memory. They reset on restart.
- Free CPU basic Space has 16 GB RAM, so the 450 MB import fits. Confirm in Logs.

## If something fails

| Symptom | Fix |
|---|---|
| Action fails with `403` or `401` | `HF_TOKEN` wrong or read-only. Redo step 3 and 4. |
| Action: `HF_USERNAME`/`HF_SPACE` empty | Put them under **Variables**, not Secrets. |
| Space: `KeyError: 'DJANGO_SECRET_KEY'` | Add it in step 5 and restart the Space. |
| `Bad Request (400)` on every page | `DJANGO_ALLOWED_HOSTS` wrong. |
| `403 CSRF verification failed` | `DJANGO_CSRF_ORIGINS` has wrong host or no `https://`. |
| `SSL` error from the database | The Postgres host does not allow SSL. Pick one that does. |
