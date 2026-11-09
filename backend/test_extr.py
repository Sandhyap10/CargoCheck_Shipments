from pathlib import Path
from app.services.document_extractor import extract_text_from_document

file_path = Path("uploads/1/6e89dfb2f0134306b61528ec7de7fcb9.pdf")

print("File exists:", file_path.exists())

text = extract_text_from_document(str(file_path))

print("\n========== EXTRACTED TEXT ==========\n")
print(text)