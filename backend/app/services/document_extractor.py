
import os
import shutil
import pymupdf
import pytesseract

from PIL import Image
from pathlib import Path
from io import BytesIO


# Configure Tesseract for Windows or Linux
tesseract_path = (
    os.getenv("TESSERACT_CMD")
    or shutil.which("tesseract")
)

if not tesseract_path and os.name == "nt":
    windows_path = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    if windows_path.exists():
        tesseract_path = str(windows_path)

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path


def extract_text_from_document(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError("Document not found")

    extension = path.suffix.lower()

    # Extract text from PDF
    if extension == ".pdf":
        extracted_text = []

        with pymupdf.open(file_path) as pdf:
            for page in pdf:
                text = page.get_text("text").strip()

                # Use OCR if the page has no selectable text
                if not text:
                    if not shutil.which("tesseract") and not (
                        tesseract_path
                    ):
                        raise RuntimeError(
                            "Tesseract OCR is not installed or configured."
                        )

                    pix = page.get_pixmap(dpi=200)
                    image = Image.open(
                        BytesIO(pix.tobytes("png"))
                    )
                    text = pytesseract.image_to_string(image)

                extracted_text.append(text)

        return "\n".join(extracted_text)

    # Extract text from images
    elif extension in [".jpg", ".jpeg", ".png"]:
        if not shutil.which("tesseract") and not tesseract_path:
            raise RuntimeError(
                "Tesseract OCR is not installed or configured."
            )

        image = Image.open(file_path)
        return pytesseract.image_to_string(image)

    else:
        raise ValueError("Unsupported document format")
