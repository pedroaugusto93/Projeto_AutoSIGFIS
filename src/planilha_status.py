# planilha_status.py
# -*- coding: utf-8 -*-
"""
Escreve o resultado de volta na planilha de entrada, nas colunas que VOCE ja
criou (nao cria coluna nenhuma):
  - coluna STATUS          -> texto amigavel (CADASTRADO COMPLETO, INCOMPLETO, ...)
  - coluna PERC_CONCLUSAO  -> percentual de conclusao do registro (ex.: "75%")

Comportamento:
  - localiza as colunas pelo NOME do cabecalho (posicao livre);
  - se alguma nao existir, apenas AVISA no log e nao grava aquela coluna
    (nao cria coluna nova);
  - preenche apenas o valor, sem alterar a formatacao da sua coluna;
  - escreve celula a celula com openpyxl (preserva o resto da planilha);
  - escreve uma unica vez, ao final da execucao;
  - se o arquivo estiver aberto/travado (Excel), salva numa COPIA
    'cadastro_STATUS_<timestamp>.xlsx' em vez de falhar.

Mapeamento linha de dados -> linha do Excel: registro i (1-based) ocupa a linha
header_row + i (com cabecalho na linha 1, o registro 1 fica na linha 2).
"""

from datetime import datetime
from pathlib import Path

import openpyxl

from logger import get_logger

log = get_logger("planilha")

# status interno -> texto que aparece na coluna STATUS
TEXTO_STATUS = {
    "OK":         "CADASTRADO COMPLETO",
    "ALERTA":     "CADASTRADO (CONFERIR DIVERGÊNCIA)",
    "INCOMPLETO": "CADASTRADO INCOMPLETO",
    "ERRO":       "NÃO CADASTRADO (ERRO)",
    "PULADO":     "JÁ CADASTRADO",
}


def _col_por_titulo(ws, titulo, header_row=1):
    alvo = str(titulo).strip().lower()
    for cell in ws[header_row]:
        if str(cell.value or "").strip().lower() == alvo:
            return cell.column  # 1-based
    return None


def escrever_status(excel_path, sheet, resultados, header_row=1):
    """
    resultados: lista de dicts com chaves 'registro' (int), 'status' (str),
                'perc' (int 0-100).
    """
    p = Path(excel_path)
    try:
        wb = openpyxl.load_workbook(p)
    except Exception as e:
        log.error("Nao consegui abrir a planilha para gravar STATUS: %s", e)
        return

    ws = wb[sheet] if sheet in wb.sheetnames else wb.active

    # Localiza as colunas existentes (NAO cria nenhuma)
    col_status = _col_por_titulo(ws, "STATUS", header_row)
    col_perc = _col_por_titulo(ws, "PERC_CONCLUSAO", header_row)

    if col_status is None:
        log.warning("Coluna 'STATUS' nao encontrada no cabecalho; status nao sera gravado.")
    if col_perc is None:
        log.warning("Coluna 'PERC_CONCLUSAO' nao encontrada no cabecalho; percentual nao sera gravado.")
    if col_status is None and col_perc is None:
        log.warning("Nenhuma coluna de resultado encontrada; nada a gravar na planilha.")
        return

    # Preenche apenas as colunas existentes
    for r in resultados:
        try:
            linha = header_row + int(r["registro"])
            if col_status is not None:
                ws.cell(row=linha, column=col_status,
                        value=TEXTO_STATUS.get(r.get("status"), r.get("status")))
            if col_perc is not None:
                # texto "NN%" -> exibe igual em qualquer formatacao da coluna
                ws.cell(row=linha, column=col_perc, value=f'{int(r.get("perc", 0))}%')
        except Exception as e:
            log.warning("Falha ao escrever resultado do registro %s: %s", r.get("registro"), e)

    # Salva (com fallback para copia se o arquivo estiver travado/aberto)
    try:
        wb.save(p)
        log.info("STATUS/percentual gravado na planilha: %s", p)
    except PermissionError:
        alt = p.with_name(f"{p.stem}_STATUS_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        try:
            wb.save(alt)
            log.warning("Planilha provavelmente aberta no Excel. Resultado salvo numa copia: %s", alt)
        except Exception as e:
            log.error("Falha ao salvar a copia: %s", e)
    except Exception as e:
        log.error("Falha ao salvar na planilha: %s", e)
