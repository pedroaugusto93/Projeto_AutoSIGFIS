# -*- coding: utf-8 -*-
"""Solicitacao e validacao dos caminhos informados na inicializacao."""

import os
import tempfile


def _normalizar_entrada(texto):
    caminho = str(texto).strip()
    if len(caminho) >= 2 and caminho.startswith('"') and caminho.endswith('"'):
        caminho = caminho[1:-1].strip()
    return os.path.normpath(caminho) if caminho else ""


def _validar_planilha(caminho):
    if not os.path.isabs(caminho):
        return "Informe o caminho absoluto da planilha."
    if os.path.splitext(caminho)[1].lower() not in (".xlsx", ".xlsm", ".xls"):
        return "A planilha deve ser um arquivo Excel (.xlsx, .xlsm ou .xls)."
    if not os.path.isfile(caminho):
        return "A planilha nao foi encontrada neste caminho."
    try:
        with open(caminho, "rb") as arquivo:
            arquivo.read(1)
    except OSError as erro:
        return f"Nao foi possivel ler a planilha: {erro}"
    return ""


def _validar_pasta(caminho):
    if not os.path.isabs(caminho):
        return "Informe o caminho absoluto da pasta de recibos."
    if not os.path.isdir(caminho):
        return "A pasta de recibos nao existe. Informe uma pasta existente."
    try:
        with tempfile.TemporaryFile(dir=caminho):
            pass
    except OSError as erro:
        return f"Sem permissao para gravar na pasta de recibos: {erro}"
    return ""


def _solicitar(prompt, validar):
    while True:
        try:
            caminho = _normalizar_entrada(input(prompt))
        except EOFError as erro:
            raise RuntimeError(
                "A execucao requer um terminal interativo para informar os caminhos."
            ) from erro
        mensagem = validar(caminho)
        if not mensagem:
            return caminho
        print(f"[CAMINHO INVALIDO] {mensagem}\n")


def solicitar_caminhos():
    """Solicita primeiro a planilha; so entao pede a pasta dos recibos."""
    planilha = _solicitar(
        "Informe o caminho completo da planilha de cadastro: ",
        _validar_planilha,
    )
    recibos = _solicitar(
        "Informe o caminho da pasta onde os recibos serao salvos: ",
        _validar_pasta,
    )
    return planilha, recibos
