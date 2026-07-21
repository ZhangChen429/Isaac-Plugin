import omni.ext
import omni.kit.actions.core
import omni.kit.commands
import omni.usd
import omni.ui as ui
from pathlib import Path
from omni.kit.menu.utils import MenuItemDescription, add_menu_items, remove_menu_items
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics


EXTENSION_TITLE = "Hello Isaac UI"
MENU_CATEGORY = "Window"
ACTION_NAME = "ToggleWindow"
REVOLUTE_JOINT_NAME = "RevoluteJoint"
FIXED_JOINT_NAME = "FixedJoint"
DEFAULT_BATCH_PATH = r"E:\Data\USD\kook"
DEFAULT_ROOT_XFORM_NAME = "root_tap"
USD_EXTENSIONS = {".usd", ".usda", ".usdc", ".usdz"}
REVOLUTE_AXES = ("X", "Y", "Z")


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._click_count = 0
        self._status_label = None
        self._batch_path_model = None
        self._root_name_model = None
        self._revolute_axis_model = None

        self._window = ui.Window(
            EXTENSION_TITLE,
            width=360,
            height=420,
            visible=False,
            dockPreference=ui.DockPreference.LEFT_BOTTOM,
        )
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.register_action(
            ext_id,
            ACTION_NAME,
            self._toggle_window,
            description=f"Show or hide {EXTENSION_TITLE}",
        )

        self._menu_items = [
            MenuItemDescription(name=EXTENSION_TITLE, onclick_action=(ext_id, ACTION_NAME))
        ]
        add_menu_items(self._menu_items, MENU_CATEGORY)

        self._build_ui()

    def on_shutdown(self):
        remove_menu_items(self._menu_items, MENU_CATEGORY)

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_action(self._ext_id, ACTION_NAME)

        self._status_label = None
        self._window = None

    def _toggle_window(self):
        self._window.visible = not self._window.visible

    def _on_visibility_changed(self, visible):
        if visible and self._status_label:
            self._status_label.text = "Window is visible. Ready."

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=10, height=0):
                ui.Label(EXTENSION_TITLE, height=28, style={"font_size": 20})
                self._status_label = ui.Label("Ready.", height=24)

                with ui.HStack(spacing=8, height=28):
                    ui.Label("Revolute axis", width=110)
                    self._revolute_axis_model = ui.ComboBox(
                        2,
                        *REVOLUTE_AXES,
                        height=24,
                    ).model

                with ui.HStack(spacing=8, height=32):
                    ui.Button("Revolute", clicked_fn=self._on_revolute_clicked)
                    ui.Button("FixedJoint", clicked_fn=self._on_fixed_joint_clicked)
                    ui.Button("Reset", clicked_fn=self._on_reset_clicked)
                ui.Button(
                    "Revolute AABB Center",
                    height=32,
                    clicked_fn=self._on_revolute_aabb_center_clicked,
                )

                ui.Spacer(height=8)
                ui.Label("Select an Xform in the Stage Tree, then create a Revolute or FixedJoint.", word_wrap=True)

                ui.Spacer(height=10)
                ui.Label("Batch USD folder:", height=20)
                self._batch_path_model = ui.SimpleStringModel(DEFAULT_BATCH_PATH)
                ui.StringField(model=self._batch_path_model, height=28)
                ui.Button(
                    "Add ArticulationRoot to missing root Xforms",
                    height=32,
                    clicked_fn=self._on_batch_articulation_root_clicked,
                )
                ui.Spacer(height=8)
                ui.Label("Root Xform name:", height=20)
                self._root_name_model = ui.SimpleStringModel(DEFAULT_ROOT_XFORM_NAME)
                ui.StringField(model=self._root_name_model, height=28)
                ui.Button(
                    "Rename root Xforms in USD folder",
                    height=32,
                    clicked_fn=self._on_batch_rename_root_xform_clicked,
                )

    def _on_revolute_clicked(self):
        stage, selected_prim = self._get_selected_xform(require_group_prefix=True)
        if not stage or not selected_prim:
            return

        body0_prim = self._find_group_0(stage) or self._find_top_level_xform(stage, selected_prim)
        if not body0_prim or not body0_prim.IsValid():
            self._set_status("Could not find group_0 or a top-level root Xform.")
            return

        self._ensure_rigid_body(selected_prim)

        joint_path = self._make_unique_child_path(stage, selected_prim.GetPath(), REVOLUTE_JOINT_NAME)
        joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
        joint.CreateBody0Rel().SetTargets([body0_prim.GetPath()])
        joint.CreateBody1Rel().SetTargets([selected_prim.GetPath()])
        axis = self._get_revolute_axis()
        self._configure_revolute_joint(joint, axis)
        self._add_angular_drive(joint)

        self._click_count += 1
        self._set_status(
            f"Created {joint_path.name} axis={axis} with angularDrive: body0={body0_prim.GetName()}, body1={selected_prim.GetName()}."
        )
        print(
            f"[{EXTENSION_TITLE}] Created {joint_path} axis={axis} "
            f"body0={body0_prim.GetPath()} body1={selected_prim.GetPath()}"
        )

    def _on_revolute_aabb_center_clicked(self):
        stage, selected_prim = self._get_selected_xform(require_group_prefix=True)
        if not stage or not selected_prim:
            return

        body0_prim = self._find_group_0(stage) or self._find_top_level_xform(stage, selected_prim)
        if not body0_prim or not body0_prim.IsValid():
            self._set_status("Could not find group_0 or a top-level root Xform.")
            return

        center_world, _auto_axis = self._compute_world_aabb_center_and_axis(selected_prim)
        if center_world is None:
            self._set_status(f"Could not compute AABB center for {selected_prim.GetPath()}.")
            return

        self._ensure_rigid_body(selected_prim)

        joint_path = self._make_unique_child_path(stage, selected_prim.GetPath(), REVOLUTE_JOINT_NAME)
        joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
        joint.CreateBody0Rel().SetTargets([body0_prim.GetPath()])
        joint.CreateBody1Rel().SetTargets([selected_prim.GetPath()])
        axis = self._get_revolute_axis()
        self._configure_revolute_joint(joint, axis)
        joint.CreateLocalPos0Attr(self._world_point_to_local(body0_prim, center_world))
        joint.CreateLocalPos1Attr(self._world_point_to_local(selected_prim, center_world))
        self._add_angular_drive(joint)

        self._click_count += 1
        center_text = f"({center_world[0]:.3f}, {center_world[1]:.3f}, {center_world[2]:.3f})"
        self._set_status(
            f"Created {joint_path.name} at AABB center {center_text}, axis={axis}: body0={body0_prim.GetName()}, body1={selected_prim.GetName()}."
        )
        print(
            f"[{EXTENSION_TITLE}] Created {joint_path} at AABB center {center_text} axis={axis} "
            f"body0={body0_prim.GetPath()} body1={selected_prim.GetPath()}"
        )

    def _on_fixed_joint_clicked(self):
        stage, selected_prim = self._get_selected_xform(require_group_prefix=False)
        if not stage or not selected_prim:
            return

        body0_prim = self._find_root_xform_for_prim(stage, selected_prim)
        if not body0_prim or not body0_prim.IsValid():
            self._set_status("Could not find the largest root Xform.")
            return

        self._ensure_rigid_body(selected_prim)

        joint_path = self._make_unique_child_path(stage, selected_prim.GetPath(), FIXED_JOINT_NAME)
        joint = UsdPhysics.FixedJoint.Define(stage, joint_path)
        joint.CreateBody0Rel().SetTargets([body0_prim.GetPath()])
        joint.CreateBody1Rel().SetTargets([selected_prim.GetPath()])

        self._click_count += 1
        self._set_status(
            f"Created {joint_path.name}: body0={body0_prim.GetName()}, body1={selected_prim.GetName()}."
        )
        print(f"[{EXTENSION_TITLE}] Created {joint_path} body0={body0_prim.GetPath()} body1={selected_prim.GetPath()}")

    def _on_reset_clicked(self):
        self._click_count = 0
        self._move_all_meshes_to_group_0()

    def _move_all_meshes_to_group_0(self):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            self._set_status("No stage is open.")
            return

        root_xform = self._find_stage_root_xform(stage)
        if not root_xform or not root_xform.IsValid():
            root_xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World")).GetPrim()

        group_path = root_xform.GetPath().AppendChild("group_0")
        group_prim = stage.GetPrimAtPath(group_path)
        if group_prim and group_prim.IsValid() and not group_prim.IsA(UsdGeom.Xform):
            self._set_status(f"{group_path} already exists but is not an Xform.")
            return
        if not group_prim or not group_prim.IsValid():
            group_prim = UsdGeom.Xform.Define(stage, group_path).GetPrim()

        mesh_paths = [
            prim.GetPath()
            for prim in stage.Traverse()
            if prim.IsA(UsdGeom.Mesh)
        ]
        if not mesh_paths:
            self._set_status("No Mesh prims found.")
            return

        moved = 0
        skipped = 0
        reserved_names = set()
        for mesh_path in mesh_paths:
            mesh_prim = stage.GetPrimAtPath(mesh_path)
            if not mesh_prim or not mesh_prim.IsValid():
                skipped += 1
                continue

            if mesh_path.GetParentPath() == group_path:
                skipped += 1
                reserved_names.add(mesh_prim.GetName())
                continue

            target_path = self._make_unique_mesh_target_path(stage, group_path, mesh_prim.GetName(), reserved_names)
            omni.kit.commands.execute(
                "MovePrim",
                path_from=str(mesh_path),
                path_to=str(target_path),
                keep_world_transform=True,
                destructive=False,
            )
            moved += 1
            reserved_names.add(target_path.name)

        self._set_status(f"Moved {moved} Mesh prims to {group_path}; skipped {skipped}.")

    def _on_batch_articulation_root_clicked(self):
        folder_text = (
            self._batch_path_model.get_value_as_string()
            if self._batch_path_model
            else ""
        )
        folder = Path(folder_text.strip().strip('"'))

        if not folder.exists() or not folder.is_dir():
            self._set_status(f"Invalid folder: {folder}")
            return

        usd_files = self._collect_usd_files(folder)

        if not usd_files:
            self._set_status(f"No USD files found: {folder}")
            return

        scanned = 0
        modified = 0
        skipped = 0
        failed = 0

        for usd_file in usd_files:
            try:
                result = self._ensure_articulation_root_in_usd(usd_file)
                scanned += 1
                if result == "modified":
                    modified += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as exc:
                failed += 1
                print(f"[{EXTENSION_TITLE}] Failed {usd_file}: {exc}")

        self._set_status(
            f"ArticulationRoot scan done: scanned={scanned}, modified={modified}, "
            f"skipped={skipped}, failed={failed}."
        )

    def _on_batch_rename_root_xform_clicked(self):
        folder_text = (
            self._batch_path_model.get_value_as_string()
            if self._batch_path_model
            else ""
        )
        new_name = (
            self._root_name_model.get_value_as_string().strip()
            if self._root_name_model
            else ""
        )
        folder = Path(folder_text.strip().strip('"'))

        if not folder.exists() or not folder.is_dir():
            self._set_status(f"Invalid folder: {folder}")
            return
        if not new_name:
            self._set_status("Root Xform name cannot be empty.")
            return
        if not Sdf.Path.IsValidIdentifier(new_name):
            self._set_status(f"Invalid USD prim name: {new_name}")
            return

        usd_files = self._collect_usd_files(folder)
        if not usd_files:
            self._set_status(f"No USD files found: {folder}")
            return

        scanned = 0
        modified = 0
        skipped = 0
        failed = 0

        for usd_file in usd_files:
            try:
                result = self._rename_root_xform_in_usd(usd_file, new_name)
                scanned += 1
                if result == "modified":
                    modified += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as exc:
                failed += 1
                print(f"[{EXTENSION_TITLE}] Failed {usd_file}: {exc}")

        self._set_status(
            f"Rename root Xforms done: scanned={scanned}, modified={modified}, "
            f"skipped={skipped}, failed={failed}."
        )

    def _set_status(self, text):
        if self._status_label:
            self._status_label.text = text
        print(f"[{EXTENSION_TITLE}] {text}")

    def _get_revolute_axis(self):
        if not self._revolute_axis_model:
            return "Z"

        index = self._revolute_axis_model.get_item_value_model().as_int
        if index < 0 or index >= len(REVOLUTE_AXES):
            return "Z"

        return REVOLUTE_AXES[index]

    def _collect_usd_files(self, folder):
        return sorted(
            [
                path
                for path in folder.rglob("*")
                if path.is_file() and path.suffix.lower() in USD_EXTENSIONS
            ],
            key=lambda path: str(path).lower(),
        )

    def _ensure_articulation_root_in_usd(self, usd_file):
        stage = Usd.Stage.Open(str(usd_file))
        if not stage:
            raise RuntimeError("Usd.Stage.Open returned None")

        root_xform = self._find_stage_root_xform(stage)
        if not root_xform or not root_xform.IsValid():
            print(f"[{EXTENSION_TITLE}] No root Xform found: {usd_file}")
            return "skipped"

        if root_xform.HasAPI(UsdPhysics.ArticulationRootAPI):
            return "skipped"

        UsdPhysics.ArticulationRootAPI.Apply(root_xform)
        stage.GetRootLayer().Save()
        print(f"[{EXTENSION_TITLE}] Added ArticulationRootAPI: {usd_file} -> {root_xform.GetPath()}")
        return "modified"

    def _rename_root_xform_in_usd(self, usd_file, new_name):
        stage = Usd.Stage.Open(str(usd_file))
        if not stage:
            raise RuntimeError("Usd.Stage.Open returned None")

        root_xform = self._find_stage_root_xform(stage)
        if not root_xform or not root_xform.IsValid():
            print(f"[{EXTENSION_TITLE}] No root Xform found: {usd_file}")
            return "skipped"

        old_path = root_xform.GetPath()
        if root_xform.GetName() == new_name:
            return "skipped"

        new_path = old_path.GetParentPath().AppendChild(new_name)
        if stage.GetPrimAtPath(new_path).IsValid():
            print(f"[{EXTENSION_TITLE}] Target root already exists, skipped: {usd_file} -> {new_path}")
            return "skipped"

        default_prim_path = None
        default_prim = stage.GetDefaultPrim()
        if default_prim and default_prim.IsValid():
            default_prim_path = default_prim.GetPath()

        editor = Usd.NamespaceEditor(stage)
        if not editor.RenamePrim(root_xform, new_name):
            raise RuntimeError(f"RenamePrim rejected {old_path} -> {new_name}")

        if not editor.CanApplyEdits():
            raise RuntimeError(f"Cannot apply rename edits {old_path} -> {new_path}")

        editor.ApplyEdits()
        renamed_prim = stage.GetPrimAtPath(new_path)
        if default_prim_path == old_path and renamed_prim and renamed_prim.IsValid():
            stage.SetDefaultPrim(renamed_prim)

        stage.GetRootLayer().Save()
        print(f"[{EXTENSION_TITLE}] Renamed root Xform: {usd_file} {old_path} -> {new_path}")
        return "modified"

    def _find_stage_root_xform(self, stage):
        default_prim = stage.GetDefaultPrim()
        if default_prim and default_prim.IsValid() and default_prim.IsA(UsdGeom.Xform):
            return default_prim

        world_prim = stage.GetPrimAtPath("/World")
        if world_prim and world_prim.IsValid() and world_prim.IsA(UsdGeom.Xform):
            return world_prim

        for prim in stage.GetPseudoRoot().GetChildren():
            if prim.IsA(UsdGeom.Xform):
                return prim

        for prim in stage.TraverseAll():
            if prim.IsA(UsdGeom.Xform):
                return prim

        return None

    def _get_selected_xform(self, require_group_prefix):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            self._set_status("No stage is open.")
            return None, None

        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            self._set_status("Select one Xform first.")
            return None, None

        selected_prim = stage.GetPrimAtPath(selected_paths[0])
        if not selected_prim or not selected_prim.IsValid():
            self._set_status("Selected prim is invalid.")
            return None, None

        if not selected_prim.IsA(UsdGeom.Xform):
            self._set_status("Selected prim must be an Xform.")
            return None, None

        if require_group_prefix and not selected_prim.GetName().startswith("group"):
            self._set_status("Selected Xform name must start with 'group'.")
            return None, None

        return stage, selected_prim

    def _ensure_rigid_body(self, prim):
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI.Apply(prim)

    def _find_group_0(self, stage):
        world_group_0 = stage.GetPrimAtPath("/World/group_0")
        if world_group_0 and world_group_0.IsValid():
            return world_group_0

        for prim in stage.Traverse():
            if prim.GetName() == "group_0" and prim.IsA(UsdGeom.Xform):
                return prim

        return None

    def _find_top_level_xform(self, stage, selected_prim):
        default_prim = stage.GetDefaultPrim()
        if default_prim and default_prim.IsValid() and default_prim.IsA(UsdGeom.Xform):
            return default_prim

        world_prim = stage.GetPrimAtPath("/World")
        if world_prim and world_prim.IsValid() and world_prim.IsA(UsdGeom.Xform):
            return world_prim

        pseudo_root = stage.GetPseudoRoot()
        for child in pseudo_root.GetChildren():
            if child.IsA(UsdGeom.Xform):
                return child

        path = selected_prim.GetPath()
        if path.pathString.count("/") > 1:
            top_path = "/" + path.pathString.strip("/").split("/")[0]
            top_prim = stage.GetPrimAtPath(top_path)
            if top_prim and top_prim.IsValid() and top_prim.IsA(UsdGeom.Xform):
                return top_prim

        return None

    def _find_root_xform_for_prim(self, stage, prim):
        path = prim.GetPath()
        root_xform = prim if prim.IsA(UsdGeom.Xform) else None

        while path != path.absoluteRootPath:
            parent_path = path.GetParentPath()
            if parent_path == path.absoluteRootPath:
                break

            parent_prim = stage.GetPrimAtPath(parent_path)
            if parent_prim and parent_prim.IsValid() and parent_prim.IsA(UsdGeom.Xform):
                root_xform = parent_prim

            path = parent_path

        return root_xform

    def _compute_world_aabb_center_and_axis(self, prim):
        time_code = Usd.TimeCode.Default()
        purposes = [
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
        ]
        bbox_cache = UsdGeom.BBoxCache(time_code, purposes, useExtentsHint=True)
        aligned_box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()

        if not aligned_box.IsEmpty():
            min_point = aligned_box.GetMin()
            max_point = aligned_box.GetMax()
            size_x = abs(float(max_point[0] - min_point[0]))
            size_y = abs(float(max_point[1] - min_point[1]))
            size_z = abs(float(max_point[2] - min_point[2]))
            face_areas = {
                "X": size_y * size_z,
                "Y": size_x * size_z,
                "Z": size_x * size_y,
            }
            axis = max(face_areas, key=face_areas.get)
            return aligned_box.GetMidpoint(), axis

        if prim.IsA(UsdGeom.Xformable):
            xform_cache = UsdGeom.XformCache(time_code)
            return xform_cache.GetLocalToWorldTransform(prim).ExtractTranslation(), "Z"

        return None, "Z"

    def _world_point_to_local(self, prim, world_point):
        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        local_point = xform_cache.GetLocalToWorldTransform(prim).GetInverse().Transform(world_point)
        return Gf.Vec3f(
            float(local_point[0]),
            float(local_point[1]),
            float(local_point[2]),
        )

    def _configure_revolute_joint(self, joint, axis):
        joint.CreateAxisAttr(axis)
        joint.CreateLowerLimitAttr(0.0)
        joint.CreateUpperLimitAttr(180.0)

    def _make_unique_mesh_target_path(self, stage, group_path, mesh_name, reserved_names):
        target_path = group_path.AppendChild(mesh_name)
        if not stage.GetPrimAtPath(target_path).IsValid() and mesh_name not in reserved_names:
            return target_path

        index = 1
        while True:
            candidate_name = f"{mesh_name}_{index}"
            candidate_path = group_path.AppendChild(candidate_name)
            if not stage.GetPrimAtPath(candidate_path).IsValid() and candidate_name not in reserved_names:
                return candidate_path
            index += 1

    def _make_unique_child_path(self, stage, parent_path, child_name):
        path = parent_path.AppendChild(child_name)
        if not stage.GetPrimAtPath(path).IsValid():
            return path

        index = 1
        while True:
            candidate = parent_path.AppendChild(f"{child_name}_{index}")
            if not stage.GetPrimAtPath(candidate).IsValid():
                return candidate
            index += 1

    def _add_angular_drive(self, joint):
        drive_api = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), UsdPhysics.Tokens.angular)
        drive_api.CreateTypeAttr("force")
        drive_api.CreateMaxForceAttr(float("inf"))
        drive_api.CreateTargetPositionAttr(90.0)
        drive_api.CreateTargetVelocityAttr(0.0)
        drive_api.CreateDampingAttr(10.0)
        drive_api.CreateStiffnessAttr(10.0)
        return drive_api
