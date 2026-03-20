import docker
import threading
from convergence_tools import run_convergence_monitor

def openfoamSimulation(simulation_name, simulation_working_directory, convergence_tolerance, convergence_window_size):

    # Docker client is setup here, interface volume mapping is defined, container is created:

    client = docker.from_env()

    # Define the volume mapping
    my_volumes = {
        simulation_working_directory: {'bind': '/simulation', 'mode': 'rw'}
    }

    # Create and start the container
    container = client.containers.run(
        image="microfluidica/openfoam:13",
        name=simulation_name,
        volumes=my_volumes,
        working_dir="/simulation", # Added this so it starts in the right folder
        command="bash", 
        detach=True,    
        tty=True,       
        stdin_open=True 
    )

    # Now these print statements will work because 'container' is defined here
    print(f"Container '{container.name}' created successfully!")
    print(f"Status: {container.status}")

    # Running the different openFOAM simulation commands (if Output is wanted, uncomment for line in result paragraph and comment for _ in result.output):

    blockMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && blockMesh'"

    print("BlockMesh started...")

    result = container.exec_run(blockMesh_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("blockMesh finished...")

    surfaceFeatures_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && surfaceFeatures'"

    print("surfaceFeatures started...")

    result = container.exec_run(surfaceFeatures_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("surfaceFeatures finished...")

    snappyHexMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && snappyHexMesh -overwrite'"

    print("snappyHexMesh started...")

    result = container.exec_run(snappyHexMesh_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("snappyHexMesh finsished...")

    checkMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && checkMesh'"

    print("checkMesh started...")

    result = container.exec_run(checkMesh_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("checkMesh finsished...")

    createNonConformalCouples_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && createNonConformalCouples innerCylinder innerCylinder_slave'"

    print("createNonConformalCouples started...")

    result = container.exec_run(checkMesh_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("createNonConformalCouples finished...")

    decomposePar_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && decomposePar'"

    print("decomposePar started...")

    result = container.exec_run(decomposePar_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("decomposePar finished...")



    # Launch convergenceStop script in parallel (threading)

    monitor_thread = threading.Thread(
        target=run_convergence_monitor,
        kwargs={
            'main_sim_folder': simulation_working_directory, 
            'tolerance': convergence_tolerance, 
            'window_size': convergence_window_size
        }
    )

    # Setting daemon=True ensures the monitor dies if the main script crashes
    monitor_thread.daemon = True 

    # Starting convergence monitoring
    print("Launching Background Convergence Monitor...")
    monitor_thread.start()

    # Starting the actual solving process

    simRun_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && mpirun --allow-run-as-root --use-hwthread-cpus -np 24 foamRun -solver incompressibleFluid -parallel | tee log.pimpleFoam'"

    print("pimpleFoamSolver started...")

    result = container.exec_run(simRun_cmd, stream=True)


    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    # The solver has now exited. 
    # If the monitor thread is NO LONGER alive, it means it found convergence and returned True.

    if not monitor_thread.is_alive():
        print("SUCCESS: Simulation stopped early due to convergence.")
    else:
        print("NOTICE: Simulation finished normally (reached original endTime).")


    reconstructPar_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && reconstructPar'"

    print("reconstructPar started...")

    result = container.exec_run(reconstructPar_cmd, stream=True)

    #for line in result.output:
    #   print(line.decode('utf-8').strip())

    for _ in result.output:
        pass

    print("reconstructPar finsished...")

    # Stop and Remove active simulation container

    print(f"Stopping container '{container.name}'...")
    container.stop()

    print(f"Removing container '{container.name}'...")
    container.remove()

    print("Cleanup complete. System ready for the next simulation.")

openfoamSimulation('XY', r"C:\Users\jonas\Downloads\Playground\DeleteIt\propellerSimulationDemo\10X7E\RPM7000\kEpsilon")