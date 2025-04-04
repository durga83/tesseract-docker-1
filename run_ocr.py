import os
import fitz  # PyMuPDF
import subprocess
import re
from pathlib import Path
from pdf2image import convert_from_path
import tempfile
import shutil

INPUT_FOLDER = "./input"
OUTPUT_FOLDER = "./output"
TEMP_FOLDER = "./temp_images"

os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

def render_pdf_to_images(pdf_path):
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_number in range(len(doc)):
            pix = doc.load_page(page_number).get_pixmap(dpi=300)
            image_filename = f"{Path(pdf_path).stem}_page{page_number + 1}.png"
            image_path = os.path.join(TEMP_FOLDER, image_filename)
            pix.save(image_path)
            images.append(image_filename)
        doc.close()
    except Exception as e:
        print(f"❌ Error rendering PDF: {e}")
    return images

def render_docx_to_images(docx_path):
    images = []
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_pdf_path = os.path.join(temp_dir, "converted.pdf")
            subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, docx_path], check=True)
            pdf_images = convert_from_path(temp_pdf_path, dpi=300)
            for i, img in enumerate(pdf_images):
                image_filename = f"{Path(docx_path).stem}_page{i + 1}.png"
                image_path = os.path.join(TEMP_FOLDER, image_filename)
                img.save(image_path)
                images.append(image_filename)
    except Exception as e:
        print(f"❌ Error converting DOCX to images: {e}")
    return images

def run_tesseract_on_image(image_filename):
    input_path = f"/app/temp_images/{image_filename}"
    output_path = f"/app/output/{Path(image_filename).stem}"
    command = [
        "docker", "exec", "tesseract-runner",
        "tesseract", input_path, output_path, "-l", "eng"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Tesseract error for {image_filename}: {result.stderr}")
    else:
        print(f"✅ OCR done: {image_filename}")

def clean_ocr_text(text):
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4},\s+\d{1,2}:\d{2}\s+(AM|PM)", line): continue
        if "file://" in line.lower(): continue
        if line == "": continue
        line = re.sub(r'^(e@|e\s+|@|-|\*|•)\s*', '', line)
        line = re.sub(r'\s{2,}', ' ', line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def process_file(filename):
    filepath = os.path.join(INPUT_FOLDER, filename)
    ext = filename.lower().split(".")[-1]

    print(f"📄 Processing {filename}...")
    if ext == "pdf":
        images = render_pdf_to_images(filepath)
    elif ext == "docx":
        images = render_docx_to_images(filepath)
    elif ext in ("png", "jpg", "jpeg"):
        # Just copy to temp_images
        dst = os.path.join(TEMP_FOLDER, filename)
        shutil.copy(filepath, dst)
        images = [filename]
    else:
        print(f"❌ Unsupported file type: {ext}")
        return

    images.sort(key=lambda name: int(re.findall(r'page(\d+)', name)[0]) if "page" in name else 0)

    for img in images:
        run_tesseract_on_image(img)

    merged_text = ""
    for img in images:
        txt_filename = f"{Path(img).stem}.txt"
        txt_path = os.path.join(OUTPUT_FOLDER, txt_filename)
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
                cleaned = clean_ocr_text(raw_text)
                merged_text += cleaned + "\n"
            # Delete per-page txt after reading
            os.remove(txt_path)

    final_txt_filename = f"{Path(filename).stem}.txt"
    final_txt_path = os.path.join(OUTPUT_FOLDER, final_txt_filename)
    with open(final_txt_path, "w", encoding="utf-8") as f:
        f.write(merged_text)

    print(f"📄 Final merged text saved to {final_txt_filename}")
    print(f"🧹 Deleted individual page-level text files.")

if __name__ == "__main__":
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith((".pdf", ".docx", ".png", ".jpg", ".jpeg"))]
    if not files:
        print("⚠️ No input files found.")
    else:
        for file in files:
            process_file(file)
    print("✅ OCR processing completed!")
