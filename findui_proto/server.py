"""FindUI MCP server (prototype).

Parity layer: the 8 Mobbin tool shapes from BRIEF.md section 4, including
the agent-context inputs task_intent, output_destination, output_tool on
every search call.

Innovation layer, in the payloads:
- search_flows returns a flow graph (states, edges with per-step actions,
  branch points, entry and exit states, success criteria), not a filmstrip.
- Every payload carries app_version and captured_at.
- Contributor items carry creator and licence fields through every result.
- find_from_draft: PROTOTYPE STUB. Text description in, nearest shipped
  patterns plus a written delta out. No image model. Labeled as a stub in
  its tool description and in every response it returns.
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import store as store_module
from .schemas import ATTRIBUTION_NOTICE

mcp = FastMCP("findui-prototype")
_store = store_module.CollectionStore()


def _context(task_intent, output_destination, output_tool):
    return {"task_intent": task_intent, "output_destination": output_destination,
            "output_tool": output_tool}


@mcp.tool()
def search_screens(query: str, platform: str, mode: str = "deep",
                   exclude_screen_ids: Optional[list] = None, limit: int = 10,
                   task_intent: Optional[str] = None,
                   output_destination: Optional[str] = None,
                   output_tool: Optional[str] = None) -> dict:
    """Search single UI screens by plain language query. Platform is its own
    parameter (ios or web); do not put it in the query. Each result carries
    screen_patterns, ui_elements, app_version, captured_at, and, for
    contributor kits, creator and licence attribution fields."""
    screens = store_module.search("screen", query, platform=platform,
                                  limit=limit, exclude_ids=exclude_screen_ids)
    return {"query": query, "mode": mode, "screens": screens,
            "agent_context": _context(task_intent, output_destination, output_tool),
            "attribution_notice": ATTRIBUTION_NOTICE}


@mcp.tool()
def search_flows(query: str, platform: str, limit: int = 10, page: int = 1,
                 task_intent: Optional[str] = None,
                 output_destination: Optional[str] = None,
                 output_tool: Optional[str] = None) -> dict:
    """Search multi-step user journeys. FindUI returns each flow as a graph:
    states, edges carrying the per-step action that leaves each state,
    branch_points, entry_state, exit_states, success_criteria, a trajectory
    record, app_version and captured_at. This is the payload Mobbin's
    filmstrip (screen_id, image_url, position) cannot express."""
    flows = store_module.search("flow", query, platform=platform, limit=limit)
    start = (page - 1) * limit
    return {"query": query, "flows": flows[start:start + limit], "page": page,
            "has_next_page": start + limit < len(flows),
            "agent_context": _context(task_intent, output_destination, output_tool),
            "attribution_notice": ATTRIBUTION_NOTICE}


@mcp.tool()
def search_sections(query: str, limit: int = 10, page: int = 1,
                    task_intent: Optional[str] = None,
                    output_destination: Optional[str] = None,
                    output_tool: Optional[str] = None) -> dict:
    """Search website sections (pricing tiers, FAQ, trust strips). Sections
    have no platform parameter. Each result carries section_patterns,
    ui_elements, app_version, captured_at, and attribution fields."""
    sections = store_module.search("section", query, limit=limit)
    start = (page - 1) * limit
    return {"query": query, "sections": sections[start:start + limit], "page": page,
            "has_next_page": start + limit < len(sections),
            "agent_context": _context(task_intent, output_destination, output_tool),
            "attribution_notice": ATTRIBUTION_NOTICE}


@mcp.tool()
def find_from_draft(draft_description: str, platform: Optional[str] = None,
                    limit: int = 5, task_intent: Optional[str] = None,
                    output_destination: Optional[str] = None,
                    output_tool: Optional[str] = None) -> dict:
    """PROTOTYPE STUB. Describe a draft or generated screen in words and get
    the nearest shipped patterns plus a written delta: elements and patterns
    the shipped references include that the draft description never mentions.
    Text only, no image model. The production version takes an image; this
    stub exists to prove the payload shape."""
    import re
    draft_tokens = set(re.findall(r"[a-z0-9]+", draft_description.lower()))
    screens = store_module.search("screen", draft_description,
                                  platform=platform, limit=limit)
    flows = store_module.search("flow", draft_description,
                                platform=platform, limit=3)
    deltas = []
    for item in screens + flows:
        for element in item.get("ui_elements") or []:
            element_tokens = set(re.findall(r"[a-z0-9]+", element.lower()))
            if not (element_tokens & draft_tokens):
                deltas.append({
                    "reference_id": item["id"],
                    "reference_name": item["name"],
                    "missing_element": element,
                    "delta": (f"Shipped reference '{item['name']}' includes "
                              f"'{element}'; the draft description does not mention it."),
                })
        for pattern in item.get("screen_patterns") or []:
            pattern_tokens = set(re.findall(r"[a-z0-9]+", pattern.lower()))
            if not (pattern_tokens & draft_tokens):
                deltas.append({
                    "reference_id": item["id"],
                    "reference_name": item["name"],
                    "missing_pattern": pattern,
                    "delta": (f"Shipped reference '{item['name']}' follows the "
                              f"'{pattern}' pattern; the draft does not describe it."),
                })
    return {"prototype_stub": True,
            "stub_note": "Text-only prototype stub. No image input, no image model.",
            "draft_description": draft_description,
            "nearest_screens": screens, "nearest_flows": flows,
            "delta": deltas,
            "agent_context": _context(task_intent, output_destination, output_tool),
            "attribution_notice": ATTRIBUTION_NOTICE}


@mcp.tool()
def list_collections() -> dict:
    """List All saved plus every collection, with per-kind counts."""
    return {"collections": _store.list_all()}


@mcp.tool()
def create_collection(name: str, description: str = "",
                      is_public: bool = False) -> dict:
    """Create a collection. Private by default, like Mobbin."""
    return _store.create(name, description, is_public)


@mcp.tool()
def get_collection_contents(collection_id: str, kind: Optional[str] = None,
                            page: int = 1, limit: int = 20) -> dict:
    """Page items from one collection, newest save first. Items carry their
    comments and their creator and licence attribution fields."""
    return _store.contents(collection_id, kind=kind, page=page, limit=limit)


@mcp.tool()
def save_content(items: list, collection_id: Optional[str] = None) -> dict:
    """Save items into a collection, or into All saved when no collection is
    given. Items are {kind, id} pairs. All-or-nothing: one unknown id fails
    the whole call, mirroring Mobbin."""
    return _store.save(items, collection_id)


@mcp.tool()
def add_comment(item_kind: str, item_id: str, text: str) -> dict:
    """Comment on a screen, flow, or section. An unsaved item is saved to
    All saved first, mirroring Mobbin."""
    return _store.add_comment(item_kind, item_id, text)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
