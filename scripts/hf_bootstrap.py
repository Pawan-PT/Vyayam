"""Create and configure the Hugging Face Docker Space for the VYAYAM demo.

Run by .github/workflows/deploy-hf.yml before the snapshot push. Idempotent.
Env: HF_TOKEN (required), HF_SPACE (optional, default "vyayam").
Stdout: HF_USER=, HF_SPACE_NAME=, and last line LIVE_URL=<url>.
The token is read from the environment only and is never printed.
"""
import os
import re
import secrets
import sys

from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError

DEFAULT_SPACE = "vyayam"


def fallback_subdomain(user, space):
    # HF builds <owner>-<space>.hf.space: lowercase, non-alphanumerics become "-".
    # Used only when the API does not return `subdomain`.
    return re.sub(r"[^a-z0-9]", "-", f"{user}-{space}".lower())


def main():
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("HF_TOKEN is empty", file=sys.stderr)
        return 1
    space = os.environ.get("HF_SPACE", "").strip() or DEFAULT_SPACE
    api = HfApi(token=token)

    user = api.whoami()["name"]
    repo_id = f"{user}/{space}"

    try:
        api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    except HfHubHTTPError as exc:
        # A refusal (paid plan / payment method) is a real answer: report HF's own words, no retry.
        print(f"HF_REFUSED_DOCKER_SPACE: {exc}", file=sys.stderr)
        return 2

    sub = api.space_info(repo_id, expand=["subdomain"]).subdomain or fallback_subdomain(user, space)
    url = f"https://{sub}.hf.space"

    for key, value in {
        "DJANGO_DEBUG": "False",
        "DJANGO_ALLOWED_HOSTS": ".hf.space",
        "DJANGO_CSRF_ORIGINS": url,
        "DEMO_SEED": "1",
    }.items():
        api.add_space_variable(repo_id, key, value)

    # Never rotate a working key: it would log out the demo.
    if "DJANGO_SECRET_KEY" not in api.get_space_secrets(repo_id):
        api.add_space_secret(repo_id, "DJANGO_SECRET_KEY", secrets.token_urlsafe(64))

    print(f"HF_USER={user}")
    print(f"HF_SPACE_NAME={space}")
    print(f"LIVE_URL={url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
