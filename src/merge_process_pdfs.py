# merge_process_pdfs.py
# -*- coding: utf-8 -*-
"""
Une PDFs de um mesmo processo (arquivos com sufixo -1, -2, -3...) em um único PDF.
Compatível com pypdf >= 6 (sem PdfMerger) e também com versões antigas (com PdfMerger).

Requisitos:
  pip install pypdf
"""

import os
import re
from pathlib import Path
import pypdf

# <<< AJUSTE AQUI SE PRECISAR >>>
# BASE_DIR = r"C:\Users\pedro\Downloads\Teste"
# BASE_DIR = str((Path(__file__).resolve().parent / "Teste").resolve())
BASE_DIR = str((Path(__file__).resolve().parent.parent / "Teste").resolve())  # se “Teste” ficar fora de src
OUT_DIR  = Path(BASE_DIR) / "Unificados"


# Regex: captura base + sufixo -N no FINAL do nome
# Ex.: "20.22....-51-3.pdf" => base="20.22....-51", seq="3"
PATTERN = re.compile(r"^(?P<base>.+?)(?:-(?P<seq>\d+))?\.pdf$", re.IGNORECASE)

def collect_groups(folder: Path):
    groups = {}
    for p in folder.glob("*.pdf"):
        # pula PDFs já unificados
        if p.parent.name.lower() == "unificados":
            continue
        m = PATTERN.match(p.name)
        if not m:
            continue
        base = m.group("base")
        seq  = m.group("seq")
        seq_num = int(seq) if seq is not None and seq.isdigit() else 0  # sem sufixo vira 0
        groups.setdefault(base, []).append((seq_num, p))

    # ordena cada grupo pelo sufixo numérico
    for base in groups:
        groups[base].sort(key=lambda t: t[0])
    return groups

def merge_with_writer(files, out_pdf: Path):
    """Compatível com pypdf >= 6: usa PdfWriter para juntar páginas."""
    writer = pypdf.PdfWriter()
    any_pages = False
    for seq, pdf_path in files:
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            for page in reader.pages:
                writer.add_page(page)
                any_pages = True
        except Exception as e:
            print(f"[WARN] Falha ao anexar '{pdf_path.name}': {e}")
    if not any_pages:
        print(f"[SKIP] Grupo sem páginas válidas para '{out_pdf.name}'.")
        return
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as f:
        writer.write(f)
    print(f"[OK] Gerado: {out_pdf}")

def merge_with_merger(files, out_pdf: Path):
    """Para versões antigas (se existir pypdf.PdfMerger)."""
    merger = pypdf.PdfMerger(strict=False)
    try:
        for seq, pdf_path in files:
            try:
                merger.append(str(pdf_path))
            except Exception as e:
                print(f"[WARN] Falha ao anexar '{pdf_path.name}': {e}")
        if len(merger.pages) == 0:
            print(f"[SKIP] Grupo sem páginas válidas para '{out_pdf.name}'.")
            return
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        merger.write(str(out_pdf))
        print(f"[OK] Gerado: {out_pdf}")
    finally:
        try:
            merger.close()
        except Exception:
            pass

def merge_group(files, out_pdf: Path):
    # Usa PdfMerger se existir, senão PdfWriter
    if hasattr(pypdf, "PdfMerger"):
        merge_with_merger(files, out_pdf)
    else:
        merge_with_writer(files, out_pdf)

def main():
    base = Path(BASE_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {BASE_DIR}")

    groups = collect_groups(base)
    if not groups:
        print("[INFO] Nenhum PDF encontrado.")
        return

    total = 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for base_name, files in groups.items():
        out_pdf = OUT_DIR / f"{base_name}.pdf"
        merge_group(files, out_pdf)
        total += 1

    print(f"\n[FINALIZADO] Grupos processados: {total}. Saída: {OUT_DIR}")

if __name__ == "__main__":
    main()
