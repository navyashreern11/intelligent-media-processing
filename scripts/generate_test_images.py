import os
from PIL import Image, ImageDraw, ImageFilter

def generate_images():
    output_dir = "sample_images"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Base Sharp Image (Also acts as standard vehicle plate mockup)
    # 600x400, white background, black text representing Indian vehicle plate format
    img_sharp = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_sharp)
    # Draw simple rectangles to represent license plate frame
    draw.rectangle([50, 150, 550, 250], fill=(240, 240, 240), outline=(0, 0, 0), width=4)
    # Draw text. Note: We use default font which is small, but we can draw larger mock characters using line drawings or blocks
    # Since default font size might be tiny, we draw simple blocks or line segments for characters to be readable by OCR,
    # or just write standard text using default font.
    draw.text((100, 180), "KA01AB1234", fill=(0, 0, 0))
    img_sharp.save(os.path.join(output_dir, "sharp.png"))
    print("Generated: sample_images/sharp.png")

    # 2. Blurry Image
    # Copy of sharp image, but heavily blurred
    img_blurry = img_sharp.filter(ImageFilter.GaussianBlur(10.0))
    img_blurry.save(os.path.join(output_dir, "blurry.png"))
    print("Generated: sample_images/blurry.png")

    # 3. Dark Image
    # 600x400, dark grey/black background
    img_dark = Image.new("RGB", (600, 400), color=(10, 10, 10))
    draw_dark = ImageDraw.Draw(img_dark)
    draw_dark.text((100, 180), "MH12DE1432", fill=(40, 40, 40))
    img_dark.save(os.path.join(output_dir, "dark.png"))
    print("Generated: sample_images/dark.png")

    # 4. Small Image
    # 150x150, below minimum required dimensions of 200x200
    img_small = Image.new("RGB", (150, 150), color=(200, 200, 200))
    img_small.save(os.path.join(output_dir, "small.png"))
    print("Generated: sample_images/small.png")

    # 5. Tampered Mockup (Contains editing software metadata or ELA anomalies)
    # Let's save a copy as JPEG to simulate JPEG compression differences when resaved
    img_tampered = img_sharp.copy()
    draw_t = ImageDraw.Draw(img_tampered)
    draw_t.rectangle([200, 180, 400, 220], fill=(255, 0, 0)) # Red block to simulate modification
    img_tampered.save(os.path.join(output_dir, "tampered.jpg"), quality=95)
    print("Generated: sample_images/tampered.jpg")

if __name__ == "__main__":
    generate_images()
