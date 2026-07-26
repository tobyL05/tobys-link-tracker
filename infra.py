"""Provision the GCP infrastructure this project needs: a Firestore database
and the link-tracker Cloud Function, then install the `links` CLI. Requires
the gcloud CLI, authenticated (`gcloud auth login`) with billing enabled on
the target project.

Run with `uv run infra.py --apply` (omit `--apply` for a dry run).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import questionary
from rich.console import Console

from utils import ENV_PATH

console = Console()

DRY_RUN = True

REQUIRED_APIS = (
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "eventarc.googleapis.com",
)

ENV_EXAMPLE_PATH = Path(__file__).parent / ".env.example"


def run(*args: str, capture: bool = False) -> str:
    if DRY_RUN and not capture:
        print(f"[dry-run] would run: {' '.join(args)}")
        return ""
    result = subprocess.run(args, text=True, capture_output=capture)
    if result.returncode != 0:
        if capture:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
        sys.exit(f"Command failed: {' '.join(args)}")
    return result.stdout.strip() if capture else ""


def check_gcloud() -> None:
    with console.status("Checking gcloud CLI is installed..."):
        gcloud_found = (
            subprocess.run(["which", "gcloud"], capture_output=True).returncode == 0
        )
    if not gcloud_found:
        sys.exit(
            "gcloud CLI not found. Install it: https://cloud.google.com/sdk/docs/install"
        )
    console.print("[green]✓[/green] gcloud CLI is installed")

    with console.status("Checking gcloud authentication..."):
        account = run("gcloud", "config", "get-value", "account", capture=True)
    if not account or account == "(unset)":
        sys.exit("Not logged in. Run `gcloud auth login` first.")
    console.print(f"[green]✓[/green] Logged in as {account}")


def pick_project() -> str:
    current = run("gcloud", "config", "get-value", "project", capture=True)
    default = current if current and current != "(unset)" else None
    project = questionary.text("GCP project ID:", default=default or "").ask()
    if not project:
        sys.exit("A project ID is required.")
    run("gcloud", "config", "set", "project", project)
    return project


def enable_apis(project: str) -> None:
    print("Enabling required APIs (this can take a minute)...")
    run("gcloud", "services", "enable", *REQUIRED_APIS, "--project", project)


def firestore_database_exists(project: str, database: str) -> bool:
    result = subprocess.run(
        [
            "gcloud",
            "firestore",
            "databases",
            "describe",
            f"--database={database}",
            "--project",
            project,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_firestore_database(project: str, database: str, region: str) -> None:
    if firestore_database_exists(project, database):
        print(f"Firestore database '{database}' already exists, skipping.")
        return
    print(f"Creating Firestore database '{database}' in {region}...")
    run(
        "gcloud",
        "firestore",
        "databases",
        "create",
        f"--database={database}",
        f"--location={region}",
        "--type=firestore-native",
        "--project",
        project,
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load_env_defaults() -> dict[str, str]:
    defaults: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                defaults[key.strip()] = _unquote(value.strip())
    return defaults


def env_keys() -> list[str]:
    keys = []
    for line in ENV_EXAMPLE_PATH.read_text().splitlines():
        if "=" in line:
            keys.append(line.partition("=")[0].strip())
    return keys


def ensure_env_vars(hints: dict[str, str]) -> dict[str, str]:
    keys = env_keys()
    values = load_env_defaults()
    missing = [key for key in keys if not values.get(key)]
    if missing:
        details = "\n".join(
            f"  {key}{f' (e.g. {hints[key]})' if key in hints else ''}"
            for key in missing
        )
        sys.exit(
            f"Missing values in {ENV_PATH} for:\n{details}\nEdit {ENV_PATH} and re-run this script."
        )

    return {key: values[key] for key in keys}


def function_exists(project: str, region: str, name: str) -> bool:
    result = subprocess.run(
        [
            "gcloud",
            "functions",
            "describe",
            name,
            "--gen2",
            f"--region={region}",
            "--project",
            project,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def deploy_function(
    project: str, region: str, name: str, values: dict[str, str]
) -> None:
    if function_exists(project, region, name):
        print(f"Cloud Function '{name}' already exists in {region}.")
        prompt = f"Overwrite '{name}' with this config?"
    else:
        prompt = f"Deploy Cloud Function '{name}' now?"

    if not questionary.confirm(prompt, default=True).ask():
        return
    print("Exporting requirements.txt...")
    run("uv", "export", "--no-hashes", "-o", "requirements.txt")
    env_vars = ",".join(f"{k}={v}" for k, v in values.items())
    print(f"Deploying '{name}'...")
    run(
        "gcloud",
        "functions",
        "deploy",
        name,
        "--gen2",
        "--runtime=python314",
        "--entry-point=main",
        "--source=.",
        f"--region={region}",
        "--project",
        project,
        "--trigger-http",
        "--allow-unauthenticated",
        f"--set-env-vars={env_vars}",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="infra.py", description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create/modify resources. Without this flag, runs as a dry run.",
    )
    return parser.parse_args()


def check_prereqs() -> None:
    with console.status("Checking .env exists..."):
        env_found = ENV_PATH.exists()
    if not env_found:
        sys.exit(
            f"{ENV_PATH} not found. Create it (see .env.example) and re-run this script."
        )
    console.print(f"[green]✓[/green] Found {ENV_PATH}")

    check_gcloud()


def main() -> None:
    global DRY_RUN
    DRY_RUN = not parse_args().apply

    print(
        "Toby's Link Tracker infrastructure setup"
        + (" (dry run — pass --apply to make real changes)" if DRY_RUN else "")
        + "\n"
    )
    check_prereqs()

    project = pick_project()
    region = questionary.text("Region:", default="us-central1").ask()
    function_name = questionary.text(
        "Cloud Function name:", default="link-tracker"
    ).ask()

    enable_apis(project)

    predicted_url = f"https://{region}-{project}.cloudfunctions.net/{function_name}"
    values = ensure_env_vars({"FUNCTION_URL": predicted_url})

    create_firestore_database(project, values["DATABASE_NAME"], region)
    deploy_function(project, region, function_name, values)
    install_cli()

    print("\nSetup complete.")
    if values["FUNCTION_URL"] != predicted_url:
        print(
            "FUNCTION_URL is set to a custom domain — make sure the domain mapping "
            f"(GCP > Cloud Functions > Domain Mapping) points it at '{function_name}'."
        )


def install_cli() -> None:
    print("Installing the `links` CLI...")
    run("uv", "tool", "install", "--editable", ".")


if __name__ == "__main__":
    main()
