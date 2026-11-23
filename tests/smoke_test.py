#!/usr/bin/env python3
"""Smoke test for the FindUI prototype MCP server.

Starts the server as a subprocess over stdio with the official MCP Python
client, then asserts:
- tools/list returns the 8 parity tools plus find_from_draft
- search_screens returns versioned, attributed results
- search_flows returns a FLOW GRAPH (states, edges with per-step actions,
  branch points, entry and exit states, success criteria, trajectory),
  not a Mobbin-style filmstrip
- search_sections works
- find_from_draft returns a delta and labels itself a stub
- the collections write/read path works end to end

Run:  .venv/bin/python tests/smoke_test.py
Exit code 0 and a final "SMOKE TEST: PASS" line mean success.
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(HERE)

EXPECTED_TOOLS = {
    "search_screens", "search_flows", "search_sections",
    "list_collections", "get_collection_contents", "create_collection",
    "save_content", "add_comment", "find_from_draft",
}

FLOW_GRAPH_FIELDS = ["states", "edges", "branch_points", "entry_state",
                     "exit_states", "success_criteria", "trajectory",
                     "app_version", "captured_at"]


ALL_PAYLOADS = []

# The old model must never come back in a payload: no per-item revenue
# share, no licence opt-in matrix, no training permission of any kind.
FORBIDDEN_IN_PAYLOADS = ("revenue_share_bps", "licence_opt_ins",
                         "training_use", "training_opt_in")


def payload(result):
    if getattr(result, "structuredContent", None):
        data = result.structuredContent
    else:
        data = None
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                data = json.loads(text)
                break
    if data is None:
        raise AssertionError("tool result had no parseable payload")
    blob = json.dumps(data)
    for token in FORBIDDEN_IN_PAYLOADS:
        if token in blob:
            raise AssertionError(f"forbidden old-model field in payload: {token}")
    ALL_PAYLOADS.append(data)
    return data


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}: {label}")
    if not condition:
        raise AssertionError(label)


async def main():
    params = StdioServerParameters(
        command=os.path.join(PROTO, ".venv", "bin", "python"),
        args=[os.path.join(PROTO, "run_server.py")],
        cwd=PROTO,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            print("tools/list:", sorted(names))
            check("tools/list returns parity 8 plus find_from_draft",
                  names == EXPECTED_TOOLS)
            screens_tool = next(t for t in tools.tools if t.name == "search_screens")
            props = set(screens_tool.inputSchema.get("properties", {}))
            check("search_screens accepts agent-context inputs",
                  {"task_intent", "output_destination", "output_tool"} <= props)

            r = await session.call_tool("search_screens", {
                "query": "paywall trial subscribe restore purchase",
                "platform": "ios",
                "task_intent": "build a paywall for a timer app",
                "output_destination": "code", "output_tool": "prototype-test"})
            data = payload(r)
            check("search_screens returns results", len(data["screens"]) >= 1)
            first = data["screens"][0]
            check("screen carries patterns, elements, version, captured_at",
                  all(k in first for k in ("screen_patterns", "ui_elements",
                                           "app_version", "captured_at",
                                           "creator_id", "licence",
                                           "pool_eligible")))
            print("sample screen:", first["id"], first["app_name"],
                  first["screen_patterns"])

            r = await session.call_tool("search_screens", {
                "query": "honest paywall kit contributor", "platform": "ios"})
            data = payload(r)
            contrib = [s for s in data["screens"]
                       if s.get("source_type") == "contributor_kit"]
            check("contributor kit found by search", len(contrib) >= 1)
            c = contrib[0]
            check("contributor result carries attribution fields",
                  bool(c.get("attribution_url")) and bool(c.get("creator_name"))
                  and bool(c.get("creator_id")))
            check("contributor result is pool eligible under the standard licence",
                  c.get("pool_eligible") is True
                  and c.get("licence") == "findui-standard-v1")
            print("contributor screen:", c["id"], "by", c["creator_name"],
                  c["attribution_url"], c["licence"],
                  "pool_eligible:", c["pool_eligible"])

            r = await session.call_tool("search_flows", {
                "query": "bank account onboarding identity verification",
                "platform": "ios",
                "task_intent": "build fintech onboarding",
                "output_destination": "code", "output_tool": "prototype-test"})
            data = payload(r)
            check("search_flows returns results", len(data["flows"]) >= 1)
            flow = data["flows"][0]
            for field in FLOW_GRAPH_FIELDS:
                check(f"flow graph field present: {field}", field in flow)
            check("flow is not a filmstrip (no position-only screens array)",
                  "screens" not in flow)
            check("flow has at least one branch point",
                  len(flow["branch_points"]) >= 1)
            edge = flow["edges"][0]
            check("edge carries per-step action with target and coordinates",
                  "action" in edge and "target_element" in edge["action"]
                  and "coordinates" in edge["action"])
            check("entry state is a real state",
                  any(s["state_id"] == flow["entry_state"] for s in flow["states"]))
            check("exit states are real states",
                  all(any(s["state_id"] == e for s in flow["states"])
                      for e in flow["exit_states"]))
            check("success criteria have verification text",
                  all(c.get("verification") for c in flow["success_criteria"]))
            steps = flow["trajectory"]["steps"]
            check("trajectory has steps with bbox, action, outcome label",
                  len(steps) >= 2 and all(
                      "elements" in s and "action" in s and "outcome_label" in s
                      for s in steps)
                  and any(s["elements"] and "bbox" in s["elements"][0]
                          for s in steps))
            print("sample flow:", flow["id"], len(flow["states"]), "states,",
                  len(flow["edges"]), "edges, branches:",
                  flow["branch_points"])

            r = await session.call_tool("search_sections",
                                        {"query": "pricing tiers fees"})
            data = payload(r)
            check("search_sections returns results", len(data["sections"]) >= 1)
            check("section carries section_patterns and captured_at",
                  "section_patterns" in data["sections"][0]
                  and "captured_at" in data["sections"][0])

            r = await session.call_tool("find_from_draft", {
                "draft_description": "a paywall screen with a subscribe button and a price",
                "platform": "ios"})
            data = payload(r)
            check("find_from_draft labels itself a prototype stub",
                  data.get("prototype_stub") is True)
            check("find_from_draft returns nearest patterns and a delta",
                  len(data["nearest_screens"]) >= 1 and len(data["delta"]) >= 1)
            print("sample delta:", data["delta"][0]["delta"])

            r = await session.call_tool("create_collection", {
                "name": "Pilot verticals", "description": "smoke test collection"})
            col = payload(r)
            check("create_collection returns an id", bool(col.get("id")))
            cid = col["id"]

            r = await session.call_tool("save_content", {
                "items": [{"kind": "screen", "id": "scr_ft_paywall"},
                          {"kind": "flow", "id": "flow_ft_paywall_trial"}],
                "collection_id": cid})
            saved = payload(r)
            check("save_content succeeds", saved.get("ok") is True)

            r = await session.call_tool("add_comment", {
                "item_kind": "screen", "item_id": "scr_ft_paywall",
                "text": "Restore link placement is the lesson here."})
            commented = payload(r)
            check("add_comment succeeds", commented.get("ok") is True)

            r = await session.call_tool("get_collection_contents",
                                        {"collection_id": cid})
            contents = payload(r)
            ids = [i["id"] for i in contents["items"]]
            check("collection contents return the saved items",
                  "scr_ft_paywall" in ids and "flow_ft_paywall_trial" in ids)
            saved_screen = next(i for i in contents["items"]
                                if i["id"] == "scr_ft_paywall")
            check("comment is attached to the saved screen",
                  len(saved_screen.get("comments", [])) == 1)

            r = await session.call_tool("list_collections", {})
            listing = payload(r)
            mine = next(c for c in listing["collections"] if c["id"] == cid)
            check("list_collections counts the saved items",
                  mine["counts"]["ios_screens"] == 1
                  and mine["counts"]["ios_flows"] == 1)

            blob = json.dumps(ALL_PAYLOADS)
            check("no training permission field or value in any payload",
                  all(t not in blob for t in FORBIDDEN_IN_PAYLOADS)
                  and "opted_in" not in blob and "opt-in" not in blob)

    print("SMOKE TEST: PASS")


if __name__ == "__main__":
    asyncio.run(main())
