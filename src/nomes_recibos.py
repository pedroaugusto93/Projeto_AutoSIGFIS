# -*- coding: utf-8 -*-
"""Nomes padronizados de recibos TCE e protecao contra sobrescrita."""

import os
import re


def _componente(valor):
    texto = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "-", str(valor or "").strip())
    texto = re.sub(r"\s+", " ", texto).strip(" .-")
    return texto


def nome_recibo_tce(processo, fornecedor):
    """TCE - PROCESSO - FORNECEDOR.pdf. Dados ausentes nao sao inventados."""
    proc = _componente(processo)
    forn = _componente(fornecedor)
    if not proc or not forn:
        raise ValueError("Processo ou nome do fornecedor ausente; recibo sem nome confiavel.")
    base = f"TCE - {proc} - {forn}"[:180].rstrip(" .")
    return f"{base}.pdf"


def caminho_disponivel(pasta, nome_arquivo):
    """Preserva recibos existentes ao adicionar um sufixo numerico."""
    raiz, ext = os.path.splitext(nome_arquivo)
    destino = os.path.join(pasta, nome_arquivo)
    numero = 2
    while os.path.exists(destino):
        destino = os.path.join(pasta, f"{raiz} ({numero}){ext}")
        numero += 1
    return destino
