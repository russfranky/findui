#!/usr/bin/env python3
"""Persistence test for the FindUI prototype SQLite store.

Proves collections, saved content, and comments survive a restart:
phase 1 opens a store on a fresh temp database, creates a collection,
saves content, adds a comment, and closes. Phase 2 opens a NEW store
object on the same database file (a fresh process in phase 3 terms) and
reads everything back. Phase 3 repeats the read in a separate Python
process against the same file, which is a real server restart.

Run:  .venv/bin/python tests/persistence_test.py
Exit code 0 and a final "PERSISTENCE TEST: PASS" line mean success.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(HERE)
sys.path.insert(0, PROTO)

from findui_proto.store import CollectionStore  # noqa: E402

COMMENT_TEXT = "Persistence check comment, week 1."
COLLECTION_NAME = "Week 1 persistence check"


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}: {label}")
    if not condition:
        raise AssertionError(label)


def phase_write(path):
    store = CollectionStore(path)
    col = store.create(COLLECTION_NAME, "written before the restart")
    cid = col["id"]
    saved = store.save(
        [{"kind": "screen", "id": "scr_ft_paywall"},
         {"kind": "flow", "id": "flow_ft_paywall_trial"}],
        collection_id=cid)
    check("phase 1 save_content succeeds", saved.get("ok") is True)
    commented = store.add_comment("screen", "scr_ft_paywall", COMMENT_TEXT)
    check("phase 1 add_comment succeeds", commented.get("ok") is True)
    store.close()
    return cid


def phase_read(path, cid, label_prefix):
    store = CollectionStore(path)
    listing = store.list_all()
    mine = [c for c in listing if c["id"] == cid]
    check(f"{label_prefix}: collection survives", len(mine) == 1)
    check(f"{label_prefix}: collection name intact",
          mine[0]["name"] == COLLECTION_NAME)
    contents = store.contents(cid)
    ids = [i["id"] for i in contents["items"]]
    check(f"{label_prefix}: saved items survive",
          "scr_ft_paywall" in ids and "flow_ft_paywall_trial" in ids)
    screen = next(i for i in contents["items"] if i["id"] == "scr_ft_paywall")
    texts = [c["text"] for c in screen.get("comments", [])]
    check(f"{label_prefix}: comment survives", COMMENT_TEXT in texts)
    check(f"{label_prefix}: counts intact",
          mine[0]["counts"]["ios_screens"] == 1
          and mine[0]["counts"]["ios_flows"] == 1)
    store.close()


READER_SNIPPET = """
import sys
sys.path.insert(0, {proto!r})
from findui_proto.store import CollectionStore
store = CollectionStore({path!r})
contents = store.contents({cid!r})
ids = [i["id"] for i in contents["items"]]
assert "scr_ft_paywall" in ids and "flow_ft_paywall_trial" in ids, ids
screen = next(i for i in contents["items"] if i["id"] == "scr_ft_paywall")
assert any(c["text"] == {comment!r} for c in screen.get("comments", [])), screen
print("subprocess read-back OK:", ids)
"""


def main():
    tmp = tempfile.mkdtemp(prefix="findui-persist-")
    path = os.path.join(tmp, "findui-test.db")
    cid = phase_write(path)
    print("phase 1 wrote collection:", cid)

    phase_read(path, cid, "phase 2 (new store object, same process)")

    snippet = READER_SNIPPET.format(proto=PROTO, path=path, cid=cid,
                                    comment=COMMENT_TEXT)
    proc = subprocess.run([sys.executable, "-c", snippet],
                          capture_output=True, text=True)
    print(proc.stdout.strip())
    check("phase 3 (separate process, real restart) read-back",
          proc.returncode == 0)

    print("PERSISTENCE TEST: PASS")


if __name__ == "__main__":
    main()
