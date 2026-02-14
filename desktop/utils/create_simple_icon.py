"""
Create a simple icon from the Asymptote branding.
Since SVG conversion requires system libraries, this creates a simple programmatic icon.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_icon(ico_path: Path, sizes=[16, 32, 48, 64, 128, 256]):
    """Create a simple 'A' icon for Asymptote."""

    print(f"Creating icon at {ico_path}...")

    images = []

    for size in sizes:
        print(f"  Generating {size}x{size} image...")

        # Create image with transparency
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Colors from Asymptote branding
        primary_color = (75, 85, 255)  # Blue from branding
        white = (255, 255, 255)

        # Draw circle background
        margin = size // 8
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=primary_color,
            outline=None
        )

        # Draw 'A' letter
        try:
            # Try to use a nice font
            font_size = int(size * 0.6)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Draw text centered
        text = "A"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2 - bbox[0]
        y = (size - text_height) // 2 - bbox[1]

        draw.text((x, y), text, fill=white, font=font)

        images.append(img)

    # Save as ICO
    print(f"  Saving {ico_path}...")
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images]
    )

    print(f"✓ Successfully created {ico_path}")
    print(f"\nNote: This is a simple programmatic icon.")
    print(f"For a better icon, consider using an online SVG to ICO converter:")
    print(f"  - https://convertio.co/svg-ico/")
    print(f"  - https://cloudconvert.com/svg-to-ico")
    print(f"\nThen replace: {ico_path}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    ico_path = script_dir / 'icon.ico'

    create_icon(ico_path)
