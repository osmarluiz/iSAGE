# Annotator reference

Complete reference for the iSAGE PyQt5 annotator widget. The annotator opens
from the notebook's annotate cell (cell 3) or from the CLI's `annotate`
subcommand. It shows one image at a time with the current model's prediction
overlaid; clicks become entries in the JSON record that drives the next
training iteration.

## Mouse

| Action | Effect |
|---|---|
| **Left-click on empty area** | Add point of currently-selected class at the exact pixel |
| **Left-click near an existing point** | Start dragging that point (release to drop at new location) |
| **Right-click near a point** | Delete that point |
| **Middle-click and drag** | Pan the image |
| **Mouse wheel** | Zoom in / out toward the cursor (8% per notch) |
| **Space + Left-click** | Force-add a new point, even on top of an existing one (bypasses drag) |

The annotator uses a spatial index, so "near" detection is fast even with
thousands of points per image.

## Keyboard shortcuts

### Class selection

| Key | Effect |
|---|---|
| `1`, `2`, ..., `9` | Select class N as the current annotation class |

The number of available class shortcuts equals `min(num_classes, 9)`. With more
than nine classes the rest are selectable from the control panel buttons only.

### Navigation

| Key | Effect |
|---|---|
| `→` (Right arrow) | Next image |
| `←` (Left arrow) | Previous image |
| `Esc` | Exit the annotator (auto-saves annotations) |

### Zoom

| Key | Effect |
|---|---|
| `Ctrl + +` | Zoom in (15% step) |
| `Ctrl + -` | Zoom out (15% step) |
| `Ctrl + 0` | Reset zoom to fit |

Mouse-wheel zoom uses a finer 8% step and zooms toward the cursor position.
Ctrl+keyboard zoom uses 15% steps and zooms around the center.

### Editing

| Key | Effect |
|---|---|
| `Ctrl + Z` | Undo the last point add, remove, or drag |

Undo applies to a stack maintained per image. Switching images clears the
stack for the new image; the previous image's annotations are persisted to
JSON when the navigation happens.

### Overlay preview (hold-to-show)

| Key | Effect |
|---|---|
| Hold `G` | Show the ground-truth mask overlay (only while held) |
| Hold `P` | Show the prediction mask overlay (only while held) |

Both keys are *hold-to-preview*: the overlay state is restored on key release.
This is useful for cross-checking the model's prediction against the GT
without changing the persistent overlay opacity sliders.

### Help

| Key | Effect |
|---|---|
| `F1` | Open the in-app help window |

## UI panels

The annotator window contains five regions arranged around the central canvas.

### Class panel (left)

One button per class, color-matched to the class colors defined in
`configs/datasets/<name>.yaml` under `classes.colors`. Clicking a button
selects that class as the current annotation target; clicking again toggles
the visibility of points of that class on the canvas. An *Add Class* button
at the bottom of the panel registers a new class on the fly (useful when
extending an existing session with a new category).

### Canvas (center)

The image with all current annotations rendered as colored circles. Points
added in the current session are drawn with a white halo to distinguish them
from prior-iteration annotations. The canvas supports pan, zoom, and all the
mouse interactions documented above.

### Overlay opacity sliders (left, below class panel)

Two horizontal sliders control the persistent overlay opacity:

- **Prediction overlay (0--100%, default 50%)** -- transparency of the model's
  prediction mask. Enable from the *Display* checkbox above the slider.
- **Ground-truth overlay (0--100%, default 30%)** -- transparency of the
  reference mask, when present in the dataset.

The hold-to-preview keys (`P` and `G`) are independent of these sliders --
they temporarily flip the overlay's visibility without changing the slider
value.

### Status panel (right)

- **Image info.** Current image filename, dimensions, and channel count.
- **Annotation counts.** Number of points per class for the current image and
  the total across all images in the iteration.
- **Interactive minimap.** Thumbnail of the current image with a rectangle
  indicating the viewport when zoomed in. Click anywhere on the minimap to
  recenter the main view; drag the viewport rectangle to pan.

### Top navigation

Session name, iteration number, and a *Jump to image* input that takes an
image index and navigates to it directly.

### Bottom navigation

Previous / Next image buttons (equivalent to the arrow keys), a *Save* button
(annotations also auto-save on navigation and on close), and the total
progress counter (`current / total` images).

## Workflow tips

- **Hold `P` before clicking.** Preview the prediction first to identify
  confident errors, then release `P` and click the wrong pixel. The workflow
  is built around this loop.
- **Use the minimap when zoomed in.** Pan to error regions visually instead
  of dragging across many small movements.
- **Switch classes mid-image.** Press a number key to change the current
  class without leaving the canvas; the next click goes to the new class.
- **Drag, don't redo.** If a point is in roughly the right area but slightly
  off, left-click the point and drag it to the correct location. Cheaper
  than delete-then-readd, and preserves the JSON history.
- **Iteration boundaries.** Closing the annotator finalizes the iteration's
  JSON record. The next iteration starts with the same points (annotations
  are copied forward) plus whatever the user adds.

## How annotations are stored

Every click is persisted to a JSON file at:

```
Sessions/<name>/iteration_N/annotations/<image_stem>.json
```

The schema is one object per file with an `annotations` array of
`[x, y, class_index]` tuples. See [`json-record-spec.md`](json-record-spec.md)
for the full schema. PNG masks are regenerated from the JSON on each
navigation; the JSON is the source of truth.

## Troubleshooting

- **No prediction overlay visible.** The current iteration may have no
  predictions yet. Predictions are generated by `train` at the end of an
  iteration; iteration 0 typically has no predictions to overlay.
- **Crash on launch.** The `annotator_crash.log` file at the repo root
  collects stack traces. See [GitHub Issues](https://github.com/osmarluiz/iSAGE/issues).
- **Window opens off-screen (multi-monitor setups).** The window opens on
  whichever monitor Qt chose. On Windows, `Alt + Space, M, then arrow keys`
  moves it back to the primary display.
