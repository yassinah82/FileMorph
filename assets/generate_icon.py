import os
from pathlib import Path
from PIL import Image, ImageDraw

def generate_app_icon():
    assets_dir = Path("d:/antigravty/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Create 256x256 high-resolution icon
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background (gradient dark slate / blue)
    # Background rounded rect
    draw.rounded_rectangle([12, 12, 244, 244], radius=48, fill=(30, 41, 59, 255), outline=(59, 130, 246, 255), width=6)

    # Draw a stylized two-document / exchange arrow emblem
    # Left sheet (Doc)
    draw.rounded_rectangle([48, 54, 130, 168], radius=10, fill=(71, 85, 105, 255), outline=(148, 163, 184, 255), width=4)
    # Right sheet (Converted)
    draw.rounded_rectangle([126, 88, 208, 202], radius=10, fill=(37, 99, 235, 255), outline=(96, 165, 250, 255), width=4)

    # Convert cycle arrows in the center
    # Top arrow (pointing right)
    draw.line([(88, 80), (168, 80)], fill=(248, 250, 252, 255), width=6)
    draw.polygon([(164, 70), (184, 80), (164, 90)], fill=(248, 250, 252, 255))

    # Bottom arrow (pointing left)
    draw.line([(168, 176), (88, 176)], fill=(56, 189, 248, 255), width=6)
    draw.polygon([(92, 166), (72, 176), (92, 186)], fill=(56, 189, 248, 255))

    # Save PNG
    png_path = assets_dir / "icon.png"
    img.save(png_path, "PNG")

    # Save ICO with standard sizes
    ico_path = assets_dir / "icon.ico"
    img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Generated icons at {png_path} and {ico_path}")

if __name__ == "__main__":
    generate_app_icon()
