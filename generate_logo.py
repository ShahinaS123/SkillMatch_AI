from PIL import Image, ImageDraw, ImageFont
import os
import glob

def create_professional_logo():
    # We draw at a very high resolution (4x) for anti-aliasing (smooth edges)
    scale = 4
    width, height = 800 * scale, 400 * scale
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255)) # White background
    draw = ImageDraw.Draw(image)

    # Professional Color Palette
    navy_blue = (10, 37, 64, 255)
    electric_cyan = (0, 180, 216, 255)
    emerald_green = (40, 167, 69, 255)
    text_color = (33, 37, 41, 255)

    # --- Draw the Graphic (Two overlapping circles) ---
    center_x, center_y = (width // 2), (height // 2) - (50 * scale)
    radius = 100 * scale
    offset = 50 * scale

    # Left Circle (Academia - Navy)
    left_box = (center_x - radius - offset, center_y - radius, 
                center_x + radius - offset, center_y + radius)
    draw.ellipse(left_box, fill=navy_blue)

    # Right Circle (Industry - Cyan) with transparency to show overlap
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    right_box = (center_x - radius + offset, center_y - radius, 
                 center_x + radius + offset, center_y + radius)
    overlay_draw.ellipse(right_box, fill=(0, 180, 216, 150)) # 150 is transparency
    
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    # Draw the Intersection (Green Checkmark)
    check_points = [
        (center_x - 25 * scale, center_y),
        (center_x - 5 * scale, center_y + 20 * scale),
        (center_x + 35 * scale, center_y - 25 * scale)
    ]
    draw.line(check_points, fill=emerald_green, width=15 * scale, joint="curve")

    # --- Draw the Text ---
    text_main = "SkillMatch AI"
    text_sub = "Engineering Instrumentation"

    # Dynamically find a TrueType font on the system
    font_main = None
    font_sub = None
    
    # Search for common fonts in Linux/WSL and Windows paths
    possible_fonts = glob.glob('/usr/share/fonts/**/*.ttf', recursive=True) + \
                     glob.glob('/mnt/c/Windows/Fonts/**/arial*.ttf', recursive=True)
    
    chosen_font_path = None
    for f_path in possible_fonts:
        if "DejaVuSans-Bold.ttf" in f_path or "arialbd.ttf" in f_path or "LiberationSans-Bold" in f_path:
            chosen_font_path = f_path
            break
            
    # Fallback if no specific bold font is found, just grab the first ttf
    if not chosen_font_path and possible_fonts:
        chosen_font_path = possible_fonts[0]

    if chosen_font_path:
        try:
            font_main = ImageFont.truetype(chosen_font_path, 80 * scale)
            font_sub = ImageFont.truetype(chosen_font_path, 30 * scale)
            print(f"✅ Using font: {chosen_font_path}")
        except IOError:
            pass

    # Absolute fallback if all else fails
    if not font_main:
        print("⚠️ Warning: Using default pixel font. Logo text may look blocky.")
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Calculate text width to center it
    bbox_main = draw.textbbox((0, 0), text_main, font=font_main)
    text_width_main = bbox_main[2] - bbox_main[0]
    text_x_main = (width - text_width_main) // 2
    text_y_main = center_y + radius + (40 * scale)

    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_sub)
    text_width_sub = bbox_sub[2] - bbox_sub[0]
    text_x_sub = (width - text_width_sub) // 2
    text_y_sub = text_y_main + (70 * scale)

    # Draw the text
    draw.text((text_x_main, text_y_main), text_main, font=font_main, fill=text_color)
    draw.text((text_x_sub, text_y_sub), text_sub, font=font_sub, fill=text_color)

    # Downscale the image to final size for anti-aliasing
    final_size = (800, 400)
    image = image.resize(final_size, Image.Resampling.LANCZOS)

    # --- FIX FOR WSL ERROR: Use absolute path and explicit format ---
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(current_dir, "logo.png")
    
    try:
        # Explicitly specify format="PNG" to avoid WSL extension parsing issues
        image.save(save_path, format="PNG")
        print(f"✅ Success: Professional 'logo.png' has been created at:\n{save_path}")
    except Exception as e:
        print(f"❌ Failed to save logo: {e}")

if __name__ == "__main__":
    create_professional_logo()