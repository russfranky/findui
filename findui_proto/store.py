"""Data layer for the FindUI prototype.

Ranked text search over the seed dataset, plus the collections saved layer
(create, save, list, contents, comment). Collections, saved content, and
comments persist in a SQLite database file (Python stdlib sqlite3, no new
dependencies), so they survive server restarts. Week 1 hardening,
2026-11-22: this replaces the earlier in-memory store, which lost all
collections on restart. Tool behavior and payload shapes are unchanged.

Database path: FINDUI_DB_PATH environment variable when set, otherwise
findui.db in this package's parent directory (the prototype root). The
database file is local prototype state, gitignored, never shipped.
"""

import os
import re
import sqlite3
import uuid

from . import seed_data
from .schemas import public_item

ALL_SAVED_ID = "all-saved"

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "findui.db")


def db_path():
    return os.environ.get("FINDUI_DB_PATH") or DEFAULT_DB_PATH


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _haystack(item):
    parts = [item.get("name", ""), item.get("app_name", ""), item.get("vertical", "")]
    for key in ("screen_patterns", "ui_elements", "section_patterns", "actions"):
        parts.extend(item.get(key) or [])
    return _tokens(" ".join(parts))


def score_item(query, item):
    q = _tokens(query)
    if not q:
        return 0
    hay = _haystack(item)
    overlap = len(q & hay)
    # Bonus when the query names the app or a full pattern phrase.
    phrase_bonus = 2 if query.lower() in (item.get("name", "").lower()) else 0
    return overlap + phrase_bonus


def search(kind, query, platform=None, limit=10, exclude_ids=None):
    pool = {"screen": seed_data.SCREENS, "flow": seed_data.FLOWS,
            "section": seed_data.SECTIONS}[kind]
    exclude = set(exclude_ids or [])
    scored = []
    for item in pool:
        if item["id"] in exclude:
            continue
        if platform and kind != "section" and item.get("platform") != platform:
            continue
        s = score_item(query, item)
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [public_item(item) for _, item in scored[:limit]]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 0,
    created_seq INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS collection_items (
    collection_id TEXT NOT NULL REFERENCES collections(id),
    kind TEXT NOT NULL,
    item_id TEXT NOT NULL,
    saved_seq INTEGER NOT NULL,
    PRIMARY KEY (collection_id, item_id)
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    text TEXT NOT NULL
);
"""


class CollectionStore:
    """SQLite-backed collections store.

    Opening a store on an existing database file reads what earlier
    processes wrote: that is the persistence the restart test proves.
    """

    def __init__(self, path=None):
        self.path = path or db_path()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        with self.conn:
            row = self.conn.execute(
                "SELECT id FROM collections WHERE id = ?", (ALL_SAVED_ID,)).fetchone()
            if row is None:
                self._insert_collection(ALL_SAVED_ID, "All saved",
                                        "Everything saved without a collection", True)

    def close(self):
        self.conn.close()

    # -- internal helpers ---------------------------------------------------

    def _next_seq(self, table, column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({column}), 0) + 1 AS n FROM {table}").fetchone()
        return row["n"]

    def _insert_collection(self, cid, name, description, is_public):
        self.conn.execute(
            "INSERT INTO collections (id, name, description, is_public, created_seq)"
            " VALUES (?, ?, ?, ?, ?)",
            (cid, name, description, 1 if is_public else 0,
             self._next_seq("collections", "created_seq")))

    def _get_collection(self, cid):
        return self.conn.execute(
            "SELECT * FROM collections WHERE id = ?", (cid,)).fetchone()

    def _items_of(self, cid):
        rows = self.conn.execute(
            "SELECT kind, item_id FROM collection_items WHERE collection_id = ?"
            " ORDER BY saved_seq ASC", (cid,)).fetchall()
        return [{"kind": r["kind"], "id": r["item_id"]} for r in rows]

    def _describe(self, row):
        counts = {"ios_screens": 0, "ios_flows": 0, "web_screens": 0,
                  "web_flows": 0, "website_sections": 0}
        for ref in self._items_of(row["id"]):
            item = seed_data.ALL_ITEMS.get(ref["id"])
            if not item:
                continue
            if ref["kind"] == "section":
                counts["website_sections"] += 1
            else:
                key = f"{item['platform']}_{ref['kind']}s"
                if key in counts:
                    counts[key] += 1
        return {"id": row["id"], "name": row["name"],
                "description": row["description"],
                "is_public": bool(row["is_public"]),
                "findui_url": f"https://findui.com/collections/{row['id']}",
                "counts": counts}

    def _comments_for(self, item_id):
        rows = self.conn.execute(
            "SELECT item_id, text FROM comments WHERE item_id = ? ORDER BY id ASC",
            (item_id,)).fetchall()
        return [{"item_id": r["item_id"], "text": r["text"]} for r in rows]

    # -- public API (same shapes as the in-memory store) --------------------

    def create(self, name, description="", is_public=False):
        cid = "col_" + uuid.uuid4().hex[:10]
        with self.conn:
            self._insert_collection(cid, name, description, bool(is_public))
        return self._describe(self._get_collection(cid))

    def list_all(self):
        rows = self.conn.execute(
            "SELECT * FROM collections ORDER BY created_seq ASC").fetchall()
        return [self._describe(r) for r in rows]

    def save(self, items, collection_id=None):
        """All-or-nothing save, mirroring Mobbin's save_content contract."""
        for ref in items:
            if ref["id"] not in seed_data.ALL_ITEMS:
                return {"ok": False, "error": f"unknown item id: {ref['id']}"}
        target_id = collection_id or ALL_SAVED_ID
        if self._get_collection(target_id) is None:
            return {"ok": False, "error": f"unknown collection: {collection_id}"}
        with self.conn:
            for ref in items:
                self.conn.execute(
                    "INSERT OR IGNORE INTO collection_items"
                    " (collection_id, kind, item_id, saved_seq) VALUES (?, ?, ?, ?)",
                    (target_id, ref["kind"], ref["id"],
                     self._next_seq("collection_items", "saved_seq")))
        return {"ok": True, "collection_id": target_id,
                "saved": [r["id"] for r in items]}

    def contents(self, collection_id, kind=None, page=1, limit=20):
        if self._get_collection(collection_id) is None:
            return {"ok": False, "error": f"unknown collection: {collection_id}"}
        refs = [r for r in reversed(self._items_of(collection_id))
                if kind is None or r["kind"] == kind]  # newest save first
        start = (page - 1) * limit
        page_refs = refs[start:start + limit]
        items = []
        for ref in page_refs:
            item = public_item(seed_data.ALL_ITEMS[ref["id"]])
            item["comments"] = self._comments_for(ref["id"])
            items.append(item)
        return {"collection_id": collection_id, "page": page,
                "has_next_page": start + limit < len(refs), "items": items}

    def add_comment(self, item_kind, item_id, text):
        if item_id not in seed_data.ALL_ITEMS:
            return {"ok": False, "error": f"unknown item id: {item_id}"}
        # Mobbin behavior: an unsaved item is saved to All saved first.
        saved = self.save([{"kind": item_kind, "id": item_id}], ALL_SAVED_ID)
        comment = {"item_id": item_id, "text": text}
        with self.conn:
            self.conn.execute(
                "INSERT INTO comments (item_id, text) VALUES (?, ?)",
                (item_id, text))
        return {"ok": True, "saved_first": saved.get("ok", False),
                "comment": comment}
