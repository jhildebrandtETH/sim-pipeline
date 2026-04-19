import os
import time
import numpy as np
import pandas as pd
import re


import numpy as np
import pandas as pd

def is_mesh_ok(log_path):
    """
    Returns True if 'Mesh OK' is found in log.checkMesh, else False.
    """

    if not log_path.exists():
        print("Coudn't confirm mesh is OK because of path error...")
        return False

    log_text = log_path.read_text(errors="ignore")

    return "Mesh OK" in log_text


def check_residuals(
    residuals_file,
    revolution_time,
    use_log=True,
    min_points=10,
):
    """
    Returns True if all residuals satisfy slope criteria over the last revolution.

    The fitted regression slope is converted from "per second" to
    "per revolution" by multiplying with revolution_time.

    If use_log=True, the checked quantity is the change in log10(residual)
    over one revolution.
    """

    # SETTINGS
    # Bounds are now interpreted as slope/change OVER ONE REVOLUTION
    slope_bounds = {
        "p":  (-5e-2, 1e-2),
        "Ux": (-5e-2, 5e-3),
        "Uy": (-5e-2, 5e-3),
        "Uz": (-5e-2, 5e-3),
        "k":  (-5e-2, 5e-3),
    }

    # Read header explicitly from second line
    with open(residuals_file, "r") as f:
        lines = f.readlines()

    if len(lines) < 3:
        raise ValueError("Residual file is too short.")

    header = lines[1].lstrip("#").strip().split()

    df = pd.read_csv(
        residuals_file,
        sep=r"\s+",
        names=header,
        skiprows=2,
        na_values=["N/A"],
        engine="python",
    )

    if "Time" not in df.columns:
        raise ValueError("Residual file must contain a 'Time' column.")

    df = df.dropna(subset=["Time"]).sort_values("Time")

    if df.empty:
        raise ValueError("Residual file contains no valid data.")

    latest_time = df["Time"].iloc[-1]

    if latest_time <= revolution_time:
        print("Failed: not enough data for one full revolution.")
        return False

    # Last revolution window
    t_start = latest_time - revolution_time
    window_df = df[df["Time"] >= t_start].copy()

    if window_df.empty:
        print("Failed: no data in last revolution window.")
        return False

    failed_fields = []

    for field, bounds in slope_bounds.items():

        if field not in window_df.columns:
            failed_fields.append(field)
            continue

        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError(
                f"Bounds for '{field}' must be (lower_bound, upper_bound)."
            )

        lower_bound, upper_bound = bounds

        data = window_df[["Time", field]].dropna()

        if len(data) < min_points:
            failed_fields.append(field)
            continue

        t = data["Time"].to_numpy(dtype=float)
        y = data[field].to_numpy(dtype=float)

        if use_log:
            mask = y > 0.0
            t = t[mask]
            y = y[mask]

            if len(y) < min_points:
                failed_fields.append(field)
                continue

            y = np.log10(y)

        slope_per_second, _ = np.polyfit(t, y, 1)
        slope_per_revolution = slope_per_second * revolution_time

        if not (lower_bound <= slope_per_revolution <= upper_bound):
            failed_fields.append(field)

    # DEBUGGING ONLY
    print("\n--- Residual slopes per revolution (debug) ---")

    for field in slope_bounds.keys():

        if field not in window_df.columns:
            print(f"{field}: not found")
            continue

        data = window_df[["Time", field]].dropna()

        if len(data) < min_points:
            print(f"{field}: not enough data")
            continue

        t = data["Time"].to_numpy(dtype=float)
        y = data[field].to_numpy(dtype=float)

        if use_log:
            mask = y > 0.0
            t = t[mask]
            y = y[mask]

            if len(y) < min_points:
                print(f"{field}: not enough valid data after log filter")
                continue

            y = np.log10(y)

        slope_per_second, _ = np.polyfit(t, y, 1)
        slope_per_revolution = slope_per_second * revolution_time

        print(f"{field}: slope per revolution = {slope_per_revolution:.3e}")

    # END OF DEBUGGING

    if len(failed_fields) == 0:
        print("Passed: all residual slope checks satisfied.")
        return True
    else:
        print(f"Failed: residual slope check failed for {failed_fields}.")
        return False


