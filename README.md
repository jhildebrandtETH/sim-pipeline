# UAV Propeller CFD Pipeline

## Overview

Automated pipeline to generate meshes and run OpenFOAM simulations for UAV propellers.

Supports:
- MRF (steady)
- AMI (transient)

Includes:
- Automated meshing (blockMesh + snappyHexMesh)
- Parallel execution
- Convergence monitoring
- Postprocessing & report generation
- Study mode
- Resume capability

---

## Requirements

- Docker Engine **running**
- Conda environment:

```bash
conda env create -f of_pipeline_env.yml
conda activate of_pipeline_env
docker info
```

---

## Usage

```bash
python main.py --sim-dir <path> --geometries <list> --rpms <list> --mode <mode> --field-init <mode> --cores <int> --study <mode> --study-parameter <string> --study-file <string> --study-values <string> --resume
```

---

## Key Arguments

- `--sim-dir` → Output directory  
- `--geometries` → STL names (without `.stl`)  
- `--rpms` → Rotation speeds  
- `--cores` → Number of cores  
- `--mode` → `MRF` or `AMI`  
- `--field-init` → Sequential initialization (`on` / `off`)  
- `--study` → Enable parameter study (`on` / `off`)  
- `--resume` → Resume previous batch  

---

## Resume Feature

The pipeline supports **automatic resume of interrupted simulations**.

### Behavior

- Detects latest valid timestep (ignores `0` folder)
- Checks required fields (e.g. `U`, `p`)
- Skips corrupted or incomplete timesteps
- Continues simulation from last valid state

### Important ⚠️

> **Each simulation run should use a NEW directory**  
> (**one simulation_run → one folder**)

Reason:
- Avoids undefined behavior from mixed states
- Prevents conflicts with existing postProcessing data
- Ensures reproducibility and stability

### Example: Resume

```bash
python main.py \
  --sim-dir /scratch/simulations \
  --resume on
```

→ Continues all pending or interrupted cases inside the simulation directory.

---

## Study Mode

Enable with:

```bash
--study on
```

### Configuration

- `--study-parameter` → Parameter to vary  
- `--study-file` → File containing parameter  
- `--study-values` → Values separated by `...`

Examples:

```bash
7...8...9
(10 12 10)...(12 14 12)
```

---

## Study Behavior

- Requires **exactly one geometry** and **one RPM**
- Runs one simulation per value
- Each case stored in its own folder:

```bash
<geometry>_<rpm>RPM_<parameter>_<value>
```

---

## Example

```bash
python main.py \
  --sim-dir /scratch/simulations \
  --geometries 10x7E \
  --rpms 7000 \
  --mode AMI \
  --cores 24 \
  --field-init on
```

---

## Example: Parameter Study

```bash
python main.py \
  --sim-dir /scratch/simulations \
  --geometries 10x7E \
  --rpms 7000 \
  --mode AMI \
  --cores 24 \
  --study on \
  --study-parameter refinementLevel \
  --study-file snappyHexMeshDict \
  --study-values 3...4...5
```

---

## Notes

- STL files must be located in `STLs/`
- Names must match (e.g. `10x7E.stl`)
- RPM order matters if `field-init on`
- Simulation parameters are defined in `Parameters/`
- AMI = more accurate, slower  
- MRF = faster, suitable for initial studies
