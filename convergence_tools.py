import os
import time
import numpy as np
import re

def run_convergence_monitor(main_sim_folder, window_size=500, tolerance=0.5, check_interval=5):
    """
    A single function to monitor an OpenFOAM simulation and stop it once converged.
    
    Args:
        main_sim_folder (str): Path to the OpenFOAM case directory.
        window_size (int): Number of trailing data points to analyze.
        tolerance (float): Standard deviation threshold for convergence.
        check_interval (int): Seconds to wait between file reads.
    """
    
    # 1. Define internal paths based on the input variable
    force_file = os.path.join(main_sim_folder, "postProcessing", "forcesBlades", "0", "forces.dat")
    control_dict = os.path.join(main_sim_folder, "system", "controlDict")

    print(f"--- Monitoring Started for: {main_sim_folder} ---")

    # 2. The Monitoring Loop
    while True:
        if not os.path.exists(force_file):
            print(f"Waiting for force file to be created...")
        else:
            try:
                # Read data
                with open(force_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Filter comments and empty lines
                    data_lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
                
                if len(data_lines) >= window_size:
                    recent_thrust = []
                    latest_sim_time = 0.0
                    
                    # Parse the last N lines
                    for line in data_lines[-window_size:]:
                        parts = line.replace('(', ' ').replace(')', ' ').split()
                        latest_sim_time = float(parts[0])
                        thrust_y = float(parts[2]) # Pressure Force Y
                        recent_thrust.append(thrust_y)
                    
                    # Check statistics
                    std_dev = np.std(recent_thrust)
                    avg_val = np.mean(recent_thrust)
                    print(f"Time: {latest_sim_time:.4f} | Avg Thrust: {avg_val:.4f} | StdDev: {std_dev:.6f}")

                    # 3. Stop logic
                    if std_dev < tolerance:
                        print(f"\n>>> CONVERGENCE REACHED AT {latest_sim_time}s <<<")
                        
                        # Update controlDict
                        with open(control_dict, 'r') as f:
                            lines = f.readlines()
                        with open(control_dict, 'w') as f:
                            for line in lines:
                                if re.match(r"^\s*endTime\s+", line):
                                    f.write(f"endTime         {latest_sim_time + 1e-8};\n")
                                else:
                                    f.write(line)
                        
                        print("Simulation stop command sent to controlDict.")
                        return True # Exit the function entirely

                else:
                    print(f"Waiting for data: {len(data_lines)}/{window_size} lines...")

            except Exception as e:
                print(f"Error during monitoring: {e}")

        # Wait before the next check
        time.sleep(check_interval)

# --- EXAMPLE OF HOW TO CALL IT ---
# if __name__ == "__main__":
#    my_path = r"C:\Users\jonas\Downloads\Playground\propellerSimulationDemo\10X7E\RPM7000\kEpsilon"
#    run_convergence_monitor(my_path, tolerance=0.1)