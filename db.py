from google.cloud import firestore
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from utils import require

DATABASE_NAME = require("DATABASE_NAME")
COLLECTION_NAME = require("COLLECTION_NAME")

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(database=DATABASE_NAME).collection(COLLECTION_NAME)
    return _db


class LinkNotFoundError(Exception):
    pass


@dataclass
class Link:
    url: str
    description: str
    clicks: int
    created_at: datetime
    last_opened: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Link":
        return cls(
            url=data["url"],
            description=data["description"],
            clicks=data["clicks"],
            created_at=data["created_at"],
            last_opened=data["last_opened"],
        )

    def __repr__(self) -> str:
        return str(asdict(self))


def _fetch(id: str) -> firestore.DocumentSnapshot:
    try:
        doc: firestore.DocumentSnapshot = _get_db().document(id).get()  # type: ignore[assignment]
        if not doc.exists:
            raise LinkNotFoundError(id)
    except Exception as e:
        print(f"Exception occurred fetching document {id}: {e}")
        raise LinkNotFoundError(id)
    return doc


def get_link(id: str) -> Link:
    doc = _fetch(id)
    data = doc.to_dict()
    assert data is not None
    return Link.from_dict(data)


def get_link_with_update(id: str) -> Link:
    link = get_link(id)
    _get_db().document(id).update(
        {"clicks": firestore.Increment(1), "last_opened": firestore.SERVER_TIMESTAMP}
    )
    return link


def list_links() -> list[tuple[str, Link]]:
    db = _get_db()
    docs = db.stream()
    return [(doc.id, Link.from_dict(doc.to_dict())) for doc in docs if doc.to_dict()]  # type: ignore[union-attr]


def delete_link(id: str) -> None:
    _fetch(id)
    _get_db().document(id).delete()


def update_url(id: str, url) -> None:
    _get_db().document(id).update({"url": url})


def update_description(id: str, description: str) -> None:
    _get_db().document(id).update({"description": description})


def create_link(id: str, url: str, description: str) -> None:
    _get_db().document(id).set(
        {
            "url": url,
            "description": description,
            "clicks": 0,
            "created_at": datetime.now(timezone.utc),
            "last_opened": None,
        }
    )
