# GitHub setup checklist

The exact fields to fill in when creating `osmarluiz/iSAGE` on GitHub, plus
the metadata table the Software Impacts paper will ask for. Bullets
ordered by where they appear in the GitHub UI.

## 1. Repository creation

Visit <https://github.com/new>. Fill in:

| Field | Value |
|---|---|
| Owner | `osmarluiz` |
| Repository name | `iSAGE` |
| Description (160 chars max) | _see candidates below_ |
| Visibility | Public |
| Initialize with README | **No** (we have one) |
| Add .gitignore | **No** (we have one) |
| Add a license | **No** (we have MIT in `LICENSE`) |

### Description candidates (pick one, edit as you like)

These are tuned for the 160-character GitHub description field, the one
that shows under the repo name on the org page and in search results:

**A. Direct (recommended for ESWA reviewers):**
> Iterative Sparse Annotation Guided by Expert — semantic segmentation from human clicks on confident model errors, plus Error-Weighted Dice Loss.

**B. Concrete (recommended for broader audience):**
> Train semantic segmentation models from a handful of expert clicks per image. No pseudo-labels, no propagation. PyQt5 annotator + EWDL + iterative loop.

**C. Result-first (recommended for citing in the paper):**
> Matches fully-supervised segmentation at 0.011 % labeled pixels by routing human clicks to confident model errors. Annotator + Error-Weighted Dice Loss + JSON-as-dataset.

## 2. Topics

Add these in the *About* sidebar → *Topics*:

```
semantic-segmentation
active-learning
sparse-annotation
human-in-the-loop
remote-sensing
pytorch
annotation-tool
jupyter
click-based-annotation
error-weighted-loss
expert-systems
```

## 3. About sidebar

| Field | Value |
|---|---|
| Description | (the one you picked above) |
| Website | `https://github.com/osmarluiz/sial-paper` (the paper repo) once it's public |
| Topics | (from §2) |
| Include in the home page | ☑ Releases · ☑ Packages · ☐ Deployments · ☑ Used by · ☑ Contributors · ☐ Environments |

## 4. Initial push

Once the repo is created (empty), from `/mnt/d/projects/isage`:

```bash
git remote add origin https://github.com/osmarluiz/iSAGE.git
git branch -M main
git push -u origin main
```

(Or if you used `git init -q` with `master`, rename to `main` first:
`git branch -m master main`.)

## 5. First release tag

After the push:

```bash
git tag -a v1.0.0 -m "Initial release accompanying the ESWA submission"
git push origin v1.0.0
```

Then on GitHub UI → *Releases* → *Draft a new release* → select `v1.0.0` →
title `iSAGE v1.0.0` → body from `CHANGELOG.md` `[1.0.0]` section →
*Publish release*. This triggers the Zenodo integration (§7).

## 6. Repo settings

- **Default branch:** `main`
- **Branch protection rules** (optional, recommended): require pull request
  before merging to `main`, require status checks to pass (the `tests` CI).
- **Issues:** enabled
- **Discussions:** enabled (for questions about BYOD usage)
- **Pages:** keep disabled for now (no docs site planned)

## 7. Zenodo integration

1. Log in to <https://zenodo.org> with your GitHub account.
2. <https://zenodo.org/account/settings/github/> → flip `osmarluiz/iSAGE`
   to On.
3. Now the *next* GitHub release (or re-publishing v1.0.0) creates a
   Zenodo archive automatically and assigns a DOI.
4. Copy the DOI badge MD from the Zenodo record page and paste it into
   `README.md` above the existing content:
   ```markdown
   [![DOI](https://zenodo.org/badge/<ID>.svg)](https://zenodo.org/badge/latestdoi/<ID>)
   ```
5. Update `CITATION.cff` with the DOI field.

## 8. README badges (after CI is green and DOI exists)

Add to the very top of `README.md`:

```markdown
[![tests](https://github.com/osmarluiz/iSAGE/actions/workflows/test.yml/badge.svg)](https://github.com/osmarluiz/iSAGE/actions/workflows/test.yml)
[![DOI](https://zenodo.org/badge/<ID>.svg)](https://zenodo.org/badge/latestdoi/<ID>)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
```

---

## Software Impacts paper — metadata table

The first page of every Software Impacts paper requires a "Code metadata"
table. Fill in once the GitHub repo and Zenodo DOI are live:

| Nr. | Code metadata description | Please fill in this column |
|---|---|---|
| C1 | Current code version | v1.0.0 |
| C2 | Permanent link to code/repository used for this code version | https://github.com/osmarluiz/iSAGE/tree/v1.0.0 |
| C3 | Permanent link to Reproducible Capsule | _N/A_ |
| C4 | Legal Code License | MIT |
| C5 | Code versioning system used | git |
| C6 | Software code languages, tools, and services used | Python 3.9+, PyTorch, PyQt5, Jupyter, segmentation_models.pytorch (vendored), pytest, GitHub Actions |
| C7 | Compilation requirements, operating environments and dependencies | See `requirements.txt`. CUDA-capable GPU recommended for training. Display required for the PyQt5 annotator (X server or native). |
| C8 | If available, link to developer documentation/manual | https://github.com/osmarluiz/iSAGE/tree/main/docs |
| C9 | Support email for questions | osmarlfcarvalho@gmail.com (or via GitHub Issues / Discussions) |

(Software Impacts also requires a "Software metadata" table — Elsevier
provides the template at <https://www.elsevier.com/journals/software-impacts/2665-9638/guide-for-authors>.)