def run_convergence_monitor(
    main_sim_folder,
    rpm,
    avg_history_count,
    tolerance,
    check_interval
):
    """
    Monitor an OpenFOAM simulation and stop it once converged.

    Convergence logic:
    - Compute the average thrust over the last ONE full revolution
    - Repeat this at every monitor check (rolling one-revolution window)
    - Store the last avg_history_count rolling revolution-averaged thrust values
    - Compute the standard deviation of those stored averaged values
    - Stop when that std dev is below tolerance

    Additionally prints y+ statistics for the 'propellerTip' patch
    over the last full revolution.

    Args:
        main_sim_folder (str): Path to the OpenFOAM case directory.
        rpm (float): Rotational speed in revolutions per minute.
        avg_history_count (int): Number of rolling one-revolution averaged
            thrust values used for the convergence std dev.
        tolerance (float): Std-dev threshold for convergence.
        check_interval (int | float): Seconds to wait between checks.
    """

    force_file = os.path.join(
        main_sim_folder, "postProcessing", "forcesBlades", "0", "forces.dat"
    )
    yplus_file = os.path.join(
        main_sim_folder, "postProcessing", "yPlus", "0", "yPlus.dat"
    )

    residuals_file = os.path.join(
        main_sim_folder, "postProcessing", "residuals", "0", "residuals.dat"
    )

    control_dict = os.path.join(main_sim_folder, "system", "controlDict")

    rev_time = 60.0 / rpm

    # History of rolling one-revolution averaged thrust values
    avg_thrust_history = []

    #print(f"Monitoring Started for: {main_sim_folder}")
    print(f"RPM: {rpm}")
    print(f"One revolution time: {rev_time:.6f} s")
    #print(f"History length for convergence check: {avg_history_count}")

    while True:
        try:
            # ----------------------------
            # Wait for force file
            # ----------------------------
            if not os.path.exists(force_file):
                print("Waiting for force file to be created...")
                time.sleep(check_interval)
                continue

            # ----------------------------
            # Read thrust data
            # ----------------------------
            with open(force_file, "r", encoding="utf-8", errors="ignore") as f:
                force_lines = [
                    l.strip()
                    for l in f
                    if l.strip() and not l.strip().startswith("#")
                ]

            if not force_lines:
                print("Force file exists but contains no usable data yet.")
                time.sleep(check_interval)
                continue

            latest_force_line = force_lines[-1]
            latest_force_parts = (
                latest_force_line.replace("(", " ").replace(")", " ").split()
            )
            latest_time = float(latest_force_parts[0])

            # Need at least one full revolution before first rolling average
            if latest_time < rev_time:
                print(
                    f"Waiting for enough data: {latest_time:.4f}/{rev_time:.4f} s "
                    f"({latest_time / rev_time:.2f}/1.00 rev)"
                )
                time.sleep(check_interval)
                continue

            # ----------------------------
            # Compute rolling one-revolution average thrust
            # ----------------------------
            thrust_values_last_rev = []
            latest_sim_time = latest_time

            rev_window_start = latest_time - rev_time
            rev_window_end = latest_time

            for line in force_lines:
                parts = line.replace("(", " ").replace(")", " ").split()
                t = float(parts[0])

                if rev_window_start <= t <= rev_window_end:
                    thrust_y = float(parts[2])   # Pressure Force Y
                    thrust_values_last_rev.append(thrust_y)

            if not thrust_values_last_rev:
                print("No thrust values found in the last full-revolution window.")
                time.sleep(check_interval)
                continue

            current_avg_thrust = float(np.mean(thrust_values_last_rev))

            avg_thrust_history.append(current_avg_thrust)

            # Keep only the most recent avg_history_count entries
            if len(avg_thrust_history) > avg_history_count:
                avg_thrust_history = avg_thrust_history[-avg_history_count:]

            # ----------------------------
            # Read y+ data over last full revolution
            # ----------------------------
            avg_yplus = float("nan")
            max_yplus = float("nan")
            min_yplus = float("nan")

            if os.path.exists(yplus_file):
                with open(yplus_file, "r", encoding="utf-8", errors="ignore") as f:
                    yplus_lines = [
                        l.strip()
                        for l in f
                        if l.strip() and not l.strip().startswith("#")
                    ]

                yplus_min_vals = []
                yplus_max_vals = []
                yplus_avg_vals = []

                for line in yplus_lines:
                    parts = line.split()

                    # Expected format: time patch min max average
                    if len(parts) >= 5 and parts[1] == "propellerTip":
                        t = float(parts[0])

                        if rev_window_start <= t <= rev_window_end:
                            y_min = float(parts[2])
                            y_max = float(parts[3])
                            y_avg = float(parts[4])

                            yplus_min_vals.append(y_min)
                            yplus_max_vals.append(y_max)
                            yplus_avg_vals.append(y_avg)

                if yplus_avg_vals:
                    avg_yplus = float(np.mean(yplus_avg_vals))
                    max_yplus = float(np.max(yplus_max_vals))
                    min_yplus = float(np.min(yplus_min_vals))

            # ----------------------------
            # Print monitor output before enough history exists
            # ----------------------------
            if len(avg_thrust_history) < avg_history_count:
                hist_str = " | ".join(f"{v:.4f}" for v in avg_thrust_history)
                print(
                    f"Time: {latest_sim_time:.4f} | "
                    f"Current 1-rev Avg Thrust: {current_avg_thrust:.4f} | "
                    f"Waiting for enough averaged values: {len(avg_thrust_history)} / {avg_history_count}"
                    f"Avg y+: {avg_yplus:.2f} | "
                    f"Max y+: {max_yplus:.2f} | "
                    f"Min y+: {min_yplus:.2f}"
                )
                time.sleep(check_interval)
                continue

            # ----------------------------
            # Convergence statistics on rolling averages
            # ----------------------------
            std_dev = float(np.std(avg_thrust_history))
            avg_val = float(np.mean(avg_thrust_history))
            hist_str = " | ".join(f"{v:.4f}" for v in avg_thrust_history)

            print(
                f"Time: {latest_sim_time:.4f} | "
                f"Current 1-rev Avg Thrust: {current_avg_thrust:.4f} | "
                f"Avg Thrust: {avg_val:.4f} | "
                f"StdDev(rolling 1-rev avgs): {std_dev:.6f} | "
                f"Avg y+: {avg_yplus:.2f} | "
                f"Max y+: {max_yplus:.2f} | "
                f"Min y+: {min_yplus:.2f}"
            )

            # ----------------------------
            # Stop logic
            # ----------------------------
            if std_dev < tolerance and check_residuals(residuals_file, rev_time):
                print(f"\n>>> SUFFICIENT CONVERGENCE REACHED AT {latest_sim_time}s <<<")

                if not os.path.exists(control_dict):
                    print(f"ERROR: controlDict not found at: {control_dict}")
                    return False

                with open(control_dict, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                with open(control_dict, "w", encoding="utf-8") as f:
                    for line in lines:
                        if re.match(r"^\s*endTime\s+", line):
                            f.write(f"endTime         {latest_sim_time + 1e-8};\n")
                        else:
                            f.write(line)

                print("Simulation stop command sent to controlDict.")
                return True

        except Exception as e:
            print(f"Error during monitoring: {e}")

        time.sleep(check_interval)

#check_residuals(r"C:\Users\jonas\Downloads\SimulationSpace\11x8E@7000\postProcessing\residuals\0\residuals.dat", 0.0086)