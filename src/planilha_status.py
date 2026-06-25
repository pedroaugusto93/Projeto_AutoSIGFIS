# planilha_status.py
# -*- coding: utf-8 -*-
"""
Escreve o resultado de volta na planilha de entrada, nas colunas que VOCE ja
criou (nao cria coluna nenhuma):
  - coluna STATUS          -> texto amigavel (CADASTRADO COMPLETO, INCOMPLETO, ...)
  - coluna PERC_CONCLUSAO  -> percentual de conclusao do registro (ex.: "75%")

Robustez contra arquivo travado (aberto no Excel / lock do OneDrive):
  - tenta ABRIR algumas vezes (retentativas com espera) antes de desistir;
  - tenta SALVAR algumas vezes; se nao der, salva numa COPIA
    'cadastro_STATUS_<timestamp>.xlsx' (nada se perde);
  - mensagens claras pedindo para fechar o Excel.

Demais regras:
  - localiza as colunas pelo NOME do cabecalho (posicao livre);
  - se alguma nao existir, apenas AVISA e nao cria;
  - preenche so o valor, sem mexer na formatacao da coluna;
  - escreve uma unica vez, ao final da execucao.

Mapeamento: registro i (1-based) -> linha header_row + i (cabecalho na linha 1).
"""

import time
from datetime import datetime
from pathlib import Path

import openpyxl

from logger import get_logger

log = get_logger("planilha")

TEXTO_STATUS = {
    "OK":            "CADASTRADO COMPLETO",
    "ENVIADO":       "ENVIADO AO TCE",
    "ENVIO_PENDENTE":"COMPLETO - ENVIAR AO TCE MANUALMENTE",
    "SEM_DOC":       "CADASTRADO SEM DOCUMENTO",
    "ALERTA":        "CADASTRADO (CONFERIR DIVERGÊNCIA)",
    "INCOMPLETO":    "CADASTRADO INCOMPLETO",
    "INTERROMPIDO":  "INTERROMPIDO (NÃO CADASTRADO)",
    "ERRO":          "NÃO CADASTRADO (ERRO)",
    "PULADO":        "JÁ CADASTRADO",
}


def _col_por_titulo(ws, titulo, header_row=1):
    alvo = str(titulo).strip().lower()
    for cell in ws[header_row]:
        if str(cell.value or "").strip().lower() == alvo:
            return cell.column  # 1-based
    return None


def _col_por_titulo_ou_cria(ws, titulo, header_row=1):
    """Como _col_por_titulo, mas cria a coluna no fim do cabecalho se nao existir."""
    col = _col_por_titulo(ws, titulo, header_row)
    if col:
        return col
    nova = (ws.max_column or 0) + 1
    ws.cell(row=header_row, column=nova, value=titulo)
    return nova


def _abrir_com_retentativa(p, tentativas, espera):
    """Tenta abrir a planilha; retorna o workbook ou None se nao conseguir."""
    for n in range(1, tentativas + 1):
        try:
            return openpyxl.load_workbook(p)
        except PermissionError:
            if n < tentativas:
                log.warning("Planilha em uso (abrir %d/%d). FECHE o Excel; tentando de novo em %.1fs...",
                            n, tentativas, espera)
                time.sleep(espera)
            else:
                log.error("Planilha continua aberta/bloqueada; nao foi possivel abrir para gravar.")
        except Exception as e:
            log.error("Nao consegui abrir a planilha: %s", e)
            return None
    return None


def _salvar_com_retentativa(wb, p, tentativas, espera):
    """Salva no original; se travado, salva numa copia. Retorna o caminho salvo ou None."""
    for n in range(1, tentativas + 1):
        try:
            wb.save(p)
            return p
        except PermissionError:
            if n < tentativas:
                log.warning("Nao consegui salvar (arquivo em uso %d/%d). FECHE o Excel; tentando em %.1fs...",
                            n, tentativas, espera)
                time.sleep(espera)
            else:
                alt = p.with_name(f"{p.stem}_STATUS_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
                try:
                    wb.save(alt)
                    log.warning("Original bloqueado. Resultado salvo numa COPIA: %s", alt)
                    return alt
                except Exception as e:
                    log.error("Falha ao salvar a copia: %s", e)
                    return None
        except Exception as e:
            log.error("Falha ao salvar na planilha: %s", e)
            return None
    return None


def escrever_status(excel_path, sheet, resultados, header_row=1, tentativas=3, espera=2.0):
    """
    resultados: lista de dicts com 'registro' (int), 'status' (str), 'perc' (int).
    """
    p = Path(excel_path)

    wb = _abrir_com_retentativa(p, tentativas, espera)
    if wb is None:
        log.error("STATUS NAO gravado na planilha. Feche o Excel e rode de novo: como tudo que "
                  "ja foi feito vira PULADO, ele reescreve o STATUS em segundos. O status por "
                  "registro tambem esta no extrato_*.xlsx.")
        return

    ws = wb[sheet] if sheet in wb.sheetnames else wb.active

    col_status = _col_por_titulo(ws, "STATUS", header_row)
    col_perc = _col_por_titulo(ws, "PERC_CONCLUSAO", header_row)
    col_disp = _col_por_titulo_ou_cria(ws, "DISPENSA_SIGFIS", header_row)
    if col_status is None:
        log.warning("Coluna 'STATUS' nao encontrada no cabecalho; status nao sera gravado.")
    if col_perc is None:
        log.warning("Coluna 'PERC_CONCLUSAO' nao encontrada no cabecalho; percentual nao sera gravado.")
    if col_status is None and col_perc is None and col_disp is None:
        log.warning("Nenhuma coluna de resultado encontrada; nada a gravar na planilha.")
        return

    for r in resultados:
        try:
            linha = header_row + int(r["registro"])
            if col_status is not None:
                ws.cell(row=linha, column=col_status,
                        value=TEXTO_STATUS.get(r.get("status"), r.get("status")))
            if col_perc is not None:
                ws.cell(row=linha, column=col_perc, value=f'{int(r.get("perc", 0))}%')
            if col_disp is not None and str(r.get("dispensa") or "").strip():
                ws.cell(row=linha, column=col_disp, value=str(r.get("dispensa")).strip())
        except Exception as e:
            log.warning("Falha ao escrever resultado do registro %s: %s", r.get("registro"), e)

    destino = _salvar_com_retentativa(wb, p, tentativas, espera)
    if destino is not None and destino == p:
        log.info("STATUS/percentual gravado na planilha: %s", p)
