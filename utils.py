import os
import flask
from dotenv import load_dotenv

load_dotenv()

BOT_UA_PATTERNS = (
    "linkedinbot",
    "slackbot",
    "discordbot",
    "twitterbot",
    "facebookexternalhit",
    "claude-user",
)


def require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def is_bot(request: flask.Request) -> bool:
    ua = request.headers.get("User-Agent", "").lower()
    return any(pattern in ua for pattern in BOT_UA_PATTERNS)
