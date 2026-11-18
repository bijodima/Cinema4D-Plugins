# PoleWire 1.0

PoleWire is a Cinema 4D plugin for building pole-and-wire lines along splines. Use your own pole models, position their wire attachment points, and generate repeated poles connected by sagging wires.

The plugin appears in Cinema 4D as **Pole Wire**. It provides a manager window and embeds the generation code in a Python Generator object in the scene.

## Features

- Open, closed, and multi-segment spline routes.
- Editable base and connector helpers for custom pole models.
- Optional corner and end pole models.
- Vertical placement on editable terrain meshes.
- Global and per-wire sag, radius, and material settings.
- Repeatable random pole rotation and tilt.
- Individual pole position, rotation, visibility, and model overrides.
- Lightweight wire spline preview.
- Pole presets saved as Cinema 4D projects with assets.

## Requirements and compatibility

PoleWire runs inside Cinema 4D and uses its bundled Python environment. No third-party Python packages are imported by the plugin.

Pole models must be editable polygon objects or groups containing editable polygon meshes. Ground objects must also contain editable polygon meshes. Convert procedural inputs to editable geometry before using them.

This source distribution does not establish a verified Cinema 4D version range or cross-platform support matrix. See the release notes of the published build for tested versions and platforms.

## Installation

1. Locate your Cinema 4D preferences folder using the application's preferences controls.
2. Open or create its `plugins` folder.
3. Copy the complete `PoleWire` folder into it. Keep the Python files and `res` directory together.
4. Remove duplicate installations of PoleWire and restart Cinema 4D.
5. Open **Extensions > Pole Wire**, or press **Shift+C** and search for **Pole Wire**.

The folder layout should be:

```text
plugins/
└── PoleWire/
    ├── PoleWire.pyp
    ├── Pole Wire Manager.py
    ├── generator_builder.py
    ├── generator_code.py
    ├── setup_core.py
    ├── preset_library.py
    ├── README.md
    └── res/
        ├── icon.png
        └── ...
```

The manager can be docked in a Cinema 4D layout. Restart and layout restoration should be checked with the specific release you install.

## Quick start

1. Prepare a pole model upright along its local Y axis. Select the complete model root in the Object Manager.
2. Open **Pole Wire** and click **Load Selected Generator / Model**.
3. Assign a spline to **Route Spline**, or click **Create Straight Route**. To use an existing selected spline, click **Use Selected Spline**.
4. Set **New rig connectors** to the required number of wires, from 1 to 8.
5. Click **Create Rig + Generator**.
6. Click **Select Base** and move `PW Base` to the pole's footing.
7. Click **Select Connectors**, expand `PW Connectors`, and move each `Connector` Null to a wire attachment point, such as an insulator.
8. Set spacing, sag, wire radius, and other options. With **Live Update** enabled, edits to a loaded generator apply automatically. Otherwise, click **Apply Settings / Route**.
9. Assign a **Wire Material** if required. Turn **Spline Preview** off before rendering.

Creation initializes spacing, sag, and radius from the model's height. Adjust these values after creating the generator. Existing rigs retain their connector positions.

When creating a route before a generator exists, the status may ask you to load or create a generator. The route is still created and linked in the window; proceed with **Create Rig + Generator**.

## Model preparation

Select the complete source model rather than an individual insulator or mesh inside it. Source geometry remains in the scene and is cloned during generation.

PoleWire adds two direct children to the model root:

```text
Your Pole Model
├── Your geometry
├── PW Base
└── PW Connectors
    ├── Connector 01
    ├── Connector 02
    └── Connector 03
```

`PW Base` defines the footing used for placement. The direct Null children of `PW Connectors` define wire endpoints in child order. Connector positions are initialized approximately; place them precisely on your model.

Keep these helper names intact. Each prepared model needs exactly one base and one connector group. A model with an incomplete or duplicate rig must be repaired before setup.

Keep the source model, route, terrain, and alternative models outside the generated Python Generator hierarchy. The route must also be outside the source pole model.

