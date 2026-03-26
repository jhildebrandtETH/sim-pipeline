
## --->  PE0_FILE_PATH, RPM, TARGET_DIRECTORY, CORE_TEMPLATE_DIRECTORY... --> THIS FUNCTION ---> READY TO RUN OPENFOAM SIMULATION FOR PARTRICULAR CASE

import shutil
import os
from PropGeom.main import generateSTL

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
                lines.append(f"{target_var} {new_value}\n")
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


def preprocessing(PE0_NAME, RPM_COUNT, MAIN_DIRECTORY, TARGET_DIRECTORY):

 
    #1. duplicate Core Template to target directory

    core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template")

    shutil.copytree(core_template_directory, TARGET_DIRECTORY, dirs_exist_ok=True)

    #2. know about what simulation we are talking about (geometry facts & RPM)
    

    #3. adapt all exisiting parameters based on certain rules

    parameters_file_path = os.path.join(TARGET_DIRECTORY, 'parameters.cpp')
    update_parameters(parameters_file_path, 'omega_val', RPM_COUNT)


    #4. generate STL file from requestes described geometry (other function)


    target_stl_path = os.path.join(TARGET_DIRECTORY, "constant", "triSurface")

    generateSTL(PE0_NAME, MAIN_DIRECTORY, target_stl_path, interpolation_points)
 



    #5. deal with all the other geometry related stuff like nonConformalCouples...

    #6. provide all prepared folder bundle to the desired location

    return None


#preprocessing("9x7-PERF", 1707, r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline", r"C:\Users\jonas\Downloads\New folder")

#generateSTL("5x3E-PERF", r"C:\Users\jonas\OneDrive\ETH\FS2026\Semester Project\GITHUB\Repository\sim-pipeline", r"C:\Users\jonas\Downloads\New folder", 100)