import fitz
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract, io
from PIL import Image, ImageFilter, ImageEnhance


def extract_pdf_chunks(path, words_per_chunk=250):
    chunks = []
    try:
        doc = fitz.open(str(path))
        all_words = []
        for page in doc:
            # try native text first
            text = page.get_text().strip()
            if len(text) > 50:
                all_words.extend(text.split())
            else:
                # fallback to OCR with preprocessing
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                # preprocess: grayscale, sharpen, contrast
                img = img.convert("L")
                img = ImageEnhance.Contrast(img).enhance(2.0)
                img = img.filter(ImageFilter.SHARPEN)
                text = pytesseract.image_to_string(img, config="--psm 6")
                all_words.extend(text.split())
        for i in range(0, len(all_words), words_per_chunk):
            chunk = " ".join(all_words[i : i + words_per_chunk])
            if len(chunk.strip()) > 100:
                chunks.append(chunk)
    except Exception as e:
        print(f"[files] PDF error {path}: {e}")
    return chunks


def extract_epub_chunks(path, words_per_chunk=250):
    chunks = []
    try:
        book = epub.read_epub(str(path))
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.content, "html.parser")
            text = soup.get_text(" ", strip=True)
            words = text.split()
            for i in range(0, len(words), words_per_chunk):
                chunk = " ".join(words[i : i + words_per_chunk])
                if len(chunk.strip()) > 100:
                    chunks.append(chunk)
    except Exception as e:
        print(f"[files] EPUB error {path}: {e}")
    return chunks


def extract_chunks(path):
    path = str(path)
    if path.endswith(".pdf"):
        return extract_pdf_chunks(path)
    elif path.endswith(".epub"):
        return extract_epub_chunks(path)
    return []