Positive source scale is supported. Zero scale is rejected; mirrored or sheared transforms are not guaranteed to work correctly.

## Routes and placement

Edit the linked spline to change the line. **Edit Route Points** selects an editable spline and switches to point mode; procedural splines must first be made editable for point editing.

| Control | Effect |
| --- | --- |
| Pole Spacing (cm) | Distance between regular supports along the route. Evaluation uses a minimum spacing of 1 cm. |
| Include End Pole | Adds a support at the final point of each open segment. Closed segments connect back to their first support. |
| Align to Adjacent Spans | Uses the horizontal direction between neighboring supports to orient poles. |
| Poles at Linear Spline Corners | Inserts supports at qualifying vertices of linear splines. |
| Pole Rotation (degrees) | Adds a yaw offset to the generated orientation. |

Corner insertion uses a fixed turn threshold greater than **35 degrees** and may remove nearby regular supports. **Corner Angle** controls alternative model selection; it does not change this insertion threshold. Exact corner insertion is only implemented for linear splines.

Separate spline segments are generated independently, without connecting wires between segments. Branching network junctions are not supported.

## Wire shape and materials

| Control | Effect |
| --- | --- |
| Sag (cm) | Downward midpoint drop relative to the straight line between attachment points. |
| Wire Radius (cm) | Circular Sweep profile radius; evaluation uses a minimum radius of 0.01 cm. |
| Segments per Span | Number of linear subdivisions per wire span, from 4 to 64. |
| Wire Material | Material applied to generated wire Sweeps. |

Sag follows a sampled parabola rather than a physical catenary simulation. Actual sag is capped at one quarter of the distance between the two attachment points. Increasing subdivisions smooths the sampled path at the cost of more geometry.

### Individual wires

1. Load the intended generator.
2. Click **Create / Select Individual Wire Settings**.
3. Select a `Wire 01`, `Wire 02`, or subsequent row in the created settings group.
4. Edit its **User Data** in the Attributes Manager.

| Setting | Effect |
| --- | --- |
| Enabled | Turns that wire on or off across the line. |
| Custom Sag and Radius | Enables this row's sag and radius instead of the global values. |
| Sag (cm) / Radius (cm) | Per-wire shape values when the custom option is enabled. |
| Material | Overrides the global wire material. An empty link uses the global material. |

Rows map to connector child order, not their names. Reordering rows changes the mapping. Extra rows are ignored when the model has fewer connectors. Missing rows use the global settings.

## Corner and end models

1. Assign a model to **Corner Pole Model** or **End Pole Model**.
2. Click **Prepare Corner Rig** or **Prepare End Rig**.
3. Position that model's `PW Base` and connector Nulls.
4. Apply the settings, or use Live Update on a loaded generator.

All models must have the same connector count in matching order. Empty model links fall back to the main pole model.

**Corner Angle (degrees)** selects the corner model when the horizontal turn between neighboring spans exceeds the threshold. It ranges from 1 to 179 degrees and defaults to 35 degrees.

The end model is used at the start of an open segment and at its final support when **Include End Pole** is enabled. Endpoint selection takes priority over corner selection. Closed segments have no end poles.

## Terrain placement

Assign an editable polygon mesh, or a group of polygon meshes, to **Ground Surface**. PoleWire casts vertically at each support position and places its base on the highest intersection. **Ground Offset (cm)** adjusts the height of successful hits.

If a support misses the terrain, it keeps its route height. The generated root name reports how many supports missed. Ground Offset is not applied to missed supports.

Spacing is measured along the route before terrain projection. Terrain placement does not align poles to surface normals. Deformed terrain caches and automatic wire-to-ground clearance are not supported; inspect the result for intersections.

## Pole tilt and variation

**Pole Pitch** and **Pole Bank** tilt poles around their footing. **Random Yaw +/-** and **Random Tilt +/-** add variation in degrees. **Random Seed** produces a repeatable pattern for a given route layout.

Changing the number of supports, segment structure, or route topology can redistribute the random pattern. Wires follow the resulting attachment points.

