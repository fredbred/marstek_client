"""Script pour extraire le texte du PDF Marstek API."""

import sys
from pathlib import Path

try:
    import pypdf
except ImportError:
    print("Installing pypdf...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    import pypdf


def extract_pdf_text(pdf_path: Path) -> str:
    """Extrait le texte d'un PDF.

    Args:
        pdf_path: Chemin vers le PDF

    Returns:
        Texte extrait du PDF
    """
    text = ""
    with open(pdf_path, "rb") as file:
        reader = pypdf.PdfReader(file)
        for page_num, page in enumerate(reader.pages, 1):
            text += f"\n--- Page {page_num} ---\n"
            text += page.extract_text()
    return text


if __name__ == "__main__":
    pdf_path = Path("docs/MarstekDeviceOpenApi.pdf")
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        sys.exit(1)
    
    print("Extracting text from PDF...")
    text = extract_pdf_text(pdf_path)
    
    output_path = Path("docs/MarstekDeviceOpenApi.txt")
    output_path.write_text(text, encoding="utf-8")
    
    print(f"Text extracted to {output_path}")
    print(f"\nFirst 2000 characters:\n{text[:2000]}")

