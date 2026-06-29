import threading
import functions_framework
import flask
import httpx
from datetime import datetime
from utils import is_bot, require, validate_url
from db import LinkNotFoundError, get_link, get_link_with_update

DISCORD_WEBHOOK = require("DISCORD_WEBHOOK")
DISCORD_USER = require("DISCORD_USER")
DEFAULT_URL = require("DEFAULT_URL")
TEST_TOKEN = require("TEST_TOKEN")
FUNCTION_URL = require("FUNCTION_URL")


def _notify(message: str) -> None:
    httpx.post(
        DISCORD_WEBHOOK,
        json={"content": f"<@{DISCORD_USER}> {message}"},
    )


def notify_async(message: str) -> None:
    print("Notifying...")
    threading.Thread(target=_notify, args=(message,), daemon=True).start()


def redirect(url: str):
    return flask.redirect(url, code=302)


@functions_framework.http
def main(request: flask.Request):
    id = request.path.strip("/").rstrip(".,;:!?")

    if not id:
        print("No ID detected. Returning default URL.")
        return redirect(DEFAULT_URL)

    bot = is_bot(request)
    test = request.headers.get("X-Test-Token") == TEST_TOKEN
    silent = bot or test
    notify = notify_async if not silent else lambda _: None
    fetch = get_link if silent else get_link_with_update

    if bot:
        print("Bot detected.")
    if test:
        print("Test client detected.")

    try:
        link = fetch(id)
    except LinkNotFoundError:
        notify(f"Failed open: unknown link `{id}`")
        print(f"Link not found: {id}")
        return redirect(DEFAULT_URL)

    if error := validate_url(link.url, FUNCTION_URL):
        notify(f"Failed open: {error} for `{id}`")
        print(f"Invalid link {id}: {error}")
        return redirect(DEFAULT_URL)

    notify(f"[{datetime.now()}] {link.description}")
    return redirect(link.url)
