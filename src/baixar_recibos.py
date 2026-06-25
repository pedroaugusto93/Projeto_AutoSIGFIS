# baixar_recibos.py
# -*- coding: utf-8 -*-
"""
Fluxo SEPARADO do cadastro: pesquisa processos no SIGFIS, baixa o recibo de
cada dispensa enviada e junta tudo num PDF unico.

Operacao SOMENTE LEITURA: nao altera nada no SIGFIS (pode rodar a vontade).

Pre-requisito: Chrome aberto em modo debug (porta 9222), logado no SIGFIS -
igual ao main.py.

Uso:
  python src/baixar_recibos.py
  (digite os processos, um por linha; linha vazia encerra a lista)
"""

import os
import re
import sys
from datetime import datetime

import config
from logger import setup_logging, get_logger
import page_pesquisa
import pdf_merge

log = get_logger("baixar")


def _slug(texto):
    """Transforma o numero do processo num nome de arquivo seguro."""
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "-", str(texto).strip())
    s = re.sub(r"\s+", "_", s)
    return s[:120] or "processo"


def _ler_processos_terminal():
    print("\nDigite os numeros de processo a pesquisar (um por linha).")
    print("Deixe uma linha em branco e tecle Enter para comecar.\n")
    processos = []
    while True:
        try:
            linha = input("Processo> ").strip()
        except EOFError:
            break
        if not linha:
            break
        processos.append(linha)
    # remove duplicados preservando a ordem
    vistos, unicos = set(), []
    for p in processos:
        if p not in vistos:
            vistos.add(p)
            unicos.append(p)
    return unicos


def main():
    setup_logging()
    log.info("=" * 60)
    log.info("AutoSIGFIS - Baixar recibos (consulta/somente leitura)")
    log.info("=" * 60)

    processos = _ler_processos_terminal()
    if not processos:
        log.warning("Nenhum processo informado. Encerrando.")
        return

    log.info("Processos a pesquisar: %s", ", ".join(processos))

    try:
        driver, wait = config.create_driver_and_wait()
    except Exception as e:
        log.error("Nao foi possivel iniciar o navegador; nada foi feito. (%s)", e)
        return

    dest_dir = config.RECIBOS_LOTE_DIR
    os.makedirs(dest_dir, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")

    gerados = []
    total_recibos = 0
    try:
        for proc in processos:
            log.info("--- Processo %s ---", proc)
            try:
                pdfs = page_pesquisa.baixar_recibos_do_processo(driver, wait, proc)
            except Exception as e:
                log.error("Falha ao processar o processo %s: %s", proc, e)
                continue
            if not pdfs:
                log.warning("Processo %s: nenhum recibo baixado.", proc)
                continue
            # um PDF unico POR PROCESSO
            nome = f"recibos_{_slug(proc)}_{carimbo}.pdf"
            destino = os.path.join(dest_dir, nome)
            final = pdf_merge.juntar_pdfs(pdfs, destino)
            if final:
                gerados.append((proc, final, len(pdfs)))
                total_recibos += len(pdfs)
                log.info("Processo %s: %d recibo(s) -> %s", proc, len(pdfs), final)
    finally:
        log.info("Fechando driver...")
        try:
            driver.quit()
        except Exception:
            pass

    log.info("=" * 60)
    if not gerados:
        log.warning("Nenhum recibo baixado em nenhum processo.")
        return
    log.info("CONCLUIDO: %d processo(s), %d recibo(s) no total.", len(gerados), total_recibos)
    for proc, caminho, n in gerados:
        log.info("  %s: %d recibo(s) -> %s", proc, n, caminho)
    log.info("Recibos individuais em: %s", os.path.join(dest_dir, "individuais"))
    log.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        get_logger("baixar").warning("Interrompido pelo usuario.")
        sys.exit(1)
