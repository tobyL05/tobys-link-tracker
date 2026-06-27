import threading
import functions_framework
import flask
import httpx
from utils import is_bot, require
from db import LinkNotFoundError, get_link, get_link_with_update

DISCORD_WEBHOOK = require("DISCORD_WEBHOOK")
DISCORD_USER = require("DISCORD_USER")
DEFAULT_URL = require("DEFAULT_URL")


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
    notify = notify_async if not bot else lambda _: None
    fetch = get_link if bot else get_link_with_update

    if bot:
        print("Bot detected.")

    try:
        link = fetch(id)
    except LinkNotFoundError:
        notify(f"Failed open: unknown link `{id}`")
        print(f"Link not found: {id}")
        return redirect(DEFAULT_URL)

    if not link.url.startswith("https://"):
        notify(f"Failed open: invalid URL for `{id}`: {link.url}")
        print(f"Invalid URL for id: {id}. URL: {link.url}")
        return redirect(DEFAULT_URL)

    notify(link.description)
    return redirect(link.url)
