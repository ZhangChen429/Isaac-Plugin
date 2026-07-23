# Hello Isaac UI

Small Isaac Sim extension that adds a `Window > Hello Isaac UI` tool window.

## Features

- Create a `PhysicsRevoluteJoint` under the selected `group*` Xform.
- Choose the RevoluteJoint axis from `X`, `Y`, or `Z` before creation.
- Apply `PhysicsRigidBodyAPI` to the selected `group*` Xform.
- Set RevoluteJoint `body0` to `group_0`; if `group_0` is missing, use the top-level root Xform.
- Set RevoluteJoint `body1` to the selected Xform.
- Add an `angularDrive` API to the RevoluteJoint with `force`, unlimited max force, target position `90`, target velocity `0`, damping `10`, and stiffness `10`.
- Create a `PhysicsFixedJoint` under any selected Xform.
- Apply `PhysicsRigidBodyAPI` to the selected Xform.
- Set FixedJoint `body0` to the largest root Xform in the selected prim hierarchy.
- Set FixedJoint `body1` to the selected Xform.
- Put selected Mesh prims, or Mesh descendants of selected Xforms, into a new `group_N` Xform under the top-level Root Xform, then move the meshes into an inner Xform named by the `Inner Xform name` input while preserving world transforms.
- Use the `Joint preset` selector for the group-and-joint tool, currently `wheel` or `door`.
- Optionally run the group-and-joint tool: in `wheel` mode it automatically adds a RevoluteJoint at the new group's AABB center.
- Optionally run the group-and-joint tool: in `door` mode it automatically adds a RevoluteJoint at the new group's AABB face center, using the current Revolute axis as the hinge axis.
- Move selected Mesh prims, or Mesh descendants of selected Xforms, directly into `group_0/<Inner Xform name>` while preserving world transforms. If the name is `body`, the tool uses `group_0/body` directly; otherwise it creates a unique sibling such as `wheel`, `wheel_1`, or `wheel_2`.
- Reset only the selected Xform subtree by moving its Mesh prims into a `group_0` child while preserving world transforms.
- Delete empty Xform prims while preserving the top-level Root Xform and DefaultPrim.
- Select AABB-similar Xform prims from a selected joint or model prim as the first-stage shape filter.
- Tune AABB shape filtering with editable size-ratio and volume tolerance fields.

## Install

Copy the `hello.isaac.ui` folder into the Isaac Sim extension user directory:

```text
<ISAAC_SIM_ROOT>/extsUser/hello.isaac.ui
```

Start Isaac Sim, then open:

```text
Window > Extensions
```

Search for `Hello Isaac UI` and enable it.

To auto-load the extension, add this dependency to the target `.kit` experience file:

```toml
[dependencies]
"hello.isaac.ui" = { order = 10000 }
```

For the default Isaac Sim launcher, the common file is:

```text
<ISAAC_SIM_ROOT>/apps/isaacsim.exp.full.kit
```
