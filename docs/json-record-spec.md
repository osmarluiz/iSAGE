# Annotation record format

Each annotation in iSAGE is a single JSON file per image, stored under
`Sessions/<name>/iteration_N/annotations/<image_stem>.json`. The file is the
**dataset itself** — there is no separate "raw" form. Everything the trainer
sees flows from this file through a deterministic mask generator
(`src/session/mask_utils.batch_json_to_masks`).

## Schema

```json
{
  "format_version": "1.0",
  "image": {
    "name": "0.png",
    "width": 512,
    "height": 512
  },
  "iteration": 4,
  "created_at": "2025-11-20T12:51:20.896643Z",
  "annotations": [
    [124, 48, 0],
    [388, 182, 3],
    [503, 164, 4]
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `format_version` | string | Schema version. Current: `"1.0"`. |
| `image.name` | string | Filename of the source image. The mask generator looks for this name in the dataset's `train_images` directory. |
| `image.width`, `image.height` | int | Image dimensions in pixels. The generated mask matches these. |
| `iteration` | int | Which iteration produced this record (0 = seed). |
| `created_at` | string | UTC ISO 8601 timestamp. |
| `annotations` | array of `[x, y, class_index]` | One entry per click. `x ∈ [0, width-1]`, `y ∈ [0, height-1]`, `class_index ∈ [0, num_classes-1]`. |

## Coordinate convention

`[x, y]` is column-first, row-second, zero-indexed from the top-left corner of
the image. `(0, 0)` is the upper-left pixel; `(width-1, height-1)` is the
lower-right.

## Class indices

The integer in the third position of each annotation is the class index, not
an RGB color. The mapping from index to human-readable name and color is in
the dataset YAML (`configs/datasets/<name>.yaml`, under the `classes:` key).
The class with index equal to `ignore_index` is excluded from training and
should not appear in `annotations`.

## Mask generation

The dataloader does not read the JSON files directly. Before training, the
session manager calls `batch_json_to_masks` which writes one PNG per JSON
under `iteration_N/masks/`. Each output mask is the same size as the source
image, filled with `ignore_index` (default: `num_classes`), with the value at
each annotated `[x, y]` set to the corresponding class index.

This separation has three consequences:

1. The JSON record is a self-contained audit trail — independent of training
   preprocessing, versionable, diffable, replayable.
2. Mask generation is deterministic: same JSONs + same converter = same masks,
   bit-for-bit.
3. The dataset is portable: JSON files + the converter are sufficient to
   reconstruct supervision, without the annotation GUI or any UI state.

## Editing records by hand

Because each entry is a single point, fixing a mislabeled click is a
single-line edit in the JSON. Remove the offending tuple, save, regenerate
the mask, retrain — no need to re-open the annotator. For the same reason,
records are easily merged across annotators by concatenating `annotations`
arrays.
