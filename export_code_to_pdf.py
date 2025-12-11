#!/usr/bin/env python3
from pathlib import Path
from fpdf import FPDF

# Folders to include
INCLUDE_DIRS = [
    "config",
    "scripts",
    "src/audio",
    "src/expression",
    "src/display",
    "src/llm",
    "src/memory",
    "src/personality",
    "tests",
]

# File extensions to include (add more if needed)
ALLOWED_EXTS = {".py", ".sh", ".yaml", ".yml", ".txt", ".md", ".json", ".ini", ".cfg"}

# Filenames to skip
SKIP_NAMES = {".DS_Store", "__pycache__", ".gitignore"}

def to_latin1(text: str) -> str:
    """Best-effort conversion so core fonts can render the text."""
    return text.encode("latin-1", "replace").decode("latin-1")

def iter_files():
    for rel_dir in INCLUDE_DIRS:
        base = Path(rel_dir)
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir():
                continue
            if path.name in SKIP_NAMES or path.suffix not in ALLOWED_EXTS:
                continue
            yield path

def add_file(pdf: FPDF, path: Path):
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin  # must be computed after add_page()
    pdf.set_font("Courier", size=8)
    pdf.multi_cell(page_width, 6, to_latin1(f"### {path}"), align="L")
    pdf.ln(1)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="replace")
    for line in text.splitlines():
        # Hard-wrap very long lines so they fit the page width
        clipped = to_latin1(line[:500])
        for i in range(0, len(clipped), 100):
            pdf.multi_cell(page_width, 4, clipped[i : i + 100], align="L")
    pdf.ln(2)

def main():
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=12)
    for file_path in iter_files():
        add_file(pdf, file_path)
    pdf.output("code_export.pdf")

if __name__ == "__main__":
    main()