"""Convert SVG to ICO file for Windows installer."""

from pathlib import Path
from PIL import Image
import cairosvg
import io

def svg_to_ico(svg_path: Path, ico_path: Path, sizes=[16, 32, 48, 64, 128, 256]):
    """
    Convert SVG to ICO file with multiple sizes.

    Args:
        svg_path: Path to input SVG file
        ico_path: Path to output ICO file
        sizes: List of icon sizes to include (default: standard Windows sizes)
    """
    print(f"Converting {svg_path.name} to {ico_path.name}...")

    # Read SVG file
    with open(svg_path, 'rb') as f:
        svg_data = f.read()

    # Convert SVG to PNG at different sizes
    images = []
    for size in sizes:
        print(f"  Generating {size}x{size} image...")
        # Convert SVG to PNG bytes at specific size
        png_data = cairosvg.svg2png(
            bytestring=svg_data,
            output_width=size,
            output_height=size
        )

        # Open PNG with PIL
        img = Image.open(io.BytesIO(png_data))
        images.append(img)

    # Save as ICO with all sizes
    print(f"  Saving {ico_path}...")
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    print(f"✓ Successfully created {ico_path}")


if __name__ == "__main__":
    # Get paths
    script_dir = Path(__file__).parent
    static_dir = script_dir.parent / 'static'

    # Convert icon_black.svg to icon.ico
    svg_path = static_dir / 'icon_black.svg'
    ico_path = script_dir / 'icon.ico'

    if not svg_path.exists():
        print(f"Error: {svg_path} not found")
        exit(1)

    try:
        svg_to_ico(svg_path, ico_path)
        print(f"\nIcon created at: {ico_path}")
        print("\nYou can now use this icon in your installer!")
    except ImportError as e:
        print(f"Error: Missing required package")
        print(f"Please install: pip install pillow cairosvg")
        print(f"\nDetails: {e}")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
