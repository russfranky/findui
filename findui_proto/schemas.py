"""Payload schemas for the FindUI prototype.

Field names for the parity layer mirror Mobbin's MCP output where Mobbin has
a field (id, name, app_name, platform, screen_patterns, ui_elements,
section_patterns, actions). Every other field is a FindUI addition, created
because BRIEF.md section 5 proved Mobbin's payload lacks it:

- states, edges, branch_points, entry_state, exit_states (flow graph)
- success_criteria (outcome data)
- app_version, captured_at (freshness data)
- trajectory (per-step capture record, see TRAJECTORY-SCHEMA.md)
- creator_id, creator_name, licence, attribution_url, pool_eligible,
  source_type (contributor supply layer, rights data)
"""

# Agent-context inputs accepted by every search tool, copied from Mobbin's
# schema idea (BRIEF.md section 4): the calling agent says what it is
# building and where the result goes next.
OUTPUT_DESTINATIONS = ["code", "design_tool", "doc", "reference_library", "chat", "other"]

# Fields every content item (screen, flow, section) carries.
COMMON_FIELDS = [
    "id",
    "app_name",
    "platform",
    "app_version",
    "captured_at",
    "findui_url",
    "source_type",       # captured_shipped | contributor_kit
    "creator_id",
    "creator_name",
    "licence",
    "attribution_url",
    "pool_eligible",
]

# The one licence for every contributor kit. Retrieval and eval use are
# the licence. Training is never permitted, for anyone, at any price,
# and no opt-in exists. Captured items are not kits and carry
# "findui_captured_reference" instead.
STANDARD_LICENCE = "findui-standard-v1"

# Fields a FindUI flow graph carries that a Mobbin filmstrip does not.
FLOW_GRAPH_FIELDS = [
    "states",            # nodes: state_id, screen_id, label, flags
    "edges",             # per-step action that leaves each state
    "branch_points",     # state_ids where the flow forks
    "entry_state",
    "exit_states",
    "success_criteria",  # list of {id, description, verification}
    "trajectory",        # capture record, see TRAJECTORY-SCHEMA.md
]

ATTRIBUTION_NOTICE = (
    "Cite findui_url for every item used. Items with an attribution_url "
    "must also credit the creator at that URL, per the platform licence."
)


def public_item(item):
    """Return a copy of a stored item safe to send to a caller."""
    return dict(item)
