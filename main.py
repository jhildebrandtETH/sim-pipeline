import argparse
import itertools
from pathlib import Path
import os

from preprocessing import preprocessing
from openfoamSimulation import openfoamSimulation


def main() -> None:
    # Repository root
    pipeline_main_directory = Path(__file__).resolve().parent

    # -------- CLI ARGUMENTS --------
    parser = argparse.ArgumentParser(
        description="Dispatch OpenFOAM simulations."
    )

    parser.add_argument(
        "--sim-dir",
        type=Path,
        required=True,
        help="Directory where simulation cases will be created",
    )

    parser.add_argument(
        "--geometries",
        nargs="+",
        required=True,
        help="List of geometries (e.g. 10x7E 11x8E)",
    )

    parser.add_argument(
        "--rpms",
        nargs="+",
        type=int,
        required=True,
        help="List of RPM values (e.g. 6000 7000)",
    )

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["AMI", "MRF"],
        help="Choose rotational approach (AMI or MRF)",
    )

    parser.add_argument(
        "--field-init",
        type=str,
        default="on",
        choices=["on", "off"],
        help="Choose if flow initialization should be used. Optional. Default: on",
    )

    args = parser.parse_args()

    simulations_directory = args.sim_dir.resolve()
    simulations_directory.mkdir(parents=True, exist_ok=True)

    requested_geometries_array = args.geometries
    requested_RPMS = args.rpms

    # -------- SETTINGS --------
    convergence_monitoring_revolutions_count = 1000
    convergence_tolerance = 1e-3
    cores_to_use = 24

    # -------- PIPELINE --------
    for geometry in requested_geometries_array:
        previous_simulation_path = None

        for rpm in requested_RPMS:
            folder_name = f"{geometry}_{rpm}RPM"
            simulation_path = simulations_directory / folder_name
            simulation_path.mkdir(parents=True, exist_ok=True)

            stl_path = pipeline_main_directory / "STLs" / f"{geometry}.stl"

            print(f"\n--- Running case: {geometry} @ {rpm} RPM @ {args.mode} @ Field Init: {args.field_init} ---")

            # Decide whether this case should use field initialization
            use_previous_init = (
                args.field_init == "on" and previous_simulation_path is not None
            )

            preprocessing(
                STL_PATH=stl_path,
                RPM_COUNT=rpm,
                MAIN_DIRECTORY=pipeline_main_directory,
                TARGET_DIRECTORY=simulation_path,
                CORES_TO_USE=cores_to_use,
                MODE=args.mode,
                INIT_FROM_PREVIOUS=use_previous_init,
                PREVIOUS_SIMULATION_PATH=previous_simulation_path
            )

            simulation_name = f"{geometry}_{rpm}RPM"

            openfoamSimulation(
                simulation_name=simulation_name,
                simulation_working_directory=simulation_path,
                convergence_tolerance=convergence_tolerance,
                rpm_count=rpm,
                convergence_window_revolutions=convergence_monitoring_revolutions_count,
                MODE=args.mode,
                initialize_from_previous=use_previous_init,
                previous_simulation_path=previous_simulation_path,
            )

            # After successful run, store current case as source for next RPM of same geometry
            previous_simulation_path = simulation_path

    print("\nAll simulations completed.")


if __name__ == "__main__":
    main()