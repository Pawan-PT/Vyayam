"""Create and configure the Hugging Face Docker Space for the VYAYAM demo.

Run by .github/workflows/deploy-hf.yml before the snapshot push. Idempotent.
Env: HF_TOKEN (required), HF_SPACE (optional, default "vyayam").
Stdout: HF_USER=, HF_SPACE_NAME=, and last line LIVE_URL=<url>.
The token is read from the environment only and is never printed.
Always writes DEPLOY_RESULT.md (repo root): first line STATUS=OK or STATUS=FAILED.
"""
import os
import re
import secrets
import sys

from huggingface_hub import HfApi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hf_diagnose import diagnose  # noqa: E402

DEFAULT_SPACE = "vyayam"
RESULT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DEPLOY_RESULT.md")


def write_result(lines):
    with open(RESULT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def fail(verdict):
    write_result([
        "STATUS=FAILED",
        f"CODE={verdict['code']}",
        f"REASON={verdict['reason']}",
        f"FIX={verdict['fix']}",
        "",
        "HF said:",
        "```",
        verdict["message"],
        "```",
    ])
    print(f"DEPLOY_FAILED CODE={verdict['code']} REASON={verdict['reason']}", file=sys.stderr)
    print(f"FIX={verdict['fix']}", file=sys.stderr)
    return 2


def fallback_subdomain(user, space):
    # HF builds <owner>-<space>.hf.space: lowercase, non-alphanumerics become "-".
    # Used only when the API does not return `subdomain`.
    return re.sub(r"[^a-z0-9]", "-", f"{user}-{space}".lower())


def main():
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("HF_TOKEN is empty", file=sys.stderr)
        return fail({
            "code": "TOKEN_MISSING",
            "reason": "The HF_TOKEN secret is empty or not set.",
            "fix": "Add a classic Write token as repo secret HF_TOKEN.",
            "message": "HF_TOKEN is empty",
        })
    space = os.environ.get("HF_SPACE", "").strip() or DEFAULT_SPACE
    api = HfApi(token=token)

    # A bad token fails at whoami; a token without repo-create rights fails at create_repo.
    # Report each separately, with HF's own words, no retry.
    try:
        user = api.whoami()["name"]
    except Exception as exc:
        return fail(diagnose(exc, "whoami"))
    repo_id = f"{user}/{space}"

    try:
        api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    except Exception as exc:
        verdict = diagnose(exc, "create_repo")
        if not verdict["ok"]:
            return fail(verdict)

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

    write_result(["STATUS=OK", f"LIVE_URL={url}"])
    print(f"HF_USER={user}")
    print(f"HF_SPACE_NAME={space}")
    print(f"LIVE_URL={url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
