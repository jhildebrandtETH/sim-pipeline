# MAIN_DIRECTORY, ARRAY_OF_REQUESTES_GEOMETRIES, ARRAY_OF_REQUESTED_RPMS,--> SIMULATION_DISPATCHER --> NONE

import itertools
from pathlib import Path
import os
from preprocessing import preprocessing
from openfoamSimulation import openfoamSimulation

### CONTROL ###
#requested_geometries_array = ["10x5E", "10x7E", "10x8E", "11x7E", "11x8E", "8x4E", "8x6E", "8x8E", "9x6E", "9x9E"]
requested_geometries_array = ["10x5E", "10x7E", "10x8E", "11x7E", "11x8E", "9x6E", "9x9E"] # 8xX series make problems with STL generation!
requested_geometries_array = ["10x7E"] # 8xX series make problems with STL generation!


requested_RPMS = [1000]

pipeline_main_directory = r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline"

simulations_directory = r"C:\Users\jonas\Downloads\SimulationSpace"

convergence_monitoring_revolutions_count = 3

convergence_tolerance = 1e-3

cores_to_use = 24


### CONTROL END ###

# Generate all combinations as a list of tuples (geometry, rpm)
all_combinations = list(itertools.product(requested_geometries_array, requested_RPMS))


# Example: Printing the results


# Create all subfolders in simulations_directory with the name PE0_NAME@RPM_COUNT
for geometry, rpm in all_combinations:

    folder_name = geometry + "@" + str(rpm)
    path = Path(os.path.join(simulations_directory, folder_name))
    path.mkdir(parents=True, exist_ok=True)

print("Cases and Subfolders created...")

# Preprocessing
for geometry, rpm in all_combinations:

    folder_name = geometry + "@" + str(rpm)
    simulation_path = Path(os.path.join(simulations_directory, folder_name))
    geometry_string = geometry + "-PERF"
    preprocessing(geometry_string, rpm, pipeline_main_directory, simulation_path, cores_to_use)

print("Preprocessing completed...")


# Launch Simulations
for geometry, rpm in all_combinations:

    folder_name = geometry + "@" + str(rpm)
    simulation_path = Path(os.path.join(simulations_directory, folder_name))
    simulation_name = geometry + "_" + str(rpm) + "RPM"
    openfoamSimulation(simulation_name, simulation_path, convergence_tolerance, rpm, convergence_monitoring_revolutions_count)

print("Simulations completed...")
###
