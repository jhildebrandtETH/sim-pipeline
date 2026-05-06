## --->  PE0_FILE_PATH, RPM, TARGET_DIRECTORY, CORE_TEMPLATE_DIRECTORY... --> THIS FUNCTION ---> READY TO RUN OPENFOAM SIMULATION FOR PARTRICULAR CASE

import shutil
import os
import math
from pathlib import Path
from tools import get_latest_timestep
from tools import update_parameter


interpolation_points = 100




# Usage


def preprocessing(STL_PATH, RPM_COUNT, MAIN_DIRECTORY, TARGET_DIRECTORY, CORES_TO_USE, MODE, INIT_FROM_PREVIOUS, PREVIOUS_SIMULATION_PATH, TURBULENCE_MODEL, STUDY_PARAMETER_NAME = None, STUDY_PARAMETER_FILE = None, STUDY_PARAMETER = None):

 
    #1. duplicate right Core Template to target directory (AMI or RMF approach)

    if MODE == "MRF":

        if TURBULENCE_MODEL == "kOmegaSST":
            core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template MRF - kOmegaSST")    
        elif TURBULENCE_MODEL == "kEpsilon":
            core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template MRF - kEpsilon")

    
    elif MODE == "AMI":

        if TURBULENCE_MODEL == "kOmegaSST":
            core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template AMI - kOmegaSST")
        
        elif TURBULENCE_MODEL == "kEpsilon":
            core_template_directory = os.path.join(MAIN_DIRECTORY, "Core Template AMI - kEpsilon")

    else:
        print("Unknown mode was passed to the pipeline...")
        return None


    shutil.copytree(core_template_directory, TARGET_DIRECTORY, dirs_exist_ok=True)
    
    # copy parameters folder to case folder

    parameters_path_main = os.path.join(MAIN_DIRECTORY, 'Parameters')

    shutil.copytree(parameters_path_main, os.path.join(TARGET_DIRECTORY, 'Parameters'))

    #

    ## Copy init related files to target


    if INIT_FROM_PREVIOUS:

        # create init folder in case
        
        init_path = Path(TARGET_DIRECTORY) / "init"
        init_path.mkdir()


        # copy relevant subfolders of previous case to new init folder to this case
        constant_init_path = Path(PREVIOUS_SIMULATION_PATH) / "constant"
        system_init_path = Path(PREVIOUS_SIMULATION_PATH) / "system"
        parameters_init_path = Path(PREVIOUS_SIMULATION_PATH) / "Parameters"

        # get latest Timestep that is then initialized
        latest_time, latest_name = get_latest_timestep(PREVIOUS_SIMULATION_PATH)
        timestep_init_path = Path(PREVIOUS_SIMULATION_PATH) / latest_name

        shutil.copytree(constant_init_path, init_path / "constant")
        shutil.copytree(system_init_path, init_path / "system")
        shutil.copytree(parameters_init_path, init_path / "Parameters")
        shutil.copytree(timestep_init_path, init_path / latest_name)
    ##


    #2. know about what simulation we are talking about (geometry facts & RPM)
    
    # adapt study parameter in case file in study mode

    if STUDY_PARAMETER_NAME is not None and STUDY_PARAMETER_FILE is not None and STUDY_PARAMETER is not None:

        file_name = STUDY_PARAMETER_FILE + ".cpp"

        file_path = Path(TARGET_DIRECTORY) / "Parameters" / file_name

        update_parameter(file_path, STUDY_PARAMETER_NAME, STUDY_PARAMETER)


    #3. adapt all exisiting parameters based on certain rules

    rotational_parameters_file_path = os.path.join(TARGET_DIRECTORY, 'Parameters', 'rotational_parameters.cpp')

    omega = RPM_COUNT * 2 * math.pi / 60

    update_parameter(rotational_parameters_file_path, 'omega_val', omega)


    decomposeParDict_parameters_file_path = os.path.join(TARGET_DIRECTORY, 'Parameters', 'decomposeParDict.cpp')

    update_parameter(decomposeParDict_parameters_file_path, 'numberOfSubdomains', CORES_TO_USE)


    # Activate prismLayers for kOmegaSST turbulence model

    snappyHexMeshDict_parameters_file_path = os.path.join(TARGET_DIRECTORY, 'Parameters', 'snappyHexMeshDict.cpp')

    if TURBULENCE_MODEL == "kOmegaSST":

        update_parameter(snappyHexMeshDict_parameters_file_path, 'addLayers', "true")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'propellerTipSurfaceLayers', "5")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'propellerTipSurfaceRefinementLevel', "(7 7)")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'firstLayerThickness', "0.00006")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'minThickness', "0.000006")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'expansionRatio', "1.15")

    else:
        update_parameter(snappyHexMeshDict_parameters_file_path, 'addLayers', "false")
        update_parameter(snappyHexMeshDict_parameters_file_path, 'propellerTipSurfaceRefinementLevel', "(5 5)")





    #4. generate STL file from requestes described geometry (other function)


    target_stl_path = os.path.join(TARGET_DIRECTORY, "constant", "triSurface", "propellerTip.stl")

    #generateSTL(PE0_NAME, MAIN_DIRECTORY, target_stl_path, interpolation_points)

    shutil.copy(STL_PATH, target_stl_path)
 



    #5. deal with all the other geometry related stuff like nonConformalCouples...

    #6. provide all prepared folder bundle to the desired location

    

    return None