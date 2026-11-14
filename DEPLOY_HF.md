# Deploy VYAYAM demo to Hugging Face Spaces

Demo only. The database is SQLite inside the container, so all data is wiped when the Space restarts.

**`DEMO_SEED=1` is set on the Space. It creates a publicly reachable login with a fixed password, so never put real patient data in this Space.**

Setup in GitHub repo Settings -> Secrets and variables -> Actions:
- Secret `HF_TOKEN`: already set.
- Optional variable `HF_SPACE`: the Space name. Default: `vyayam`.

The push to `deploy` (or Actions -> Run workflow on `deploy`) creates and configures the Space and pushes the code. The live URL is written to `DEPLOY_RESULT.md` on the `deploy` branch.
