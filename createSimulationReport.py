from pathlib import Path
from datetime import datetime
import numpy as np
import re
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def create_simulation_report(case_path, rpm, mode, output_pdf=None):

    def create_yplus_distribution_plot(case_path, report_dir, patch_name="propellerTip"):
        def get_latest_time_dir(case_path):
            time_dirs = []

            for item in case_path.iterdir():
                if item.is_dir():
                    try:
                        time_dirs.append((float(item.name), item))
                    except ValueError:
                        pass

            if not time_dirs:
                return None

            return max(time_dirs, key=lambda x: x[0])[1]

        latest_time_dir = get_latest_time_dir(case_path)

        if latest_time_dir is None:
            return None

        yplus_file = latest_time_dir / "yPlus"

        if not yplus_file.exists():
            return None

        text = yplus_file.read_text(encoding="utf-8", errors="ignore")

        patch_pattern = rf"{re.escape(patch_name)}\s*\{{(.*?)\}}"
        patch_match = re.search(patch_pattern, text, re.DOTALL)

        if not patch_match:
            return None

        patch_block = patch_match.group(1)

        list_pattern = r"nonuniform\s+List<scalar>\s*(\d+)\s*\((.*?)\)"
        list_match = re.search(list_pattern, patch_block, re.DOTALL)

        if not list_match:
            return None

        values_block = list_match.group(2)

        yplus_values = np.array(
            [
                float(v)
                for v in re.findall(
                    r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?",
                    values_block,
                )
            ],
            dtype=float,
        )

        if len(yplus_values) == 0:
            return None

        counts = [
            np.sum(yplus_values < 5),
            np.sum((yplus_values >= 5) & (yplus_values <= 30)),
            np.sum(yplus_values > 30),
        ]

        total = len(yplus_values)
        percentages = [100.0 * c / total for c in counts]

        labels = ["y+ < 5", "5 ≤ y+ ≤ 30", "y+ > 30"]

        yplus_plot = report_dir / "yplus_distribution.png"

        plt.figure(figsize=(5.0, 3.4))
        bars = plt.bar(labels, percentages)

        plt.ylabel("Surface face share [%]")
        plt.title(f"y+ Distribution: {patch_name}")
        plt.grid(axis="y")

        for bar, percentage in zip(bars, percentages):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{percentage:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        plt.tight_layout()
        plt.savefig(yplus_plot, dpi=200)
        plt.close()

        return yplus_plot

    def read_mesh_element_types(case_path):
        log_checkmesh = case_path / "log.checkMesh"

        element_types = {
            "hexahedra": 0,
            "prisms": 0,
            "wedges": 0,
            "pyramids": 0,
            "tet wedges": 0,
            "tetrahedra": 0,
            "polyhedra": 0,
        }

        if not log_checkmesh.exists():
            return element_types

        text = log_checkmesh.read_text(encoding="utf-8", errors="ignore")

        patterns = {
            "hexahedra": r"hexahedra:\s*([0-9]+)",
            "prisms": r"prisms:\s*([0-9]+)",
            "wedges": r"wedges:\s*([0-9]+)",
            "pyramids": r"pyramids:\s*([0-9]+)",
            "tet wedges": r"tet wedges:\s*([0-9]+)",
            "tetrahedra": r"tetrahedra:\s*([0-9]+)",
            "polyhedra": r"polyhedra:\s*([0-9]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                element_types[key] = int(match.group(1))

        return element_types
    
    def create_mesh_element_plot(element_types, report_dir):
        nonzero = {
            key: value
            for key, value in element_types.items()
            if value > 0
        }

        if not nonzero:
            return None

        total = sum(nonzero.values())

        labels = list(nonzero.keys())
        values = [100.0 * value / total for value in nonzero.values()]

        mesh_plot = report_dir / "mesh_element_types.png"

        plt.figure(figsize=(5.0, 3.4))
        bars = plt.bar(labels, values)

        plt.ylabel("Cell share [%]")
        plt.title("Mesh Element Types")
        plt.xticks(rotation=30, ha="right")
        plt.grid(axis="y")

        # --- Add percentage labels on bars ---
        for bar, val in zip(bars, values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        plt.tight_layout()
        plt.savefig(mesh_plot, dpi=200)
        plt.close()

        return mesh_plot

    def read_mesh_information(case_path):
        log_checkmesh = case_path / "log.checkMesh"

        mesh_info = {
            "mesh_ok": False,
            "cells": None,
            "faces": None,
            "points": None,
            "boundary_patches": None,
            "max_aspect_ratio": None,
            "max_skewness": None,
            "max_non_orthogonality": None,
        }

        if not log_checkmesh.exists():
            mesh_info["status"] = "log.checkMesh not found"
            return mesh_info

        text = log_checkmesh.read_text(encoding="utf-8", errors="ignore")

        mesh_info["mesh_ok"] = "Mesh OK" in text
        mesh_info["status"] = "Mesh OK" if mesh_info["mesh_ok"] else "Mesh check failed / not confirmed"

        patterns = {
            "points": r"points:\s*([0-9]+)",
            "faces": r"faces:\s*([0-9]+)",
            "cells": r"cells:\s*([0-9]+)",
            "boundary_patches": r"boundary patches:\s*([0-9]+)",
            "max_aspect_ratio": r"Max aspect ratio\s*=\s*([0-9.eE+-]+)",
            "max_skewness": r"Max skewness\s*=\s*([0-9.eE+-]+)",
            "max_non_orthogonality": r"Mesh non-orthogonality Max:\s*([0-9.eE+-]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(1)
                try:
                    mesh_info[key] = float(value) if "." in value or "e" in value.lower() else int(value)
                except ValueError:
                    mesh_info[key] = value

        return mesh_info

    def format_seconds(seconds):
        if seconds is None:
            return "Not found"

        seconds = int(round(seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        if h > 0:
            return f"{h} h {m} min {s} s"
        if m > 0:
            return f"{m} min {s} s"
        return f"{s} s"

    def create_force_plots(times, thrusts, report_dir, rev_time):
        force_plot = report_dir / "force_plot.png"
        conv_plot = report_dir / "force_convergence.png"

        latest_time = float(times[-1])
        last_rev_start = latest_time - rev_time

        # Ignore extreme startup spikes only for y-axis scaling
        plot_mask = times > 0.001
        plot_thrusts = thrusts[plot_mask]

        if len(plot_thrusts) > 0:
            y_min = np.percentile(plot_thrusts, 1)
            y_max = np.percentile(plot_thrusts, 99)
            y_margin = 0.15 * (y_max - y_min)
        else:
            y_min, y_max, y_margin = np.min(thrusts), np.max(thrusts), 1.0

        # -----------------------------
        # Force plot
        # -----------------------------
        plt.figure(figsize=(12, 5))
        plt.plot(times, thrusts, label="Pressure force Fy")

        plt.axvspan(
            last_rev_start,
            latest_time,
            alpha=0.2,
            label="last revolution window",
        )

        plt.ylim(y_min - y_margin, y_max + y_margin)

        plt.xlabel("Time [s]")
        plt.ylabel("Force Fy [N]")
        plt.title("Pressure Force Fy")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(force_plot, dpi=200)
        plt.close()

        # -----------------------------
        # Force convergence metric
        # -----------------------------
        window = 200
        eps_rel = 1e-3
        metric = np.full(len(thrusts), np.nan)

        for i in range(window - 1, len(thrusts)):
            w = thrusts[i - window + 1 : i + 1]
            metric[i] = (np.max(w) - np.min(w)) / max(abs(np.mean(w)), 1e-12)

        good = metric < eps_rel
        good[np.isnan(metric)] = False

        first_conv = None

        if np.any(good):
            suffix_all_good = np.flip(
                np.cumprod(np.flip(good.astype(int))).astype(bool)
            )
            idx = np.where(suffix_all_good)[0]

            if len(idx) > 0:
                first_conv = int(idx[0])

        plt.figure(figsize=(12, 5))
        plt.plot(times, metric, label="(max - min) / mean")

        plt.axvspan(
            last_rev_start,
            latest_time,
            alpha=0.2,
            label="last revolution window",
        )

        plt.axhline(eps_rel, linestyle="--", label=f"threshold = {eps_rel:g}")

        if first_conv is not None:
            plt.axvline(
                times[first_conv],
                linestyle="--",
                label=f"convergence start: {times[first_conv]:.4f} s",
            )

        plt.yscale("log")
        plt.xlabel("Time [s]")
        plt.ylabel("Convergence metric")
        plt.title("Force Convergence Criterion")
        plt.grid(True, which="both")
        plt.legend()
        plt.tight_layout()
        plt.savefig(conv_plot, dpi=200)
        plt.close()

        return force_plot, conv_plot, first_conv

    def create_residual_plot(residual_file, report_dir, rev_time, latest_time):
        residual_plot = report_dir / "residuals.png"

        if not residual_file.exists():
            return None

        last_rev_start = latest_time - rev_time

        with open(residual_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        if len(lines) < 3:
            return None

        header = lines[1].lstrip("#").split()

        df = pd.read_csv(
            residual_file,
            sep=r"\s+",
            names=header,
            skiprows=2,
            engine="python",
        )

        if "Time" not in df.columns:
            return None

        plt.figure(figsize=(12, 5))

        for col in df.columns:
            if col != "Time":
                plt.plot(df["Time"], df[col], label=col)

        plt.axvspan(
            last_rev_start,
            latest_time,
            alpha=0.2,
            label="last revolution window",
        )

        plt.yscale("log")
        plt.xlabel("Time [s]")
        plt.ylabel("Residual")
        plt.title("Residual Convergence")
        plt.grid(True, which="both")
        plt.legend()
        plt.tight_layout()
        plt.savefig(residual_plot, dpi=200)
        plt.close()

        return residual_plot

    case_path = Path(case_path)
    report_dir = case_path / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    force_file = case_path / "postProcessing" / "forcesBlades" / "merged_forces.dat"
    residual_file = case_path / "postProcessing" / "residuals" / "merged_residuals.dat"
    log_file = case_path / "log.pimpleFoam"

    mesh_info = read_mesh_information(case_path)
    mesh_element_types = read_mesh_element_types(case_path)
    mesh_element_plot = create_mesh_element_plot(mesh_element_types, report_dir)

    yplus_plot = create_yplus_distribution_plot(case_path, report_dir, patch_name="propellerTip",)

    

    if output_pdf is None:
        output_pdf = report_dir / "simulation_report.pdf"
    else:
        output_pdf = Path(output_pdf)

    times, thrusts = [], []

    with open(force_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            parts = line.replace("(", " ").replace(")", " ").split()

            try:
                times.append(float(parts[0]))
                thrusts.append(float(parts[2]))
            except (ValueError, IndexError):
                continue

    if not times:
        raise ValueError("No valid force data found.")

    times = np.asarray(times, dtype=float)
    thrusts = np.asarray(thrusts, dtype=float)

    idx = np.argsort(times)
    times = times[idx]
    thrusts = thrusts[idx]

    latest_time = float(times[-1])
    rev_time = 60.0 / float(rpm)
    eff_revs = latest_time / rev_time

    if latest_time < rev_time:
        raise ValueError("Simulation shorter than one revolution.")

    idx_start = np.searchsorted(times, latest_time - rev_time, side="left")
    thrust_avg = float(np.mean(thrusts[idx_start:]))

    exec_time = None
    clock_time = None

    if log_file.exists():
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(
                    r"ExecutionTime\s*=\s*([0-9.eE+-]+)\s*s\s+ClockTime\s*=\s*([0-9.eE+-]+)\s*s",
                    line,
                )
                if m:
                    exec_time = float(m.group(1))
                    clock_time = float(m.group(2))

    runtime_text = (
        f"{format_seconds(exec_time)} CPU | {format_seconds(clock_time)} wall"
        if exec_time is not None
        else "Not found"
    )

    force_plot, conv_plot, first_conv_idx = create_force_plots(
        times, thrusts, report_dir, rev_time
    )

    residual_plot = create_residual_plot(
    residual_file,
    report_dir,
    rev_time,
    latest_time,
    )
    c = canvas.Canvas(str(output_pdf), pagesize=A4)
    w, h = A4

    y = h - 60

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "CFD Simulation Report")

    y -= 35
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Case Information")

    c.setFont("Helvetica", 11)

    y -= 22
    c.drawString(50, y, f"Case: {case_path.name}")

    y -= 22
    c.drawString(50, y, f"Mode: {mode}")

    y -= 22
    c.drawString(50, y, f"RPM: {rpm}")

    y -= 22
    c.drawString(50, y, f"One revolution time: {rev_time:.6f} s")

    y -= 22
    c.drawString(50, y, f"Simulated time: {latest_time:.6f} s")

    y -= 22
    c.drawString(50, y, f"Effective simulated revolutions: {eff_revs:.2f}")

    y -= 22
    c.drawString(50, y, f"Runtime (rank0): {runtime_text}")

    y -= 40

    # -----------------------------
    # Mesh Information
    # -----------------------------
    y -= 40
    mesh_section_y = y

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Mesh Information")

    c.setFont("Helvetica", 11)

    y -= 22
    c.drawString(50, y, f"Mesh status: {mesh_info['status']}")

    y -= 22
    c.drawString(50, y, f"Cells: {mesh_info['cells']}")

    y -= 22
    c.drawString(50, y, f"Faces: {mesh_info['faces']}")

    y -= 22
    c.drawString(50, y, f"Points: {mesh_info['points']}")

    y -= 22
    c.drawString(50, y, f"Max aspect ratio: {mesh_info['max_aspect_ratio']}")

    y -= 22
    c.drawString(50, y, f"Max skewness: {mesh_info['max_skewness']}")

    y -= 22
    c.drawString(50, y, f"Max non-orthogonality: {mesh_info['max_non_orthogonality']}")

    if mesh_element_plot is not None:
        c.drawImage(
            str(mesh_element_plot),
            320,
            mesh_section_y - 190,
            width=220,
            height=170,
            preserveAspectRatio=True,
            mask="auto",
        )
    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Main Result")

    y -= 24
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Last 1-rev averaged thrust: {thrust_avg:.6f} N")

    if first_conv_idx is not None:
        y -= 24
        c.setFont("Helvetica", 11)
        c.drawString(
            50,
            y,
            f"Force convergence start: {times[first_conv_idx]:.6f} s",
        )

    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 50, "Force Evaluation")

    c.drawImage(str(force_plot), 40, 440, width=510, height=240)
    c.drawImage(str(conv_plot), 40, 150, width=510, height=240)

    if residual_plot is not None:
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 50, "Residual Evaluation")
        c.drawImage(str(residual_plot), 40, 350, width=510, height=260)

    if yplus_plot is not None:
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 50, "Wall Treatment Evaluation")

        c.drawImage(
            str(yplus_plot),
            80,
            h - 360,
            width=430,
            height=260,
            preserveAspectRatio=True,
            mask="auto",
        )

    c.save()

    print(f"Report created: {output_pdf}")

    return {
        "case_path": str(case_path),
        "mode": mode,
        "rpm": float(rpm),
        "one_rev_time_s": rev_time,
        "simulated_time_s": latest_time,
        "effective_revolutions": eff_revs,
        "mesh_info": mesh_info,
        "mesh_element_types": mesh_element_types,
        "yplus_plot_path": str(yplus_plot) if yplus_plot is not None else None,
        "mesh_element_plot_path": str(mesh_element_plot) if mesh_element_plot is not None else None,
        "last_one_rev_avg_thrust_N": thrust_avg,
        "execution_time_s": exec_time,
        "clock_time_s": clock_time,
        "force_convergence_start_s": (
            float(times[first_conv_idx]) if first_conv_idx is not None else None
        ),
        "pdf_path": str(output_pdf),
        "force_plot_path": str(force_plot),
        "force_convergence_plot_path": str(conv_plot),
        "residual_plot_path": str(residual_plot) if residual_plot is not None else None,
    }

#create_simulation_report(r"C:\Users\jonas\Downloads\study\10x7E_7000RPM_blocks_resolution_16_48_16", 7000, "MRF")
