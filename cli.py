import questionary
from nanoid import generate
from utils import require
from db import (
    LinkNotFoundError,
    create_link,
    delete_link,
    get_link,
    list_links,
    update_link,
)

FUNCTION_URL = require("FUNCTION_URL")


def pick_link(prompt: str) -> str | None:
    links = list_links()
    if not links:
        print("No links found.")
        return None
    choices = [
        questionary.Choice(title=f"{id}  {link.url}  {link.description}", value=id)
        for id, link in links
    ]
    return questionary.select(prompt, choices=choices).ask()


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _parse_url(url: str) -> str | None:
    url = url.strip().rstrip(".,;:!?")
    if url.rstrip("/") == FUNCTION_URL.rstrip("/"):
        print("Error: URL cannot point to the link tracker itself.")
        return None
    return url


def handle_list() -> None:
    links = list_links()
    if not links:
        print("No links found.")
        return

    headers = ("ID", "URL", "Description", "Clicks", "Created", "Last Opened")
    rows = [
        (
            id,
            _truncate(link.url, 40),
            _truncate(link.description, 30),
            str(link.clicks),
            link.created_at.strftime("%Y-%m-%d"),
            link.last_opened.strftime("%Y-%m-%d") if link.last_opened else "—",
        )
        for id, link in links
    ]

    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    sep = "  "

    def fmt(row: tuple) -> str:
        return sep.join(cell.ljust(w) for cell, w in zip(row, widths))

    print(fmt(headers))
    print(sep.join("─" * w for w in widths))
    for row in rows:
        print(fmt(row))


def handle_create() -> None:
    url = questionary.text("URL:").ask()
    description = questionary.text("Description:").ask()
    if not url or not description or not (url := _parse_url(url)):
        return
    custom_id = questionary.text("ID (leave empty to generate):").ask()
    id = custom_id.strip() if custom_id and custom_id.strip() else generate(size=8)
    create_link(id, url, description)
    print(f"Created {FUNCTION_URL}/{id}")


def handle_edit() -> None:
    id = pick_link("Select link to edit:")
    if not id:
        return
    try:
        link = get_link(id)
    except LinkNotFoundError:
        print(f"No link found with id {id}")
        return
    url = questionary.text("URL:", default=link.url).ask()
    description = questionary.text("Description:", default=link.description).ask()
    if url is None or description is None or not (url := _parse_url(url)):
        return
    update_link(id, url, description)
    print(f"Updated {id}")


def handle_delete() -> None:
    id = pick_link("Select link to delete:")
    if not id:
        return
    confirmed = questionary.confirm(f"Delete {id}?", default=False).ask()
    if confirmed:
        delete_link(id)
        print(f"Deleted {id}")


ACTIONS = {
    "List": handle_list,
    "Create": handle_create,
    "Edit": handle_edit,
    "Delete": handle_delete,
}


def main() -> None:
    action = questionary.select(
        "What do you want to do?", choices=list(ACTIONS.keys())
    ).ask()
    if action:
        ACTIONS[action]()


if __name__ == "__main__":
    main()
