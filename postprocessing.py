from createSimulationReport import create_simulation_report



def postprocessing(SIMULATION_WORKING_DIRECTORY, RPM_COUNT, MODE):
    create_simulation_report(case_path=SIMULATION_WORKING_DIRECTORY, rpm=RPM_COUNT, mode=MODE)

    return None