## Individual pole overrides

1. Finish the route and spacing first.
2. Enter the desired **Pole number for override**, starting at 1.
3. Click **Create / Select Pole Override**.
4. Edit the selected override Null in the Attributes Manager.

Use **Coordinates** to apply local position and rotation offsets from the generated placement. Zero offsets retain the original placement. The parent configuration group's transform is ignored.

The override's User Data includes:

- **Pole Number**: the support affected by this override.
- **Hide Pole (keep wires)**: removes the pole clone while retaining its wire connections.
- **Model (prepared rig)**: replaces this pole with a prepared model using the same connector count and order.

Numbering follows the route across spline segments. Changing spacing, spline direction, inserted corners, or segment structure can change which support a number identifies. To reset a pole completely, delete its override Null. To retain the row, zero its offsets, clear its model link, and disable Hide Pole.

## Preview and rendering

**Spline Preview** replaces wire Sweeps with bare spline paths to reduce wire geometry. Pole models remain at full detail.

**Turn Spline Preview off before rendering.** In preview mode PoleWire does not generate renderable wire Sweeps. The setting is manual and does not switch automatically for rendering.

## Pole presets

**Save Pole Preset** saves the currently assigned source model and rig as a Cinema 4D project with assets. Choose a new folder name; existing folders are not overwritten.

**Load Pole Preset** imports the preset's `Pole.c4d` into the active document. Assign a route, then click **Create Rig + Generator**.

A preset contains one model root and its associated assets. It does not export the complete line, route, generator settings, or per-pole overrides. A file with multiple model roots is rejected.

## Editing existing scenes

Select the intended PoleWire Python Generator and click **Load Selected Generator / Model**. Selecting a source model also loads its generator when exactly one matching generator exists.

Opening the manager does not modify the scene. Applying settings updates the embedded generator code for supported older parameter layouts, with Undo support. Unsupported parameter layouts are rejected.

The window synchronizes with changes to the loaded generator's parameters. **Live Update** controls edits sent from the window; turning it off does not stop incoming synchronization.

When switching lines or documents, explicitly load the intended generator again. The manager attempts to reconnect to its loaded generator after Undo/Redo.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Pole Wire is missing from the command search | Keep the complete plugin folder together, remove duplicate installations, restart Cinema 4D, and inspect the Python console for registration errors. |
| The manager says no generator is loaded | Create a generator, or select an existing one and click Load Selected Generator / Model. |
| A model is rejected | Select the complete model root and ensure it contains editable polygon geometry and has nonzero scale. |
| A variant fails to generate | Check its base, connector group, and matching connector count. |
| Wires attach to the wrong locations | Check connector positions and child order on every model type. |
| Wires are absent in the render | Disable Spline Preview, check per-wire Enabled settings, and verify the route has at least two supports. |
| Some poles ignore terrain | Check editable ground coverage at their horizontal positions and read the generated root name. |
| Generation stops above 500 poles | Increase spacing or simplify the route; inserted corner supports also count toward the limit. |
| The window edits the wrong line | Select and explicitly load the intended generator. |
| Generation returns an empty result | Inspect the manager status and the generated root object's name for configuration errors. |

## Limits

- Maximum 500 supports across the route, including inserted corner supports.
- From 1 to 8 connectors per prepared model.
- No branching junction solver or automatic cable clearance.
- Exact vertex support insertion only on linear splines.
- Editable polygon geometry required for model preparation and ground intersection.
- Mirrored and sheared source transforms are not guaranteed.
- Support numbering and random variation depend on route structure.

## Source layout

| File | Purpose |
| --- | --- |
| PoleWire.pyp | Cinema 4D command registration and window restoration. |
| Pole Wire Manager.py | Manager UI, setting synchronization, overrides, and actions. |
| generator_builder.py | Python Generator creation and parameter definitions. |
| generator_code.py | Embedded scene generation logic. |
| setup_core.py | Model bounds, rig creation, and setup helpers. |
| preset_library.py | Preset project saving and import. |
| res/ | Command icon and resource files. |
