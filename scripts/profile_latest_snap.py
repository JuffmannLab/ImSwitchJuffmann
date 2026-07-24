from pathlib import Path
import argparse
import csv

import numpy as np
import tifffile as tiff


try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


def find_latest_snap(recordings_root: Path) -> Path:
    """Find the newest snap TIFF inside the ImSwitch recordings folder."""
    candidates = list(recordings_root.rglob("*_snap*.tif*"))

    if not candidates:
        candidates = list(recordings_root.rglob("*.tif*"))

    if not candidates:
        raise FileNotFoundError(
            f"No TIFF files found inside: {recordings_root}"
        )

    return max(candidates, key=lambda p: p.stat().st_mtime)


def prepare_image(image: np.ndarray) -> np.ndarray:
    """Return a 2D grayscale image."""
    if image.ndim == 2:
        return image

    # RGB/RGBA image
    if image.ndim == 3 and image.shape[-1] in (3, 4):
        return image[..., :3].mean(axis=2)

    # If it is a stack, use the first frame for now.
    if image.ndim == 3:
        return image[0]

    raise ValueError(f"Unsupported image shape: {image.shape}")


def calculate_profile(image: np.ndarray, mode: str):
    """Calculate a 1D intensity profile from a 2D image."""
    height, width = image.shape

    if mode == "horizontal":
        # Average all rows. One value per x pixel.
        profile = image.mean(axis=0)
        pixels = np.arange(width)
        x_label = "x pixel"
        title = "Horizontal averaged profile"

    elif mode == "vertical":
        # Average all columns. One value per y pixel.
        profile = image.mean(axis=1)
        pixels = np.arange(height)
        x_label = "y pixel"
        title = "Vertical averaged profile"

    elif mode == "center-horizontal":
        # Use only the central row.
        profile = image[height // 2, :]
        pixels = np.arange(width)
        x_label = "x pixel"
        title = "Horizontal center-line profile"

    elif mode == "center-vertical":
        # Use only the central column.
        profile = image[:, width // 2]
        pixels = np.arange(height)
        x_label = "y pixel"
        title = "Vertical center-line profile"

    else:
        raise ValueError(f"Unknown profile mode: {mode}")

    return pixels, profile, x_label, title


def save_csv(csv_path: Path, pixels: np.ndarray, profile: np.ndarray):
    """Save profile data as CSV."""
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pixel", "gray_value"])

        for pixel, value in zip(pixels, profile):
            writer.writerow([int(pixel), float(value)])


def save_plot(
    png_path: Path,
    pixels: np.ndarray,
    profile: np.ndarray,
    image_path: Path,
    image_shape,
    x_label: str,
    title: str,
):
    """Save profile plot as PNG."""
    if plt is None:
        print("Matplotlib is not available, so only the CSV was saved.")
        print("Install it with: python -m pip install matplotlib")
        return

    plt.figure(figsize=(9, 4.5))
    plt.plot(pixels, profile)
    plt.xlabel(x_label)
    plt.ylabel("gray value")
    plt.title(f"{title}\n{image_path.name}, shape={image_shape}")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create an intensity profile from the latest ImSwitch snap TIFF."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Optional path to a specific TIFF file. If omitted, the latest snap is used.",
    )

    parser.add_argument(
        "--recordings-root",
        type=str,
        default="imswitch/ImSwitch/recordings",
        help="Path to the ImSwitch recordings folder.",
    )

    parser.add_argument(
        "--mode",
        choices=[
            "horizontal",
            "vertical",
            "center-horizontal",
            "center-vertical",
        ],
        default="horizontal",
        help="Profile type to calculate.",
    )

    args = parser.parse_args()

    if args.input is None:
        image_path = find_latest_snap(Path(args.recordings_root))
    else:
        image_path = Path(args.input)

    image = tiff.imread(image_path)
    image = prepare_image(image)

    pixels, profile, x_label, title = calculate_profile(image, args.mode)

    output_base = image_path.with_suffix("")
    csv_path = output_base.with_name(output_base.name + f"_profile_{args.mode}.csv")
    png_path = output_base.with_name(output_base.name + f"_profile_{args.mode}.png")

    save_csv(csv_path, pixels, profile)
    save_plot(png_path, pixels, profile, image_path, image.shape, x_label, title)

    print("Input image:")
    print(f"  {image_path}")
    print(f"Image shape:")
    print(f"  {image.shape}")
    print(f"Profile mode:")
    print(f"  {args.mode}")
    print(f"Profile points:")
    print(f"  {len(profile)}")
    print(f"Gray value range:")
    print(f"  min={profile.min():.3f}, max={profile.max():.3f}, mean={profile.mean():.3f}")
    print("Saved CSV:")
    print(f"  {csv_path}")
    print("Saved plot:")
    print(f"  {png_path}")


if __name__ == "__main__":
    main()