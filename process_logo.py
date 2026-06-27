import pymupdf as fitz
from PIL import Image
import os

pdf_path = r"C:\Users\NACHI\.gemini\antigravity\brain\e427ce44-dc02-491a-93f4-00ff89515e60\media__1782537665354.pdf"
out_dir = r"C:\Users\NACHI\.gemini\antigravity\scratch\EarthX_designs\static\uploads"

def remove_bg(img, bg_color, threshold=40):
    """Remove background color and make it transparent."""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    
    for item in data:
        r, g, b, a = item
        if bg_color == 'black':
            if r < threshold and g < threshold and b < threshold:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)
        elif bg_color == 'white':
            if r > (255 - threshold) and g > (255 - threshold) and b > (255 - threshold):
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
    img.putdata(new_data)
    return img

def auto_crop(img):
    """Crop transparent borders."""
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

print("Opening PDF...")
doc = fitz.open(pdf_path)
page = doc.load_page(0)
pix = page.get_pixmap(dpi=300)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
width, height = img.size
print(f"Page size: {width}x{height}")

# The PDF has 3 sections:
# Top: White logo on BLACK background
# Middle: Black logo on WHITE background  
# Bottom: Small EX icon on WHITE background (with a frame/card)

section_h = height // 3

# ---- LOGO WHITE (for dark backgrounds like footer, hero) ----
section1 = img.crop((0, 0, width, section_h))
s1_clean = remove_bg(section1, 'black', threshold=50)
s1_clean = auto_crop(s1_clean)
# Add some padding
pad = 10
s1_padded = Image.new("RGBA", (s1_clean.width + pad*2, s1_clean.height + pad*2), (0, 0, 0, 0))
s1_padded.paste(s1_clean, (pad, pad))
s1_padded.save(os.path.join(out_dir, "logo_white.png"), "PNG")
print(f"Saved logo_white.png ({s1_padded.size[0]}x{s1_padded.size[1]})")

# ---- LOGO BLACK (for light backgrounds like navbar) ----
# Crop a bit more tightly from the middle section to avoid the black border at top
section2 = img.crop((0, section_h + 40, width, section_h * 2 - 10))
s2_clean = remove_bg(section2, 'white', threshold=35)
s2_clean = auto_crop(s2_clean)
s2_padded = Image.new("RGBA", (s2_clean.width + pad*2, s2_clean.height + pad*2), (0, 0, 0, 0))
s2_padded.paste(s2_clean, (pad, pad))
s2_padded.save(os.path.join(out_dir, "logo_black.png"), "PNG")
print(f"Saved logo_black.png ({s2_padded.size[0]}x{s2_padded.size[1]})")

# ---- LOGO SMALL / ICON (compact EX version for favicon) ----
# The bottom section has a white card with EX icon inside
section3 = img.crop((0, section_h * 2, width, height))
# This section is mostly white with a light grey card, remove white bg
s3_clean = remove_bg(section3, 'white', threshold=45)
s3_clean = auto_crop(s3_clean)
if s3_clean.size[0] > 10:
    s3_padded = Image.new("RGBA", (s3_clean.width + pad*2, s3_clean.height + pad*2), (0, 0, 0, 0))
    s3_padded.paste(s3_clean, (pad, pad))
    s3_padded.save(os.path.join(out_dir, "logo_small.png"), "PNG")
    print(f"Saved logo_small.png ({s3_padded.size[0]}x{s3_padded.size[1]})")
    
    # Create favicon
    favicon_img = s3_padded.resize((32, 32), Image.LANCZOS)
    favicon_path = os.path.join(out_dir, "..", "favicon.ico")
    favicon_img.save(favicon_path, format='ICO', sizes=[(32,32)])
    print("Saved favicon.ico")
else:
    print("Small logo extraction failed, using black logo for favicon")
    favicon_img = s2_padded.resize((32, 32), Image.LANCZOS)
    favicon_path = os.path.join(out_dir, "..", "favicon.ico")
    favicon_img.save(favicon_path, format='ICO', sizes=[(32,32)])

print("\nDone! All logos extracted with transparent backgrounds.")
