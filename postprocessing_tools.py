from pathlib import Path
import re
import matplotlib.pyplot as plt


def plot_yplus_classes(yplus_file, patch_name="propellerTip", show_percent=True):
    """
    Read an OpenFOAM yPlus field file, extract yPlus values from one boundary patch,
    classify them into:
        - y+ < 5
        - 5 <= y+ <= 30
        - y+ > 30
    and plot a bar chart.

    Parameters
    ----------
    yplus_file : str or Path
        Path to the OpenFOAM yPlus file (e.g. 0.0237498/yPlus)
    patch_name : str
        Name of the boundary patch to read, e.g. "walls", "propellerTip"
    show_percent : bool
        If True, plot percentages. If False, plot absolute counts.

    Returns
    -------
    dict
        Dictionary with counts, percentages, and extracted values.
    """
    yplus_file = Path(yplus_file)

    if not yplus_file.exists():
        raise FileNotFoundError(f"File not found: {yplus_file}")

    text = yplus_file.read_text(encoding="utf-8", errors="ignore")

    # Find the chosen patch block inside boundaryField
    patch_pattern = rf"{re.escape(patch_name)}\s*\{{(.*?)\}}"
    patch_match = re.search(patch_pattern, text, re.DOTALL)

    if not patch_match:
        raise ValueError(f"Patch '{patch_name}' not found in file.")

    patch_block = patch_match.group(1)

    # Extract the nonuniform List<scalar> block
    list_pattern = r"nonuniform\s+List<scalar>\s*(\d+)\s*\((.*?)\)"
    list_match = re.search(list_pattern, patch_block, re.DOTALL)

    if not list_match:
        raise ValueError(
            f"No 'nonuniform List<scalar>' found for patch '{patch_name}'."
        )

    expected_n = int(list_match.group(1))
    values_block = list_match.group(2)

    # Extract all floating-point values from the list body
    values = [
        float(v)
        for v in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", values_block)
    ]

    if len(values) != expected_n:
        print(
            f"Warning: expected {expected_n} values, but parsed {len(values)} values."
        )

    if not values:
        raise ValueError(f"No yPlus values could be extracted for patch '{patch_name}'.")

    total = len(values)

    count_below_5 = sum(v < 5 for v in values)
    count_5_to_30 = sum(5 <= v <= 30 for v in values)
    count_above_30 = sum(v > 30 for v in values)

    categories = ["y+ < 5", "5 ≤ y+ ≤ 30", "y+ > 30"]
    counts = [count_below_5, count_5_to_30, count_above_30]
    percentages = [100 * c / total for c in counts]

    plot_values = percentages if show_percent else counts
    ylabel = "Percentage of faces [%]" if show_percent else "Number of faces"

    plt.figure(figsize=(8, 5))
    bars = plt.bar(categories, plot_values)
    plt.ylabel(ylabel)
    plt.title(f"yPlus distribution for patch '{patch_name}'\nFile: {yplus_file.name}")

    # Annotate bars
    for bar, c, p in zip(bars, counts, percentages):
        label = f"{p:.1f}%" if show_percent else f"{c}"
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            label,
            ha="center",
            va="bottom"
        )

    plt.tight_layout()
    plt.show()

    return {
        "patch": patch_name,
        "total_values": total,
        "counts": {
            "below_5": count_below_5,
            "between_5_and_30": count_5_to_30,
            "above_30": count_above_30,
        },
        "percentages": {
            "below_5": percentages[0],
            "between_5_and_30": percentages[1],
            "above_30": percentages[2],
        },
        "values": values,
    }


result = plot_yplus_classes(r"C:\Users\jonas\Downloads\SimulationSpace\11x8E@7000\0.0571013\yPlus", patch_name="propellerTip", show_percent=True)


print(result["percentages"])