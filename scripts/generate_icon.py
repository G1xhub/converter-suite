
import os
from PIL import Image, ImageDraw, ImageOps

def create_icon(output_path):
    size = (512, 512)
    # Create image with transparent background
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background - Rounded Rectangle
    bg_color = (15, 23, 42)  # Dark slate #0F172A
    rect_coords = [0, 0, 512, 512]
    radius = 100
    draw.rounded_rectangle(rect_coords, radius=radius, fill=bg_color)
    
    # Gradient effect (simulated with concentric rectangles or just simple)
    # Let's keep it simple flat for stability
    
    # Draw "Converter" symbol - Two arrows forming a circle
    # Center: 256, 256
    center = (256, 256)
    radius_circle = 140
    arrow_width = 40
    color_primary = (6, 182, 212) # Cyan #06B6D4
    
    # Draw arc 1
    bbox = [center[0]-radius_circle, center[1]-radius_circle, center[0]+radius_circle, center[1]+radius_circle]
    draw.arc(bbox, start=30, end=150, fill=color_primary, width=arrow_width)
    
    # Draw arrow head 1
    # Simple triangle at end of arc
    # (Approximation coordinates)
    # End of arc at 150 degrees
    # ... actually drawing nice arrows is hard in pure PIL without math.
    
    # Let's draw a stylized "C" and "S" or just a nice shape.
    # Let's draw a hexagon with arrows.
    
    # Alternative: Draw a thick ring with gaps
    draw.arc(bbox, start=20, end=160, fill=color_primary, width=arrow_width)
    draw.arc(bbox, start=200, end=340, fill=color_primary, width=arrow_width)
    
    # Arrow heads
    # Head 1 at 160 deg
    # Head 2 at 340 deg
    
    # Just save it as is, a broken ring looks "techy" enough.
    # Add a central dot or square
    
    rect_inner = [center[0]-40, center[1]-40, center[0]+40, center[1]+40]
    draw.rounded_rectangle(rect_inner, radius=10, fill=(255, 255, 255))

    # Save as PNG first
    png_path = output_path.replace('.ico', '.png')
    img.save(png_path)
    print(f"Generated PNG: {png_path}")

    # Save as ICO
    img.save(output_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Generated ICO: {output_path}")

if __name__ == "__main__":
    output_dir = os.path.join("src", "assets")
    os.makedirs(output_dir, exist_ok=True)
    create_icon(os.path.join(output_dir, "icon.ico"))
