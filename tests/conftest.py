import os
import pytest
import httpx
from dotenv import load_dotenv


def pytest_addoption(parser):
    parser.addoption("--env", choices=["prod", "staging"], required=False)


@pytest.fixture(scope="session", autouse=True)
def load_env(request):
    env = request.config.getoption("--env")
    if env is None:
        return
    env_file = ".env" if env == "prod" else ".env.staging"
    load_dotenv(env_file)


@pytest.fixture(scope="session")
def client(load_env):
    with httpx.Client(
        base_url=os.environ["FUNCTION_URL"],
        follow_redirects=False,
    ) as c:
        yield c


@pytest.fixture(scope="session")
def default_url(load_env):
    return os.environ["DEFAULT_URL"]
