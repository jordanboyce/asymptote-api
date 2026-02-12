"""
Simple SVG to ICO converter using svglib and reportlab.

This approach doesn't require system Cairo libraries.
"""

from pathlib import Path
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

def svg_to_ico(svg_path: Path, ico_path: Path, sizes=[16, 32, 48, 64, 128, 256]):
    """
    Convert SVG to ICO file with multiple sizes.

    Args:
        svg_path: Path to input SVG file
        ico_path: Path to output ICO file
        sizes: List of icon sizes to include
    """
    print(f"Converting {svg_path.name} to {ico_path.name}...")

    # Load SVG
    drawing = svg2rlg(svg_path)

    if drawing is None:
        raise ValueError(f"Failed to load SVG: {svg_path}")

    # Generate images at different sizes
    images = []
    for size in sizes:
        print(f"  Generating {size}x{size} image...")

        # Render SVG to PNG bytes
        png_data = renderPM.drawToString(drawing, fmt='PNG', dpi=72, bg=0xFFFFFF)

        # Open with PIL and resize
        img = Image.open(Path(__file__).parent / 'temp.png') if Path('temp.png').exists() else None

        # Better approach: render at target size
        scale_x = size / drawing.width
        scale_y = size / drawing.height
        scale = min(scale_x, scale_y)

        drawing_copy = svg2rlg(svg_path)
        drawing_copy.width = size
        drawing_copy.height = size
        drawing_copy.scale(scale, scale)

        # Render to bytes
        png_bytes = renderPM.drawToString(drawing_copy, fmt='PNG')

        # Convert to PIL Image
        from io import BytesIO
        img = Image.open(BytesIO(png_bytes))

        # Ensure RGBA mode
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        images.append(img)

    # Save as ICO
    print(f"  Saving {ico_path}...")
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images]
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
        print(f"Please install: pip install svglib reportlab pillow")
        print(f"\nDetails: {e}")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
