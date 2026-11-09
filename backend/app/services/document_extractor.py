import pymupdf
import pytesseract

from PIL import Image
from pathlib import Path
from io import BytesIO
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

def extract_text_from_document(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError("Document not found")

    extension = path.suffix.lower()

    # Extract text from PDF
    if extension == ".pdf":
        pdf = pymupdf.open(file_path)
        extracted_text = []

        for page_number, page in enumerate(pdf):
            text = page.get_text("text").strip()

            # Use OCR if the page has no selectable text
            if not text:
                pix = page.get_pixmap(dpi=200)
                image = Image.open(
                    BytesIO(pix.tobytes("png"))
                )
                text = pytesseract.image_to_string(image)

            extracted_text.append(text)

        pdf.close()
        return "\n".join(extracted_text)

    # Extract text from images
    elif extension in [".jpg", ".jpeg", ".png"]:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)

    else:
        raise ValueError("Unsupported document format")