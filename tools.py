import os
import time
import numpy as np
import pandas as pd
import re
from pathlib import Path



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
        "p":  (-10e-2, 10e-2), #(-5e-2, 1e-2)
        "Ux": (-10e-2, 10e-3), #(-5e-2, 5e-3)
        "Uy": (-10e-2, 10e-3), #(-5e-2, 5e-3)
        "Uz": (-10e-2, 10e-3), #(-5e-2, 5e-3)
        "k":  (-10e-2, 10e-3), #(-5e-2, 5e-3)
    }
    ###

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

    Improved logic:
    - Reconstruct all possible rolling 1-revolution averaged thrust values
      directly from forces.dat at every check
    - Use the last avg_history_count of those values for convergence
    - Therefore convergence no longer depends on how often this Python
      function polls, but on how many actual force samples exist

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

    print(f"RPM: {rpm}")
    print(f"One revolution time: {rev_time:.6f} s")

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
            # Read full force data
            # ----------------------------
            times = []
            thrusts = []

            with open(force_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.replace("(", " ").replace(")", " ").split()

                    # We only need time and pressure force Y
                    if len(parts) < 3:
                        continue

                    try:
                        t = float(parts[0])
                        thrust_y = float(parts[2])   # Pressure Force Y
                    except ValueError:
                        continue

                    times.append(t)
                    thrusts.append(thrust_y)

            if not times:
                print("Force file exists but contains no usable data yet.")
                time.sleep(check_interval)
                continue

            times = np.asarray(times, dtype=float)
            thrusts = np.asarray(thrusts, dtype=float)

            sort_idx = np.argsort(times)
            times = times[sort_idx]
            thrusts = thrusts[sort_idx]

            latest_time = float(times[-1])

            # Need at least one full revolution before first rolling average
            if latest_time < rev_time:
                print(
                    f"Waiting for enough data: {latest_time:.4f}/{rev_time:.4f} s "
                    f"({latest_time / rev_time:.2f}/1.00 rev)"
                )
                time.sleep(check_interval)
                continue

            # ----------------------------
            # Build ALL rolling 1-rev averages from current file
            # ----------------------------
            csum = np.concatenate(([0.0], np.cumsum(thrusts)))
            avg_times = []
            avg_vals = []

            for i in range(len(times)):
                t_end = times[i]
                t_start = t_end - rev_time

                if t_start < 0.0:
                    continue

                # first index still inside window
                j = np.searchsorted(times, t_start, side="left")
                count = i - j + 1

                if count <= 0:
                    continue

                window_sum = csum[i + 1] - csum[j]
                avg_val = window_sum / count

                avg_times.append(t_end)
                avg_vals.append(avg_val)

            if not avg_vals:
                print("No valid rolling 1-rev averages available yet.")
                time.sleep(check_interval)
                continue

            avg_times = np.asarray(avg_times, dtype=float)
            avg_vals = np.asarray(avg_vals, dtype=float)

            latest_sim_time = float(avg_times[-1])
            current_avg_thrust = float(avg_vals[-1])

            # ----------------------------
            # Define last full-revolution window for y+ and residual reporting
            # ----------------------------
            rev_window_start = latest_sim_time - rev_time
            rev_window_end = latest_sim_time

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
                        try:
                            t = float(parts[0])
                            y_min = float(parts[2])
                            y_max = float(parts[3])
                            y_avg = float(parts[4])
                        except ValueError:
                            continue

                        if rev_window_start <= t <= rev_window_end:
                            yplus_min_vals.append(y_min)
                            yplus_max_vals.append(y_max)
                            yplus_avg_vals.append(y_avg)

                if yplus_avg_vals:
                    avg_yplus = float(np.mean(yplus_avg_vals))
                    max_yplus = float(np.max(yplus_max_vals))
                    min_yplus = float(np.min(yplus_min_vals))

            # ----------------------------
            # Not enough rolling averages yet
            # ----------------------------
            if len(avg_vals) < avg_history_count:
                print(
                    f"Time: {latest_sim_time:.4f} | "
                    f"Current 1-rev Avg Thrust: {current_avg_thrust:.4f} | "
                    f"Waiting for enough averaged values: "
                    f"{len(avg_vals)} / {avg_history_count} | "
                    f"Avg y+: {avg_yplus:.2f} | "
                    f"Max y+: {max_yplus:.2f} | "
                    f"Min y+: {min_yplus:.2f}"
                )
                time.sleep(check_interval)
                continue

            # ----------------------------
            # Convergence statistics on most recent rolling averages
            # ----------------------------
            avg_thrust_history = avg_vals[-avg_history_count:]
            std_dev = float(np.std(avg_thrust_history))
            avg_val = float(np.mean(avg_thrust_history))

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


def get_latest_timestep(case_path):
    case_path = Path(case_path)

    time_dirs = []
    for item in case_path.iterdir():
        if item.is_dir():
            try:
                time_value = float(item.name)
                time_dirs.append((time_value, item.name))
            except ValueError:
                pass

    if not time_dirs:
        raise FileNotFoundError(f"No time directories found in {case_path}")

    latest_time, latest_name = max(time_dirs, key=lambda x: x[0])
    return latest_time, latest_name

def update_parameter(file_path, target_var, new_value):
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
