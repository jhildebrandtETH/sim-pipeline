# UAV Propeller CFD Pipeline

## Overview

Automated pipeline to generate meshes and run OpenFOAM simulations for UAV propellers.

Supports both steady and transient rotating domain approaches.

---

## Requirements

* Docker Engine **running**
* Conda environment:

```bash
conda env create -f of_pipeline_env.yml
conda activate of_pipeline_env
docker info
```

---

## Usage

```bash
python main.py --sim-dir <path> --geometries <list> --rpms <list> --mode <mode> --field-init <mode> --study <mode> --study-parameter <string> --study-file <string> --study-values <string>
```

### Key Arguments

* `--sim-dir` → Output directory
* `--geometries` → STL names (without `.stl`)
* `--rpms` → Rotation speeds
* `--mode` → Simulation approach:

  * `MRF` (steady)
  * `AMI` (transient)

* `--field-init` → Sequential field initialization:

  * `on` (Flow fields of preceding simulation run of same geometry will be used to initialise flow field of following one)
  * `off` (Flow fields are always zero initialised)

* `--study` → Study parameter mode:

  * `on` (Study feature activated)
  * `off` (default: normal operation with study off)

---

### Study Configuration (when `--study on`)

* `--study-parameter` → Name of the parameter to vary  
  *(e.g. `refinementLevel`, `nSurfaceLayers`, `cellSize`)*

* `--study-file` → File where the parameter is located  
  *(e.g. `snappyHexMeshDict`, `controlDict`)*

* `--study-values` → Values to sweep over  
  Supported input formats:

  * Scalar values (separated by `...`):
    ```bash
    7...8...9
    ```

  * Vector / tuple values (separated by `...`):
    ```bash
    (10 12 10)...(12 14 12)
    ```

  → `...` is used as the separator between study cases.
  → Each entry is treated as one study case and passed exactly to the target parameter.
  *(e.g. `3 4 5` or `(1 1 1) (2 2 2)`)*

---

## Study Mode Behavior

When `--study on` is used:

* `--geometries` must contain **exactly one** entry
* `--rpms` must contain **exactly one** entry
* The pipeline runs **one simulation per study value**
* Each case is stored in its own folder:

```bash
<geometry>_<rpm>RPM_<parameter>_<value>
```

---

## Example

```bash
python main.py --sim-dir /scratch/simulations --geometries 10x7E --rpms 7000 --mode MRF --field-init on
```

---

## Example: Parameter Study

```bash
python main.py \
  --sim-dir /scratch/simulations \
  --geometries 10x7E \
  --rpms 7000 \
  --mode AMI \
  --study on \
  --study-parameter refinementLevel \
  --study-file snappyHexMeshDict \
  --study-values 3...4...5
```

---

## Notes

* STL files must be in `STLs/`
* Names must match (e.g. `10x7E.stl`)
* RPM values should be entered in order of desired execution (will have effect if field init is on)
* Simulation settings are defined in the `Parameters/` folder files
* AMI = more accurate, slower
* MRF = faster, good for initial studies

