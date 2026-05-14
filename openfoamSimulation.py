import docker
from pathlib import Path
import threading

from tools import run_convergence_monitor
from tools import is_mesh_ok
from tools import get_safe_timestep
from tools import processor_deletion_is_safe
from tools import safe_exec


convergence_check_interval = 1


def openfoamSimulation(
    simulation_name,
    simulation_working_directory,
    convergence_tolerance,
    rpm_count,
    convergence_window_revolutions,
    MODE,
    TURBULENCE_MODEL,
    NUMBER_OF_CORES,
    resume,
    MESH_ONLY,
    ALLOW_BAD_MESH,
    initialize_from_previous=False,
    previous_simulation_path=None,
):
    status = False
    container = None
    monitor_thread = None
    monitor_stop_event = None

    try:
        client = docker.from_env()

        my_volumes = {
            simulation_working_directory: {"bind": "/simulation", "mode": "rw"}
        }

        container = client.containers.run(
            image="microfluidica/openfoam:13",
            name=simulation_name,
            volumes=my_volumes,
            working_dir="/simulation",
            command="bash",
            detach=True,
            tty=True,
            stdin_open=True,
        )

        print(f"Container '{container.name}' created successfully!")
        print(f"Status: {container.status}")

        # ---------------- NOT RESUME ----------------
        if not resume:

            blockMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && blockMesh > log.blockMesh'"
            print("blockMesh started...")
            if not safe_exec(container, blockMesh_cmd, "blockMesh"):
                return False
            print("blockMesh finished...")

            surfaceFeatures_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && surfaceFeatures > log.surfaceFeatures'"
            print("surfaceFeatures started...")
            if not safe_exec(container, surfaceFeatures_cmd, "surfaceFeatures"):
                return False
            print("surfaceFeatures finished...")

            snappyHexMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && snappyHexMesh > log.snappyHexMesh'"
            print("snappyHexMesh started...")
            if not safe_exec(container, snappyHexMesh_cmd, "snappyHexMesh"):
                return False
            print("snappyHexMesh finished...")

            checkMesh_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && checkMesh | tee log.checkMesh'"
            print("checkMesh started...")
            if not safe_exec(container, checkMesh_cmd, "checkMesh", print_output=True):
                return False
            print("checkMesh finished...")

            checkMesh_log_path = Path(simulation_working_directory) / "log.checkMesh"

            if not (is_mesh_ok(checkMesh_log_path) or ALLOW_BAD_MESH):
                print("Mesh is not OK... stopping this case")
                return False

            if MODE == "AMI":
                createNonConformalCouples_cmd = (
                    "bash -c 'source /opt/openfoam13/etc/bashrc && "
                    "createNonConformalCouples innerCylinder innerCylinder_slave "
                    "> log.createNonConformalCouples'"
                )
                print("createNonConformalCouples started...")
                if not safe_exec(container, createNonConformalCouples_cmd, "createNonConformalCouples"):
                    return False
                print("createNonConformalCouples finished...")

            if initialize_from_previous:
                print(f"Initializing from previous case: {previous_simulation_path}")

                mapFields_cmd = (
                    "bash -c 'source /opt/openfoam13/etc/bashrc && "
                    "mapFields /simulation/init/ -consistent -sourceTime latestTime "
                    "> log.mapFields'"
                )
                print("mapFields started...")
                if not safe_exec(container, mapFields_cmd, "mapFields"):
                    return False
                print("mapFields finished...")

            if not MESH_ONLY:
                decomposePar_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && decomposePar > log.decomposePar'"
                print("decomposePar started...")
                if not safe_exec(container, decomposePar_cmd, "decomposePar"):
                    return False
                print("decomposePar finished...")

        # ---------------- RESUME ----------------
        else:
            print("Preparing to resume...")

            safe_time = get_safe_timestep(Path(simulation_working_directory))

            if safe_time is None:
                print("No safe timestep found for resume.")
                return False

            reconstructPar_resume_cmd = (
                f"bash -c 'source /opt/openfoam13/etc/bashrc && "
                f"reconstructPar -time {safe_time} > log_resume.reconstructPar'"
            )
            print("Reconstructing safe timestep...")
            if not safe_exec(container, reconstructPar_resume_cmd, "resume reconstructPar"):
                return False
            print("Reconstructing safe timestep finished...")

            print("Checking if reconstruction was successful...")

            path_to_control_dict_parameter = (
                Path(simulation_working_directory) / "Parameters" / "controlDict.cpp"
            )

            is_processor_deletion_safe = processor_deletion_is_safe(
                PATH_TO_CONTROL_DICT_PARAMETERS=path_to_control_dict_parameter,
                SIMULATION_DIRECTORY=simulation_working_directory,
                RESUME=True,
                TURBULENCE_MODEL=TURBULENCE_MODEL,
            )

            if not is_processor_deletion_safe:
                print(
                    f"Reconstructed data in '{simulation_working_directory}' failed integrity checks. "
                    "Resume operation aborted. Case marked as failed."
                )
                return False

            print("Reconstruction looks healthy, continue to clean up...")
            print("Deleting processor folders...")

            delete_processor_folders_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && rm -rf processor*'"
            if not safe_exec(container, delete_processor_folders_cmd, "delete processor folders after resume reconstruction"):
                return False
            print("Deleted processor folder...")

            decomposePar_resume_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && decomposePar > log_resume.decomposePar'"
            print("decomposePar started...")
            if not safe_exec(container, decomposePar_resume_cmd, "resume decomposePar"):
                return False
            print("decomposePar finished...")

        # ---------------- SOLVER ----------------
        if not MESH_ONLY:

            if resume:
                timestep_str = str(safe_time)
            else:
                timestep_str = "0"

            monitor_stop_event = threading.Event()

            monitor_thread = threading.Thread(
                target=run_convergence_monitor,
                kwargs={
                    "main_sim_folder": simulation_working_directory,
                    "rpm": rpm_count,
                    "avg_history_count": convergence_window_revolutions,
                    "tolerance": convergence_tolerance,
                    "check_interval": convergence_check_interval,
                    "timestep": timestep_str,
                    "stop_event": monitor_stop_event,
                },
            )

            monitor_thread.daemon = True

            print(f"Launching Background Convergence Monitor... Timestep is: {timestep_str}")
            monitor_thread.start()

            simRun_cmd = (
                f"bash -c 'source /opt/openfoam13/etc/bashrc && "
                f"mpirun --allow-run-as-root --use-hwthread-cpus -np {NUMBER_OF_CORES} "
                f"foamRun -solver incompressibleFluid -parallel | tee log.pimpleFoam'"
            )

            print("pimpleFoamSolver started...")
            if not safe_exec(container, simRun_cmd, "pimpleFoamSolver"):
                return False
            print("pimpleFoamSolver finished...")

            # Solver has ended. Make sure the monitor from this case cannot continue
            # while the next case starts preprocessing.
            if monitor_stop_event is not None:
                monitor_stop_event.set()

            if monitor_thread is not None and monitor_thread.is_alive():
                monitor_thread.join(timeout=5)

            if monitor_thread is not None and not monitor_thread.is_alive():
                print("Convergence monitor ended.")
            else:
                print("WARNING: Convergence monitor did not stop within timeout.")

            reconstructPar_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && reconstructPar > log.reconstructPar'"
            print("reconstructPar started...")
            if not safe_exec(container, reconstructPar_cmd, "reconstructPar"):
                return False
            print("reconstructPar finished...")

        else:
            print("Mesh-only mode: skipping solver.")

        # ---------------- FOAM FILE ----------------
        foam_file_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && touch sim.foam'"
        print("Creating FOAM file...")
        if not safe_exec(container, foam_file_cmd, "create FOAM file"):
            return False
        print("FOAM File created...")

        # ---------------- PROCESSOR CLEANUP CHECK ----------------
        path_to_control_dict_parameter = (
            Path(simulation_working_directory) / "Parameters" / "controlDict.cpp"
        )

        is_processor_deletion_safe = processor_deletion_is_safe(
            PATH_TO_CONTROL_DICT_PARAMETERS=path_to_control_dict_parameter,
            SIMULATION_DIRECTORY=simulation_working_directory,
            RESUME=False,
            TURBULENCE_MODEL=TURBULENCE_MODEL,
        )

        if is_processor_deletion_safe:
            print("Reconstruction looks healthy, continue to clean up...")
            print("Deleting processor folders...")

            delete_processor_folders_cmd = "bash -c 'source /opt/openfoam13/etc/bashrc && rm -rf processor*'"
            if not safe_exec(container, delete_processor_folders_cmd, "final delete processor folders"):
                return False

            print("Deleted processor folder...")
            print("Cleanup complete. System ready for the next simulation.")

        else:
            print(
                f"Reconstructed data in '{simulation_working_directory}' failed integrity checks. "
                "Processor source files were preserved for safety and manual inspection."
            )

        status = True
        return status

    except Exception as e:
        print(f"Simulation case failed unexpectedly: {e}")
        return False

    finally:
        # Always stop the monitor belonging to this case before leaving this function.
        try:
            if monitor_stop_event is not None:
                monitor_stop_event.set()

            if monitor_thread is not None and monitor_thread.is_alive():
                monitor_thread.join(timeout=5)

        except Exception as e:
            print(f"Monitor cleanup skipped/failed: {e}")

        # Always attempt container cleanup, but never let cleanup crash the pipeline.
        if container is not None:
            try:
                container.reload()

                if container.status == "running":
                    print(f"Stopping container '{container.name}'...")
                    container.stop()

                print(f"Removing container '{container.name}'...")
                container.remove(force=True)

            except Exception as e:
                print(f"Container cleanup skipped/failed: {e}")

        print(f"openFoamSimulation returns status: {status}")
