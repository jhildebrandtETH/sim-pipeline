## --->  PE0_FILE_PATH, RPM, TARGET_DIRECTORY, CORE_TEMPLATE_DIRECTORY... --> THIS FUNCTION ---> READY TO RUN OPENFOAM SIMULATION FOR PARTRICULAR CASE

import shutil
import os
import math
interpolation_points = 100


def update_parameters(file_path, target_var, new_value):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    lines = []
    updated = False

    # Read the file and modify the specific line
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == target_var:
                lines.append(f"{target_var} {new_value};\n")
                updated = True
            else:
                lines.append(line)

    # Write the changes back to the file
    if updated:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print(f"Successfully updated {target_var} to {new_value}.")
    else:
        print(f"Variable '{target_var}' not found in the file.")

# Usage
#update_parameters(r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline\Core Template\parameters.cpp", 'omega_val', 850.50)


def preprocessing(STL_PATH, RPM_COUNT, MAIN_DIRECTORY, TARGET_DIRECTORY, CORES_TO_USE, MODE):

 
    #1. duplicate right Core Template to target directory (AMI or RMF approach)

    if MODE == "MRF":

        core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template MRF")
    
    elif MODE == "AMI":

        core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template AMI")

    else:
        print("Unknown mode was passed to the pipeline...")
        return None


    shutil.copytree(core_template_directory, TARGET_DIRECTORY, dirs_exist_ok=True)
    
    # copy parameters folder to case folder

    parameters_path_main = os.path.join(MAIN_DIRECTORY, 'Parameters')

    shutil.copytree(parameters_path_main, os.path.join(TARGET_DIRECTORY, 'Parameters'))

    #


    #2. know about what simulation we are talking about (geometry facts & RPM)
    

    #3. adapt all exisiting parameters based on certain rules

    rotational_parameters_file_path = os.path.join(TARGET_DIRECTORY, 'Parameters', 'rotational_parameters.cpp')

    omega = RPM_COUNT * 2 * math.pi / 60

    update_parameters(rotational_parameters_file_path, 'omega_val', omega)


    decomposeParDict_parameters_file_path = os.path.join(TARGET_DIRECTORY, 'Parameters', 'decomposeParDict_parameters.cpp')

    update_parameters(decomposeParDict_parameters_file_path, 'numberOfSubdomains', CORES_TO_USE)


    #4. generate STL file from requestes described geometry (other function)


    target_stl_path = os.path.join(TARGET_DIRECTORY, "constant", "triSurface", "propellerTip.stl")

    #generateSTL(PE0_NAME, MAIN_DIRECTORY, target_stl_path, interpolation_points)

    shutil.copy(STL_PATH, target_stl_path)
 



    #5. deal with all the other geometry related stuff like nonConformalCouples...

    #6. provide all prepared folder bundle to the desired location

    

    return None


#preprocessing("9x7-PERF", 1707, r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline", r"C:\Users\jonas\Downloads\New folder")

#generateSTL("5x3E-PERF", r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline", r"C:\Users\jonas\Downloads\New folder", 100)