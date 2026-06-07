# Bring your own data

This document walks through using iSAGE on a fresh dataset.

The platform is domain-agnostic: any image collection with enumerable classes
works. The only domain-specific input is a YAML file describing your dataset
and (optionally) a YAML file describing the training configuration.

## 1. Organize your images

Place training images and (optional) validation images under a directory. The
images should be tiled to a fixed size — the paper used 256×256 (BsB Aerial)
and 512×512 (Vaihingen). Pick a tile size that suits your GPU and the spatial
scale of your classes.

A typical layout:

```
my_dataset/
├── train_images/
│   ├── 0.png
│   ├── 1.png
│   └── ...
├── val_images/        # optional, but used for metric reporting
│   └── ...
└── val_masks/         # required if val_images is set; dense PNG masks
    └── ...
```

For validation, the masks should be PNGs of the same dimensions as the
validation images, with each pixel containing the class index (not RGB
color). Pixels you want excluded (e.g., undefined, void) should equal
`ignore_index`.

You do **not** need any training masks. The iSAGE workflow generates them
from your clicks.

## 2. Write a dataset YAML

Copy `configs/datasets/vaihingen_1k_v3.yaml` to
`configs/datasets/my_dataset.yaml` and edit:

```yaml
name: MY_DATASET
paths:
  train_images: my_dataset/train_images
  train_dense_masks: null            # not needed — iSAGE creates sparse masks
  train_sparse_masks: my_dataset/sparse_masks   # where session masks live
  val_images: my_dataset/val_images
  val_masks: my_dataset/val_masks
  test_images: null
  test_masks: null
classes:
  num_classes: 3                     # number of FOREGROUND classes
  ignore_index: 3                    # always num_classes (the unlabeled marker)
  names:
    - road
    - building
    - vegetation
  colors:
    - [128, 64, 128]
    - [70, 70, 70]
    - [107, 142, 35]
image:
  width: 512
  height: 512
  channels: 3                        # 3 for RGB, 4 for IRRG, etc.
```

Paths are resolved relative to the notebook's working directory. Use absolute
paths if the data lives outside the repo.

## 3. (Optional) Pick or write a training YAML

`configs/training/unet_efficientnet_b7.yaml` is the canonical setup used in
the paper. For most use cases, copy it and adjust:

- `model.architecture` and `model.encoder` to a smaller backbone if you have
  limited VRAM (e.g., `Unet` + `efficientnet-b0` runs on 8 GB).
- `training.num_epochs` per iteration. 100–500 depending on dataset size.
- `training.batch_size`.
- `loss.train` — pick from EWDL family (`ewdl_multi`, `ewdl_binary`,
  `dwcdl_multiclass`, etc.) or fall back to plain `dice_loss` or
  `cross_entropy` to compare.

## 4. Edit and run the notebook

Open `isage_workflow.ipynb` and change two lines in Cell 2:

```python
DATASET_CONFIG_PATH = 'configs/datasets/my_dataset.yaml'
TRAINING_CONFIG_PATH = 'configs/training/unet_efficientnet_b7.yaml'
```

Then change Cell 3:

```python
SESSION_NAME = 'MY_DATASET_RUN1'
```

Run cells 1–3 once. From cell 3 onward, the session is created on disk under
`Sessions/MY_DATASET_RUN1/`.

## 5. Annotate and train

- **Cell 4** launches the PyQt5 widget. Left-click on a pixel to add a point
  for the currently-selected class (toolbar on the left). Right-click on an
  existing point to remove it. Close the window when you're done with the
  iteration.
- **Cell 5** runs training, generates predictions for the new iteration's
  overlay, and advances to `iteration_{N+1}`.

Repeat 4 → 5 → 4 → 5. The model in `iteration_N/models/best_model.pth` is
the model trained on all annotations up to iteration N.

## Seed annotations (iteration 0)

For iteration 0 there is no prior model, so the annotator opens with no
overlay. Drop a few clicks on each class to give the first training run
something to learn from. The paper used a fixed budget of 1 pixel per class
per frame at iteration 0 (the same adversarial cap used at every later
iteration), but this is not a constraint — you can place as many seed clicks
as you want.

## Sanity checks before training

- Verify image and mask dimensions match (width, height) in the YAML.
- `ignore_index` must equal `num_classes` (not `num_classes - 1`).
- Validation masks should use the same class indices as the YAML names.
- If you change the YAML mid-session, regenerate masks: the next training
  run will use whatever masks are on disk under `iteration_N/masks/`.
