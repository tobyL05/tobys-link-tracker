import os
import flask
from unittest.mock import patch, MagicMock
from flask import Flask

os.environ.setdefault("WEBHOOK_URL", "https://hooks.example.com")
os.environ.setdefault("DEFAULT_URL", "https://default.example.com")
os.environ.setdefault("FUNCTION_URL", "https://function.example.com")
os.environ.setdefault("DATABASE_NAME", "test-db")
os.environ.setdefault("COLLECTION_NAME", "links")

from main import main
from db import LinkNotFoundError

DEFAULT_URL = os.environ["DEFAULT_URL"]
_app = Flask(__name__)


def _call(path="/abc", params=None, ua=None):
    headers = {"User-Agent": ua} if ua else {}
    with _app.test_request_context(path, query_string=params or {}, headers=headers):
        return main(flask.request)


def _link(url="https://example.com", label="My Link"):
    link = MagicMock()
    link.url = url
    link.label = label
    return link


@patch("main.notify_async")
@patch("main.get_link_with_update")
@patch("main.get_link")
class TestNormal:
    def test_increments_clicks(self, get_link, get_link_with_update, notify_async):
        get_link_with_update.return_value = _link()
        _call("/abc")
        get_link_with_update.assert_called_once_with("abc")
        get_link.assert_not_called()

    def test_notification_has_no_prefix(
        self, get_link, get_link_with_update, notify_async
    ):
        get_link_with_update.return_value = _link(label="My Link")
        _call("/abc")
        msg = notify_async.call_args[0][0]
        assert "[PREVIEW]" not in msg
        assert "My Link" in msg


@patch("main.notify_async")
@patch("main.get_link_with_update")
@patch("main.get_link")
class TestPreview:
    def test_does_not_increment_clicks(
        self, get_link, get_link_with_update, notify_async
    ):
        get_link.return_value = _link()
        _call("/abc", params={"preview": "true"})
        get_link.assert_called_once_with("abc")
        get_link_with_update.assert_not_called()

    def test_notification_has_prefix(
        self, get_link, get_link_with_update, notify_async
    ):
        get_link.return_value = _link(label="My Link")
        _call("/abc", params={"preview": "true"})
        msg = notify_async.call_args[0][0]
        assert msg.startswith("[PREVIEW]")
        assert "My Link" in msg

    def test_case_insensitive(self, get_link, get_link_with_update, notify_async):
        get_link.return_value = _link()
        _call("/abc", params={"preview": "True"})
        get_link.assert_called_once_with("abc")
        get_link_with_update.assert_not_called()
        msg = notify_async.call_args[0][0]
        assert msg.startswith("[PREVIEW]")


@patch("main.notify_async")
@patch("main.get_link_with_update")
@patch("main.get_link")
class TestBot:
    def test_does_not_increment_clicks(
        self, get_link, get_link_with_update, notify_async
    ):
        get_link.return_value = _link()
        _call("/abc", ua="LinkedInBot/1.0")
        get_link.assert_called_once_with("abc")
        get_link_with_update.assert_not_called()

    def test_does_not_notify(self, get_link, get_link_with_update, notify_async):
        get_link.return_value = _link()
        _call("/abc", ua="LinkedInBot/1.0")
        notify_async.assert_not_called()


@patch("main.notify_async")
@patch("main.get_link_with_update")
@patch("main.get_link")
class TestRedirects:
    def test_empty_path_redirects_to_default(
        self, get_link, get_link_with_update, notify_async
    ):
        response = _call("/")
        assert response.status_code == 302
        assert response.headers["Location"] == DEFAULT_URL

    def test_unknown_id_redirects_to_default(
        self, get_link, get_link_with_update, notify_async
    ):
        get_link_with_update.side_effect = LinkNotFoundError("abc")
        response = _call("/abc")
        assert response.status_code == 302
        assert response.headers["Location"] == DEFAULT_URL
