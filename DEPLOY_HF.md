# Deploy VYAYAM demo to Hugging Face Spaces

Demo only. The database is SQLite inside the container, so all data is wiped when the Space restarts.

**Setting `DEMO_SEED=1` creates a publicly reachable login with a fixed password, so never put real patient data in this Space.**

1. Create a Space at https://huggingface.co/new-space. SDK: Docker (Blank). Hardware: CPU basic. Leave it empty.
2. Create an HF access token with write access: https://huggingface.co/settings/tokens
3. GitHub repo Settings -> Secrets and variables -> Actions:
   - Variables: `HF_USERNAME` (your HF user), `HF_SPACE` (the Space name).
   - Secret: `HF_TOKEN` (the token from step 2).
4. Space Settings -> Variables and secrets. Add:
   - `DJANGO_SECRET_KEY` (Secret): 50+ random chars. `python -c "import secrets; print(secrets.token_urlsafe(64))"`
   - `DJANGO_DEBUG` = `False`
   - `DJANGO_ALLOWED_HOSTS` = `.hf.space`
   - `DJANGO_CSRF_ORIGINS` = `https://<user>-<space>.hf.space` (lowercase, scheme included)
   - Optional: `DEMO_SEED` = `1` (seeds demo logins at each start).
5. Deploy: `git push origin deploy`. Watch GitHub -> Actions, then the Space Logs. The first start takes about a minute (the app loads 450 MB of exercise code).
6. Open `https://<user>-<space>.hf.space/healthz/`. Expect `{"status":"ok"}`.

Use the direct `.hf.space` URL, not the huggingface.co Space page. The app blocks iframes, and the camera needs the direct URL.
