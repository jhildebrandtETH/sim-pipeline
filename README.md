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
python main.py --sim-dir <path> --geometries <list> --rpms <list> --mode <mode> --field-init <mode>
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


---

## Example

```bash
python main.py --sim-dir /scratch/simulations --geometries 10x7E --rpms 7000 --mode MRF --field-init on
```

---

## Notes

* STL files must be in `STLs/`
* Names must match (e.g. `10x7E.stl`)
* RPM values should be entered in order of desired execution (will have effect if field init is on)
* Simulation settings are defined in the `Parameters/` folder files
* AMI = more accurate, slower
* MRF = faster, good for initial studies
