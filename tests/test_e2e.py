import httpx


def test_empty_path_redirects_to_default(client: httpx.Client, default_url: str):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["location"] == default_url


def test_unknown_id_redirects_to_default(client: httpx.Client, default_url: str):
    response = client.get("/this-id-does-not-exist")
    assert response.status_code == 302
    assert response.headers["location"] == default_url


def test_valid_link_redirects(client: httpx.Client):
    response = client.get("/e2e-test-link")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


def test_bot_ua_does_not_count(client: httpx.Client):
    response = client.get("/test", headers={"User-Agent": "LinkedInBot/1.0"})
    assert response.status_code == 302
