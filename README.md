# Simulation Pipeline – Quick Usage

## Requirements

* Docker Engine **running**
* Conda environment `of_pipeline_env` installed and activated

### Setup

```bash
conda env create -f of_pipeline_env.yml
conda activate of_pipeline_env
```

Check Docker:

```bash
docker info
```

---

## Run Pipeline

```bash
python main.py --sim-dir <path> --geometries <list> --rpms <list>
```

### Example

```bash
python main.py --sim-dir /scratch/simulations --geometries 10x7E --rpms 7000
```

---

## Notes

* STL files must be in:

  ```
  STLs/
  ```
* Geometry names must match STL filenames (e.g. `10x7E.stl`)
* Docker must be running before execution
