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
- Put selected Mesh prims into a new independent Xform under their nearest common Xform parent while preserving world transforms.
- Reset only the selected Xform subtree by moving its Mesh prims into a `group_0` child while preserving world transforms.
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
