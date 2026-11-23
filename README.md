# FindUI

FindUI is a library of UI flows for builders and AI agents. A designer publishes a UI flow that they made and own. A builder or an agent finds that flow through FindUI, uses it in a product, and the designer gets credited and paid for that use.

## The razor

FindUI is one library where a designer publishes a UI flow once, one upload, one licence, one page, and any AI agent can find it with one call and install it with one command, with the designer automatically credited in every payload and paid 70% of what that use earns.

## How the prototype works

This repo holds a working prototype, not a deployed product.

- MCP server: `findui_proto/server.py` is an MCP server built on FastMCP and the official mcp SDK. It serves tools over stdio when you run `run_server.py`. Tools search screens, flows, and sections, return single items, and support collections held in server memory.
- Flow graphs, not filmstrips: a flow in FindUI is a graph. States are nodes. Edges carry the per step action, the target element, and coordinates. Branch points, entry states, exit states, and success criteria are explicit fields. A filmstrip of screens in order does not carry any of that, so FindUI does not return filmstrips.
- Trajectory schema: `TRAJECTORY-SCHEMA.md` is the capture spec. One trajectory records one run of one flow: the state at each step, the screenshot reference, the visible elements with bounding boxes, the action taken with coordinates, an accessibility snippet, and an outcome label of progress, success, or failure. Coordinates use a 0 to 1000 relative scale. Every seed flow in `findui_proto/seed_data.py` carries a trajectory record in this shape.
- Payloads: screens, flows, and sections carry creator and licence fields where the item is a contributor kit. Every payload carries app version and captured date fields. Search in the prototype is token overlap ranking over a synthetic seed set. All seed data is synthetic. No third party screens, images, or text were copied.
- Sample kit: `packages/@findui/kit-paywall-pro/` is one sample contributor package, the Honest Paywall Kit by Devon Okafor. It shows the package shape: a presentational component, a `findui.json` manifest, `ATTRIBUTION.md`, and a `LICENSE` file. It is a local folder only. It has not been published.

Layout:

- `findui_proto/server.py`: the MCP tools
- `findui_proto/store.py`: data layer, ranked search, collections
- `findui_proto/schemas.py`: payload field definitions
- `findui_proto/seed_data.py`: the synthetic seed dataset
- `findui_proto/__init__.py`: package marker
- `run_server.py`: server entry point
- `requirements.txt`: Python dependencies
- `tests/smoke_test.py`: end to end smoke test
- `TRAJECTORY-SCHEMA.md`: the trajectory capture spec
- `packages/@findui/kit-paywall-pro/`: the sample contributor kit

## Run it

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python run_server.py

The server speaks MCP over stdio.

## Test it

    .venv/bin/python tests/smoke_test.py

Exit code 0 and a final `SMOKE TEST: PASS` line mean the run passed. The smoke test starts the server, calls every tool, and checks attribution fields, pool eligibility, the standard licence identifier, and that no training permission field appears in any payload.

## Licence

Every FindUI kit is published under one licence, the FindUI Standard Licence. There is no per kit licence choice. The full text is in `LICENSE` at the root of this repo.

In short: agents and tools may retrieve and cite a kit through FindUI, a kit may be included in FindUI eval sets and benchmarks, and builders may implement designs based on a kit in their own product. Attribution is a condition of the licence. Training is never permitted: no one may use a kit, its components, or its flow data to train or fine tune a model, at any price, and no opt in or separate agreement can grant it. No one may redistribute a kit itself as a standalone package or template outside FindUI channels. A creator may take a kit down through FindUI. Takedown stops new distribution, and uses already made under the licence stay licensed.

## Contributor economics

Contributors are paid from a royalty pool.

- Split: 70% of net attributed revenue goes to contributors as a pool, and FindUI keeps 30%.
- Division: the pool is divided pro rata by metered uses in the period.
- One use metering rule: a use is a kit's flow or screens included in an API/MCP response to a paying account.
- There are no weighted use types. A retrieval, a full flow pull, and an eval inclusion each count under that same rule. Free account calls never count, and npm downloads never count.
- Payouts: minimum payout threshold is $50, balances under the threshold roll forward, and payouts run monthly. See the contributor model in the project records for the full policy.

Attribution is automatic. Every API and MCP payload that returns a contributor item carries the creator id, creator name, licence, attribution URL, and kit version.

## Status: BUILT prototype, PROVEN running locally by its smoke test. Not deployed. Week 1 of the launch path.
