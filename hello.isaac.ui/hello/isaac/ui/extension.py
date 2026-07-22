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
DEFAULT_MESH_BODY_XFORM_NAME = "body"
USD_EXTENSIONS = {".usd", ".usda", ".usdc", ".usdz"}
REVOLUTE_AXES = ("X", "Y", "Z")
MESH_JOINT_PRESETS = ("wheel", "door")
AABB_SIZE_TOLERANCE = 0.08
AABB_VOLUME_TOLERANCE = 0.20
MIN_AABB_AXIS_LENGTH = 1e-5


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._click_count = 0
        self._status_label = None
        self._batch_path_model = None
        self._root_name_model = None
        self._mesh_body_name_model = None
        self._mesh_joint_preset_model = None
        self._revolute_axis_model = None
        self._aabb_size_tolerance_model = None
        self._aabb_volume_tolerance_model = None

        self._window = ui.Window(
            EXTENSION_TITLE,
            width=430,
            height=560,
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
            with ui.ScrollingFrame():
                with ui.VStack(spacing=8, height=0):
                    ui.Label(EXTENSION_TITLE, height=28, style={"font_size": 20})
                    self._status_label = ui.Label("Ready.", height=24, word_wrap=True)

                    self._build_section_header("Joint Tools")
                    with ui.VStack(spacing=6, height=0):
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Revolute axis", width=120)
                            self._revolute_axis_model = ui.ComboBox(
                                2,
                                *REVOLUTE_AXES,
                                height=24,
                            ).model

                        with ui.HStack(spacing=8, height=32):
                            ui.Button("Revolute", clicked_fn=self._on_revolute_clicked)
                            ui.Button("FixedJoint", clicked_fn=self._on_fixed_joint_clicked)
                            ui.Button("Reset Selected", clicked_fn=self._on_reset_clicked)
                        ui.Button(
                            "Revolute AABB Center",
                            height=32,
                            clicked_fn=self._on_revolute_aabb_center_clicked,
                        )

                    self._build_section_header("Mesh Tools")
                    with ui.VStack(spacing=6, height=0):
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Inner Xform name", width=120)
                            self._mesh_body_name_model = ui.SimpleStringModel(DEFAULT_MESH_BODY_XFORM_NAME)
                            ui.StringField(model=self._mesh_body_name_model, height=24)
                        ui.Button(
                            "Put Selected Meshes in New Group",
                            height=32,
                            clicked_fn=self._on_group_selected_meshes_clicked,
                        )
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Joint preset", width=120)
                            self._mesh_joint_preset_model = ui.ComboBox(
                                0,
                                *MESH_JOINT_PRESETS,
                                height=24,
                            ).model
                        ui.Button(
                            "Put Selected Meshes in New Group + Joint",
                            height=32,
                            clicked_fn=self._on_group_selected_meshes_with_joint_clicked,
                        )
                        ui.Button(
                            "Move Selected to group_0/body",
                            height=32,
                            clicked_fn=self._on_move_selected_to_group_0_body_clicked,
                        )

                    self._build_section_header("Shape Selection")
                    with ui.VStack(spacing=6, height=0):
                        ui.Button(
                            "Select Similar Shape by AABB",
                            height=32,
                            clicked_fn=self._on_select_similar_shape_aabb_clicked,
                        )
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Size tolerance", width=120)
                            self._aabb_size_tolerance_model = ui.SimpleFloatModel(AABB_SIZE_TOLERANCE)
                            ui.FloatField(model=self._aabb_size_tolerance_model, height=24)
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Volume tolerance", width=120)
                            self._aabb_volume_tolerance_model = ui.SimpleFloatModel(AABB_VOLUME_TOLERANCE)
                            ui.FloatField(model=self._aabb_volume_tolerance_model, height=24)

                    self._build_section_header("Batch USD")
                    with ui.VStack(spacing=6, height=0):
                        ui.Label("Folder", height=18)
                        self._batch_path_model = ui.SimpleStringModel(DEFAULT_BATCH_PATH)
                        ui.StringField(model=self._batch_path_model, height=28)
                        ui.Button(
                            "Add ArticulationRoot to missing root Xforms",
                            height=32,
                            clicked_fn=self._on_batch_articulation_root_clicked,
                        )
                        with ui.HStack(spacing=8, height=28):
                            ui.Label("Root Xform name", width=120)
                            self._root_name_model = ui.SimpleStringModel(DEFAULT_ROOT_XFORM_NAME)
                            ui.StringField(model=self._root_name_model, height=24)
                        ui.Button(
                            "Rename root Xforms in USD folder",
                            height=32,
                            clicked_fn=self._on_batch_rename_root_xform_clicked,
                        )

                    ui.Spacer(height=4)

    def _build_section_header(self, title):
        ui.Spacer(height=4)
        ui.Separator(height=1)
        ui.Label(title, height=22, style={"font_size": 16})

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

        center_world, auto_axis = self._compute_world_aabb_center_and_axis(selected_prim)
        if center_world is None:
            self._set_status(f"Could not compute AABB center for {selected_prim.GetPath()}.")
            return

        self._ensure_rigid_body(selected_prim)

        joint_path = self._make_unique_child_path(stage, selected_prim.GetPath(), REVOLUTE_JOINT_NAME)
        joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
        joint.CreateBody0Rel().SetTargets([body0_prim.GetPath()])
        joint.CreateBody1Rel().SetTargets([selected_prim.GetPath()])
        axis = auto_axis
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

    def _on_group_selected_meshes_clicked(self):
        body_name = self._get_mesh_body_xform_name()
        result = self._group_selected_meshes(body_name)
        if not result:
            return

        group_path, body_path, moved, skipped = result
        self._set_status(f"Moved {moved} Mesh prims into {body_path}; created {group_path}; skipped {skipped}.")
        print(f"[{EXTENSION_TITLE}] Created mesh group: {group_path}, inner Xform: {body_path}")

    def _on_group_selected_meshes_with_joint_clicked(self):
        body_name = self._get_mesh_joint_preset_name()
        result = self._group_selected_meshes(body_name)
        if not result:
            return

        group_path, body_path, moved, skipped = result
        stage = omni.usd.get_context().get_stage()
        group_prim = stage.GetPrimAtPath(group_path) if stage else None
        if not group_prim or not group_prim.IsValid():
            self._set_status(f"Could not find created group: {group_path}")
            return

        body_name = body_path.name
        joint_mode = "face" if body_name == "door" else "center"
        joint_result = self._create_revolute_joint_for_group(stage, group_prim, joint_mode)
        if not joint_result:
            return

        joint_path, joint_point, axis = joint_result
        point_text = f"({joint_point[0]:.3f}, {joint_point[1]:.3f}, {joint_point[2]:.3f})"
        self._set_status(
            f"Moved {moved} Mesh prims into {body_path}; created {group_path}; "
            f"added {joint_path.name} at {joint_mode} {point_text}, axis={axis}; skipped {skipped}."
        )
        print(
            f"[{EXTENSION_TITLE}] Created mesh group: {group_path}, inner Xform: {body_path}, "
            f"joint={joint_path}, mode={joint_mode}, point={point_text}, axis={axis}"
        )

    def _on_move_selected_to_group_0_body_clicked(self):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            self._set_status("No stage is open.")
            return

        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            self._set_status("Select one or more Mesh or Xform prims first.")
            return

        mesh_paths = self._collect_mesh_paths_from_selection(stage, selected_paths)
        if not mesh_paths:
            self._set_status("Selection does not contain any Mesh prims or Xforms with Mesh descendants.")
            return

        body_path = self._ensure_root_group_0_body(stage)
        if not body_path:
            return

        moved = 0
        skipped = 0
        reserved_names = set()
        for mesh_path in mesh_paths:
            mesh_prim = stage.GetPrimAtPath(mesh_path)
            if not mesh_prim or not mesh_prim.IsValid():
                skipped += 1
                continue

            if mesh_path.GetParentPath() == body_path:
                skipped += 1
                reserved_names.add(mesh_prim.GetName())
                continue

            target_path = self._make_unique_mesh_target_path(stage, body_path, mesh_prim.GetName(), reserved_names)
            omni.kit.commands.execute(
                "MovePrim",
                path_from=str(mesh_path),
                path_to=str(target_path),
                keep_world_transform=True,
                destructive=False,
            )
            moved += 1
            reserved_names.add(target_path.name)

        omni.usd.get_context().get_selection().set_selected_prim_paths([str(body_path)], True)
        self._set_status(f"Moved {moved} Mesh prims into {body_path}; skipped {skipped}.")
        print(f"[{EXTENSION_TITLE}] Moved selected meshes to {body_path}: moved={moved}, skipped={skipped}")

    def _group_selected_meshes(self, body_name):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            self._set_status("No stage is open.")
            return None

        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            self._set_status("Select one or more Mesh or Xform prims first.")
            return None

        mesh_paths = self._collect_mesh_paths_from_selection(stage, selected_paths)
        if not mesh_paths:
            self._set_status("Selection does not contain any Mesh prims or Xforms with Mesh descendants.")
            return None

        root_xform = self._find_stage_root_xform(stage)
        if not root_xform or not root_xform.IsValid():
            root_xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World")).GetPrim()

        parent_path = root_xform.GetPath()

        if not Sdf.Path.IsValidIdentifier(body_name):
            self._set_status(f"Invalid inner Xform name: {body_name}")
            return None

        group_path = self._make_next_group_path(stage, parent_path)
        group_prim = UsdGeom.Xform.Define(stage, group_path).GetPrim()
        if not group_prim or not group_prim.IsValid():
            self._set_status(f"Could not create Xform: {group_path}")
            return None

        body_path = group_path.AppendChild(body_name)
        body_prim = UsdGeom.Xform.Define(stage, body_path).GetPrim()
        if not body_prim or not body_prim.IsValid():
            self._set_status(f"Could not create inner Xform: {body_path}")
            return None

        moved = 0
        skipped = 0
        reserved_names = set()
        for mesh_path in mesh_paths:
            mesh_prim = stage.GetPrimAtPath(mesh_path)
            if not mesh_prim or not mesh_prim.IsValid():
                skipped += 1
                continue

            target_path = self._make_unique_mesh_target_path(stage, body_path, mesh_prim.GetName(), reserved_names)
            omni.kit.commands.execute(
                "MovePrim",
                path_from=str(mesh_path),
                path_to=str(target_path),
                keep_world_transform=True,
                destructive=False,
            )
            moved += 1
            reserved_names.add(target_path.name)

        omni.usd.get_context().get_selection().set_selected_prim_paths([str(group_path)], True)
        return group_path, body_path, moved, skipped

    def _on_select_similar_shape_aabb_clicked(self):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            self._set_status("No stage is open.")
            return

        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            self._set_status("Select one track joint or model prim first.")
            return

        selected_prim = stage.GetPrimAtPath(selected_paths[0])
        if not selected_prim or not selected_prim.IsValid():
            self._set_status("Selected prim is invalid.")
            return

        source_prim = self._resolve_model_prim_from_selection(stage, selected_prim)
        if not source_prim or not source_prim.IsValid():
            self._set_status(f"Could not resolve a model prim from {selected_prim.GetPath()}.")
            return

        size_tolerance = self._get_aabb_size_tolerance()
        volume_tolerance = self._get_aabb_volume_tolerance()
        matches, details = self._find_similar_shape_prims_by_aabb(
            stage,
            source_prim,
            size_tolerance,
            volume_tolerance,
        )
        if not matches:
            self._set_status(
                f"No AABB-similar prims found for {source_prim.GetPath()} "
                f"with size_tol={size_tolerance:.3f}, volume_tol={volume_tolerance:.3f}."
            )
            return

        match_paths = [str(prim.GetPath()) for prim, _score, _dims, _volume in matches]
        omni.usd.get_context().get_selection().set_selected_prim_paths(match_paths, True)
        self._set_status(
            f"Selected {len(match_paths)} AABB-similar prims; source={source_prim.GetPath()}."
        )
        print(f"[{EXTENSION_TITLE}] AABB source from selection: {selected_prim.GetPath()} -> {source_prim.GetPath()}")
        print(
            f"[{EXTENSION_TITLE}] source dims(sorted)={details['source_dims']} "
            f"normalized={details['source_normalized']} volume={details['source_volume']:.6f} "
            f"size_tolerance={size_tolerance:.3f} volume_tolerance={volume_tolerance:.3f}"
        )
        for prim, score, dims, volume in matches:
            print(
                f"[{EXTENSION_TITLE}] AABB match score={score:.3f} "
                f"dims(sorted)={dims} volume={volume:.6f}: {prim.GetPath()}"
            )

    def _on_reset_clicked(self):
        self._click_count = 0
        self._move_selected_xform_meshes_to_group_0()

    def _move_selected_xform_meshes_to_group_0(self):
        stage, root_xform = self._get_selected_xform(require_group_prefix=False)
        if not stage or not root_xform:
            return

        group_path = root_xform.GetPath().AppendChild("group_0")
        group_prim = stage.GetPrimAtPath(group_path)
        if group_prim and group_prim.IsValid() and not group_prim.IsA(UsdGeom.Xform):
            self._set_status(f"{group_path} already exists but is not an Xform.")
            return
        if not group_prim or not group_prim.IsValid():
            group_prim = UsdGeom.Xform.Define(stage, group_path).GetPrim()

        mesh_paths = [
            prim.GetPath()
            for prim in Usd.PrimRange(root_xform)
            if prim.IsA(UsdGeom.Mesh)
        ]
        if not mesh_paths:
            self._set_status(f"No Mesh prims found under {root_xform.GetPath()}.")
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

        self._set_status(
            f"Moved {moved} Mesh prims under {root_xform.GetPath()} to {group_path}; skipped {skipped}."
        )

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

    def _resolve_model_prim_from_selection(self, stage, selected_prim):
        if self._is_physics_joint(selected_prim):
            body_prim = self._get_joint_body_prim(stage, selected_prim, prefer_body1=True)
            if body_prim and body_prim.IsValid():
                return self._find_model_root_for_prim(body_prim)

        return self._find_model_root_for_prim(selected_prim)

    def _is_physics_joint(self, prim):
        type_name = prim.GetTypeName()
        return (
            type_name.startswith("Physics") and type_name.endswith("Joint")
        ) or prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.FixedJoint)

    def _get_joint_body_prim(self, stage, joint_prim, prefer_body1):
        body_names = ("body1", "body0") if prefer_body1 else ("body0", "body1")
        for body_name in body_names:
            rel = joint_prim.GetRelationship(f"physics:{body_name}")
            if not rel:
                continue

            targets = rel.GetTargets()
            for target in targets:
                body_prim = stage.GetPrimAtPath(target)
                if body_prim and body_prim.IsValid():
                    return body_prim

        return None

    def _find_model_root_for_prim(self, prim):
        if prim.IsA(UsdGeom.Xform):
            return prim

        path = prim.GetPath()
        stage = prim.GetStage()
        while path != path.absoluteRootPath:
            parent_path = path.GetParentPath()
            if parent_path == path.absoluteRootPath:
                break

            parent_prim = stage.GetPrimAtPath(parent_path)
            if (
                parent_prim
                and parent_prim.IsValid()
                and parent_prim.IsA(UsdGeom.Xform)
            ):
                return parent_prim

            path = parent_path

        return prim

    def _find_similar_shape_prims_by_aabb(self, stage, source_prim, size_tolerance, volume_tolerance):
        bbox_cache = self._make_bbox_cache()
        source_sig = self._compute_aabb_signature(bbox_cache, source_prim)
        if not source_sig:
            return [], {}

        source_dims, source_normalized, source_volume = source_sig
        matches = []

        for prim in stage.Traverse():
            if not prim.IsA(UsdGeom.Xform):
                continue
            if not self._has_mesh_descendant(prim):
                continue

            candidate_sig = self._compute_aabb_signature(bbox_cache, prim)
            if not candidate_sig:
                continue

            dims, normalized, volume = candidate_sig
            size_delta = self._max_abs_delta(source_normalized, normalized)
            volume_delta = self._relative_delta(source_volume, volume)

            if size_delta <= size_tolerance and volume_delta <= volume_tolerance:
                score = max(
                    0.0,
                    1.0
                    - (size_delta / max(size_tolerance, MIN_AABB_AXIS_LENGTH)) * 0.7
                    - (volume_delta / max(volume_tolerance, MIN_AABB_AXIS_LENGTH)) * 0.3,
                )
                matches.append((prim, score, dims, volume))

        matches.sort(key=lambda item: (-item[1], item[0].GetPath().pathString))
        details = {
            "source_dims": source_dims,
            "source_normalized": source_normalized,
            "source_volume": source_volume,
        }
        return matches, details

    def _get_aabb_size_tolerance(self):
        return self._get_positive_float_model_value(
            self._aabb_size_tolerance_model,
            AABB_SIZE_TOLERANCE,
            minimum=0.0,
            maximum=1.0,
        )

    def _get_aabb_volume_tolerance(self):
        return self._get_positive_float_model_value(
            self._aabb_volume_tolerance_model,
            AABB_VOLUME_TOLERANCE,
            minimum=0.0,
            maximum=10.0,
        )

    def _get_positive_float_model_value(self, model, default_value, minimum, maximum):
        if not model:
            return default_value

        try:
            value = float(model.as_float)
        except Exception:
            return default_value

        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value

    def _make_bbox_cache(self):
        purposes = [
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
        ]
        return UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes, useExtentsHint=True)

    def _compute_aabb_signature(self, bbox_cache, prim):
        aligned_box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
        if aligned_box.IsEmpty():
            return None

        min_point = aligned_box.GetMin()
        max_point = aligned_box.GetMax()
        dims = sorted(
            [
                abs(float(max_point[0] - min_point[0])),
                abs(float(max_point[1] - min_point[1])),
                abs(float(max_point[2] - min_point[2])),
            ],
            reverse=True,
        )
        if dims[0] <= MIN_AABB_AXIS_LENGTH:
            return None

        normalized = tuple(round(dim / dims[0], 6) for dim in dims)
        volume = max(dims[0], MIN_AABB_AXIS_LENGTH) * max(dims[1], MIN_AABB_AXIS_LENGTH) * max(dims[2], MIN_AABB_AXIS_LENGTH)
        rounded_dims = tuple(round(dim, 6) for dim in dims)
        return rounded_dims, normalized, volume

    def _has_mesh_descendant(self, prim):
        for child_prim in Usd.PrimRange(prim):
            if child_prim.IsA(UsdGeom.Mesh):
                return True
        return False

    def _max_abs_delta(self, values_a, values_b):
        return max(abs(float(a) - float(b)) for a, b in zip(values_a, values_b))

    def _relative_delta(self, value_a, value_b):
        denominator = max(abs(float(value_a)), abs(float(value_b)), MIN_AABB_AXIS_LENGTH)
        return abs(float(value_a) - float(value_b)) / denominator

    def _get_revolute_axis(self):
        if not self._revolute_axis_model:
            return "Z"

        index = self._revolute_axis_model.get_item_value_model().as_int
        if index < 0 or index >= len(REVOLUTE_AXES):
            return "Z"

        return REVOLUTE_AXES[index]

    def _get_mesh_body_xform_name(self):
        if not self._mesh_body_name_model:
            return DEFAULT_MESH_BODY_XFORM_NAME

        name = self._mesh_body_name_model.get_value_as_string().strip()
        return name or DEFAULT_MESH_BODY_XFORM_NAME

    def _get_mesh_joint_preset_name(self):
        if not self._mesh_joint_preset_model:
            return MESH_JOINT_PRESETS[0]

        index = self._mesh_joint_preset_model.get_item_value_model().as_int
        if index < 0 or index >= len(MESH_JOINT_PRESETS):
            return MESH_JOINT_PRESETS[0]

        return MESH_JOINT_PRESETS[index]

    def _create_revolute_joint_for_group(self, stage, group_prim, joint_mode):
        body0_prim = self._find_group_0(stage)
        if body0_prim and body0_prim.GetPath() == group_prim.GetPath():
            body0_prim = None
        body0_prim = body0_prim or self._find_top_level_xform(stage, group_prim)
        if not body0_prim or not body0_prim.IsValid():
            self._set_status("Could not find group_0 or a top-level root Xform.")
            return None

        if joint_mode == "face":
            joint_point, axis = self._compute_world_aabb_face_center_and_axis(group_prim)
            point_label = "AABB face center"
        else:
            joint_point, axis = self._compute_world_aabb_center_and_axis(group_prim)
            point_label = "AABB center"

        if joint_point is None:
            self._set_status(f"Could not compute {point_label} for {group_prim.GetPath()}.")
            return None

        self._ensure_rigid_body(group_prim)

        joint_path = self._make_unique_child_path(stage, group_prim.GetPath(), REVOLUTE_JOINT_NAME)
        joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
        joint.CreateBody0Rel().SetTargets([body0_prim.GetPath()])
        joint.CreateBody1Rel().SetTargets([group_prim.GetPath()])
        self._configure_revolute_joint(joint, axis)
        joint.CreateLocalPos0Attr(self._world_point_to_local(body0_prim, joint_point))
        joint.CreateLocalPos1Attr(self._world_point_to_local(group_prim, joint_point))
        self._add_angular_drive(joint)

        self._click_count += 1
        return joint_path, joint_point, axis

    def _collect_mesh_paths_from_selection(self, stage, selected_paths):
        mesh_paths = []
        seen_paths = set()

        for selected_path in selected_paths:
            prim = stage.GetPrimAtPath(selected_path)
            if not prim or not prim.IsValid():
                continue

            if prim.IsA(UsdGeom.Mesh):
                self._append_unique_mesh_path(mesh_paths, seen_paths, prim.GetPath())
                continue

            if prim.IsA(UsdGeom.Xform):
                for child_prim in Usd.PrimRange(prim):
                    if child_prim.IsA(UsdGeom.Mesh):
                        self._append_unique_mesh_path(mesh_paths, seen_paths, child_prim.GetPath())

        return mesh_paths

    def _append_unique_mesh_path(self, mesh_paths, seen_paths, mesh_path):
        path_text = str(mesh_path)
        if path_text in seen_paths:
            return

        seen_paths.add(path_text)
        mesh_paths.append(mesh_path)

    def _ensure_root_group_0_body(self, stage):
        root_xform = self._find_stage_root_xform(stage)
        if not root_xform or not root_xform.IsValid():
            root_xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World")).GetPrim()

        group_path = root_xform.GetPath().AppendChild("group_0")
        group_prim = stage.GetPrimAtPath(group_path)
        if group_prim and group_prim.IsValid() and not group_prim.IsA(UsdGeom.Xform):
            self._set_status(f"{group_path} already exists but is not an Xform.")
            return None
        if not group_prim or not group_prim.IsValid():
            group_prim = UsdGeom.Xform.Define(stage, group_path).GetPrim()

        body_path = group_path.AppendChild("body")
        body_prim = stage.GetPrimAtPath(body_path)
        if body_prim and body_prim.IsValid() and not body_prim.IsA(UsdGeom.Xform):
            self._set_status(f"{body_path} already exists but is not an Xform.")
            return None
        if not body_prim or not body_prim.IsValid():
            body_prim = UsdGeom.Xform.Define(stage, body_path).GetPrim()

        return body_path

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

    def _compute_world_aabb_face_center_and_axis(self, prim):
        time_code = Usd.TimeCode.Default()
        purposes = [
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
        ]
        bbox_cache = UsdGeom.BBoxCache(time_code, purposes, useExtentsHint=True)
        aligned_box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()

        if aligned_box.IsEmpty():
            if prim.IsA(UsdGeom.Xformable):
                xform_cache = UsdGeom.XformCache(time_code)
                return xform_cache.GetLocalToWorldTransform(prim).ExtractTranslation(), self._get_revolute_axis()
            return None, self._get_revolute_axis()

        min_point = aligned_box.GetMin()
        max_point = aligned_box.GetMax()
        midpoint = aligned_box.GetMidpoint()
        axis = self._get_revolute_axis()
        axis_to_index = {"X": 0, "Y": 1, "Z": 2}
        rotation_axis_index = axis_to_index.get(axis, 2)

        sizes = [
            abs(float(max_point[0] - min_point[0])),
            abs(float(max_point[1] - min_point[1])),
            abs(float(max_point[2] - min_point[2])),
        ]
        candidate_indices = [index for index in range(3) if index != rotation_axis_index]
        face_axis_index = min(candidate_indices, key=lambda index: sizes[index])

        face_center_values = [
            float(midpoint[0]),
            float(midpoint[1]),
            float(midpoint[2]),
        ]
        face_center_values[face_axis_index] = float(min_point[face_axis_index])
        return Gf.Vec3d(*face_center_values), axis

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

    def _make_next_group_path(self, stage, parent_path):
        used_indices = set()
        parent_prim = stage.GetPrimAtPath(parent_path)
        if parent_prim and parent_prim.IsValid():
            for child in parent_prim.GetChildren():
                name = child.GetName()
                if not name.startswith("group_"):
                    continue
                suffix = name[len("group_"):]
                if suffix.isdigit():
                    used_indices.add(int(suffix))

        index = 0
        while index in used_indices:
            index += 1

        while True:
            group_path = parent_path.AppendChild(f"group_{index}")
            if not stage.GetPrimAtPath(group_path).IsValid():
                return group_path
            index += 1

    def _find_common_xform_parent_path(self, stage, prim_paths):
        if not prim_paths:
            return None

        ancestor_sets = []
        for prim_path in prim_paths:
            ancestors = []
            current_path = prim_path.GetParentPath()
            while current_path != current_path.absoluteRootPath:
                prim = stage.GetPrimAtPath(current_path)
                if prim and prim.IsValid() and prim.IsA(UsdGeom.Xform):
                    ancestors.append(current_path)
                current_path = current_path.GetParentPath()
            ancestor_sets.append(ancestors)

        first_ancestors = ancestor_sets[0]
        for candidate_path in first_ancestors:
            if all(candidate_path in ancestors for ancestors in ancestor_sets[1:]):
                return candidate_path

        root_xform = self._find_stage_root_xform(stage)
        if root_xform and root_xform.IsValid():
            return root_xform.GetPath()

        return Sdf.Path("/World")

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
