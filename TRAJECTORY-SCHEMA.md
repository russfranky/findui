# FindUI Trajectory Schema: the capture spec

Status: BUILT as a spec, PROVEN in use by the prototype seed data (every
seed flow carries a trajectory record in this shape, and the smoke test
asserts the fields exist).

## Why this exists, in plain terms

A screenshot says what a screen looked like. A trajectory says what
happened: which state the user was in, what they tapped, where, and
whether it worked. Trajectories are the training and evaluation currency
for GUI agents, and they cannot be backfilled from an archive of
screenshots. Mobbin's MCP flow output has no per-step action, no
coordinates, no outcome label (PROVEN absent, REA brief section 5).
FindUI records trajectories at capture time, from the first flow.

## Record shape

One trajectory per recorded run of one flow.

| Field | Meaning |
|---|---|
| flow_id | The flow this run belongs to |
| recorded_by | Capture operator or capture automation id |
| app_version | App version during the run (also stamped on the flow payload) |
| captured_at | Date of the run (also stamped on the flow payload) |
| steps | Ordered list of step records, below |

## Step shape

| Field | Meaning |
|---|---|
| step_index | Position in the run, starting at 1 |
| state_id | The flow-graph state this step starts in |
| screenshot_ref | Reference to the captured screenshot for this state. Prototype uses placeholder references; production uses the stored capture file |
| elements | Visible actionable elements: label, role, and bbox as x_min, y_min, x_max, y_max on a 0 to 1000 relative scale |
| action | What left this state: type (tap, type, swipe, select, system, none), target_element, coordinates on the same 0 to 1000 scale, text for type actions |
| accessibility_snippet | Short accessibility tree excerpt for the state, where the platform exposes one. Text form is acceptable; full trees are stored as capture attachments in production |
| outcome_label | progress, success, or failure. The final step of a completed run is success; a run that dies at a step marks that step failure and stops |

## Rules

1. One action per step. If a state needs two actions to leave, it is two
   states in the graph.
2. Branch points in the flow graph must have at least one recorded run
   per branch before the flow is marked complete.
3. Failure runs are kept, not deleted. A failed KYC run with the failure
   step labeled is worth more for evaluation than a clean run.
4. Coordinates and bounding boxes use the 0 to 1000 relative scale
   everywhere, so records survive device size changes.
5. Contributor kits may include a trajectory only when the kit includes a
   flow, and the trajectory is authored by the contributor against their
   own kit, never recorded against a third party app.
6. Every field above is part of the data promised in trajectory licence
   deals (see pilot/LOI-TEMPLATE.md). A field the capture pipeline does
   not produce cannot be sold.

## Worked example

See the seed flows in findui_proto/seed_data.py. Example:
flow_nb_onboarding_kyc carries 5 trajectory steps from the welcome state
to the account ready state, each with element bounding boxes, the tap
action with coordinates, an accessibility snippet, and an outcome label,
ending in success.
