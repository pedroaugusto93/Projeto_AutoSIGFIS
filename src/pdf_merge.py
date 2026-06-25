# pdf_merge.py
# -*- coding: utf-8 -*-
"""
Utilitario generico para juntar varios PDFs num unico arquivo.
Nao tem nada de SIGFIS: serve para qualquer fluxo (recibos, documentos, etc.).
"""

import os
from pypdf import PdfReader, PdfWriter
from logger import get_logger

log = get_logger("pdf_merge")


def juntar_pdfs(caminhos, destino, ordenar=True):
    """
    Junta os PDFs de `caminhos` (lista) num unico arquivo em `destino`.
    - ignora caminhos vazios/inexistentes;
    - se `ordenar`, ordena por nome do arquivo (alfabetico) antes de juntar;
    - retorna o caminho gerado ou "" se nada foi gerado.
    """
    validos = [c for c in caminhos if c and os.path.isfile(c)]
    if not validos:
        log.warning("Nenhum PDF valido para juntar.")
        return ""
    if ordenar:
        validos = sorted(validos, key=lambda p: os.path.basename(p).lower())

    writer = PdfWriter()
    juntados = 0
    for c in validos:
        try:
            reader = PdfReader(c)
            for page in reader.pages:
                writer.add_page(page)
            juntados += 1
        except Exception as e:
            log.error("Falha ao ler PDF (%s): %s; pulando.", c, e)

    if juntados == 0:
        log.error("Nenhum PDF pode ser lido; nada gerado.")
        return ""

    pasta = os.path.dirname(destino)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(destino, "wb") as f:
        writer.write(f)
    log.info("PDF unico gerado (%d de %d arquivos): %s", juntados, len(validos), destino)
    return destino


def juntar_pasta(pasta, destino, prefixo="", ordenar=True):
    """Junta todos os .pdf de uma pasta (opcionalmente filtrando por prefixo de nome)."""
    if not os.path.isdir(pasta):
        log.error("Pasta nao encontrada: %s", pasta)
        return ""
    pref = (prefixo or "").lower()
    arquivos = [
        os.path.join(pasta, f) for f in os.listdir(pasta)
        if f.lower().endswith(".pdf") and f.lower().startswith(pref)
        and os.path.join(pasta, f) != destino  # nao inclui o proprio destino
    ]
    return juntar_pdfs(arquivos, destino, ordenar=ordenar)
