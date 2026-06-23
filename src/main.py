# main.py
# -*- coding: utf-8 -*-

# Dica: abrir o Chrome em modo debug (PowerShell):
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
#
# Reprocessar tudo do zero (ignorar o estado; pode duplicar): set SIGFIS_FORCE=1

import os
import sys
import time
import traceback

import config
import verify
import planilha_status
from helpers import wait_for_page_complete
from logger import setup_logging, get_logger, dump_failure, ExecutionReport, LOG_FILE
from state import EstadoProcessados
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from page_dados_basicos import preencher_dados_basicos
from page_itens import preencher_itens
from page_documentos import preencher_documentos
from page_empenhos import preencher_empenhos

log = get_logger("main")

# Etapas que compoem 100% de um registro
TOTAL_ETAPAS = 4  # 1 Dados Basicos, 2 Itens, 3 Documentos, 4 Empenhos


def selecionar_aba(driver, wait, titulo: str):
    if "Enviar" in titulo:
        try:
            aba = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//ul[contains(@class,'nav-tabs')]//a[.//fa-icon[@title='5 - Enviar'] or contains(normalize-space(.),'Enviar')]"
            )))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", aba)
            driver.execute_script("arguments[0].click();", aba)
            wait_for_page_complete(driver, wait)
            log.info("Aba 'Enviar' acessada")
        except Exception:
            log.info("Aba 'Enviar' nao existe nesta tela; seguindo direto para o botao.")
        return

    aba = wait.until(EC.element_to_be_clickable((By.XPATH,
        f"//ul[contains(@class,'nav-tabs')]//fa-icon[@title='{titulo}']/ancestor::a"
    )))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", aba)
    driver.execute_script("arguments[0].click();", aba)
    wait_for_page_complete(driver, wait)
    log.info("Aba '%s' acessada", titulo)


def _chk(fn, driver, cfg, nome):
    """Executa uma conferencia de read-back de forma segura e loga o resultado."""
    try:
        ok, msg = fn(driver, cfg)
    except Exception as e:
        ok, msg = False, f"{nome}: erro na verificacao ({e})"
    (log.info if ok else log.warning)("Conferencia -> %s", msg)
    return ok, msg


def main():
    setup_logging()
    force = str(os.environ.get("SIGFIS_FORCE", "")).strip().lower() in ("1", "true", "sim", "s", "yes")

    log.info("=" * 60)
    log.info("AutoSIGFIS iniciado (preenchimento; NAO envia ao TCE) | FORCE=%s", force)
    log.info("=" * 60)

    report = ExecutionReport()
    estado = EstadoProcessados(force=force)

    cfgs = config.load_all_cfgs()
    if not cfgs:
        log.error("Nenhuma config encontrada em: %s", config.EXCEL_PATH)
        return

    driver, wait = config.create_driver_and_wait()

    try:
        for idx, cfg in enumerate(cfgs, start=1):
            t0 = time.time()
            proc = cfg.get('PROCESSO')
            forn = cfg.get('NOME_FORNECEDOR')
            inicio = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0))

            # --- Anti-duplicidade / retomada ---
            if estado.ja_feito(cfg):
                rec = estado.info(cfg) or {}
                did = rec.get("dispensa_id", "")
                log.info("--- Registro %d/%d PULADO (dispensa ja criada: %s) | %s ---",
                         idx, len(cfgs), did or "?", proc)
                report.add(registro=idx, processo=proc, nome_fornecedor=forn,
                           cnpj_fornecedor=cfg.get('CNPJ_FORNECEDOR'), valor=cfg.get('VALOR'),
                           num_empenho=cfg.get('NUM_EMPENHO'), dispensa_id=did,
                           status="PULADO", perc_conclusao=100, validacoes="ja existente no estado",
                           ultima_aba="-", etapa_falha="", erro_tipo="", erro_msg="",
                           duracao_s=0.0, inicio=inicio)
                continue

            log.info("--- Registro %d/%d | PROCESSO: %s | Fornecedor: %s ---",
                     idx, len(cfgs), proc, forn)

            ultima_aba = "-"
            status = "OK"
            etapa_falha = ""
            erro_tipo = ""
            erro_msg = ""
            dispensa_id = ""
            etapas = 0          # quantas etapas (de TOTAL_ETAPAS) foram concluidas
            checagens = []

            try:
                driver.get(config.URL_DISPENSA)
                wait_for_page_complete(driver, wait)

                # === Aba 1: Dados Básicos ===
                ultima_aba = "1 - Dados Basicos"
                selecionar_aba(driver, wait, "1 - Dados Básicos")
                dispensa_id = preencher_dados_basicos(driver, wait, cfg) or ""
                etapas = 1
                if not dispensa_id:
                    log.warning("Nao consegui ler o Nº da Dispensa apos salvar (read-back vazio).")
                try:
                    valor_p1 = driver.find_element(By.NAME, 'Valor').get_attribute('value')
                except Exception:
                    valor_p1 = cfg.get('VALOR', '')

                # === Aba 2: Itens ===
                ultima_aba = "2 - Itens"
                selecionar_aba(driver, wait, "Itens")
                preencher_itens(driver, wait, cfg)
                etapas = 2
                checagens.append(_chk(verify.verificar_item, driver, cfg, "Item"))

                # === Aba 3: Documentos ===
                ultima_aba = "3 - Documentos"
                selecionar_aba(driver, wait, "3 - Documentos")
                preencher_documentos(driver, wait, cfg)
                etapas = 3
                checagens.append(_chk(verify.verificar_documento, driver, cfg, "Documento"))

                # === Aba 4: Empenhos ===
                ultima_aba = "4 - Empenhos"
                selecionar_aba(driver, wait, "4 - Empenhos")
                preencher_empenhos(driver, wait, cfg, valor_p1)
                etapas = 4
                checagens.append(_chk(verify.verificar_empenho, driver, cfg, "Empenho"))

                # === Envio ao TCE: desativado de proposito (dry-run) ===

                todas_ok = all(ok for ok, _ in checagens)
                status = "OK" if todas_ok else "ALERTA"
                if status == "OK":
                    log.info("[OK] Registro %d concluido e conferido: %s (dispensa %s)",
                             idx, proc, dispensa_id or "?")
                else:
                    log.warning("[ALERTA] Registro %d criado, mas a conferencia apontou divergencia: %s",
                                idx, proc)

            except Exception as e:
                erro_tipo = type(e).__name__
                erro_msg = (str(e).strip() or repr(e))
                etapa_falha = ultima_aba
                # Se ja existe dispensa_id, a dispensa FOI criada -> nao re-tentar (evita duplicar)
                status = "INCOMPLETO" if dispensa_id else "ERRO"
                log.error("[%s] Registro %d falhou na aba '%s' -> %s: %s",
                          status, idx, ultima_aba, erro_tipo, erro_msg)
                log.debug("Traceback:\n%s", traceback.format_exc())
                dump_failure(driver, prefixo=f"falha_reg{idx}")

            finally:
                perc = round(etapas / TOTAL_ETAPAS * 100)
                validacoes = " | ".join(msg for _, msg in checagens) if checagens else ""
                estado.marcar(cfg, status, dispensa_id, validacoes)
                report.add(registro=idx, processo=proc, nome_fornecedor=forn,
                           cnpj_fornecedor=cfg.get('CNPJ_FORNECEDOR'), valor=cfg.get('VALOR'),
                           num_empenho=cfg.get('NUM_EMPENHO'), dispensa_id=dispensa_id,
                           status=status, perc_conclusao=perc, validacoes=validacoes,
                           ultima_aba=ultima_aba, etapa_falha=etapa_falha, erro_tipo=erro_tipo,
                           erro_msg=erro_msg, duracao_s=round(time.time() - t0, 1), inicio=inicio)

    finally:
        log.info("Fechando driver...")
        try:
            driver.quit()
        except Exception:
            pass

        # Resumo + percentual geral de conclusao do lote
        ok, nao_ok, total = report.resumo()
        completos = sum(1 for r in report.rows if r.get("perc_conclusao") == 100)
        perc_lote = round(completos / total * 100) if total else 0

        # Escreve STATUS + PERC_CONCLUSAO de volta na planilha
        resultados = [{"registro": r["registro"], "status": r["status"],
                       "perc": r.get("perc_conclusao", 0)} for r in report.rows]
        planilha_status.escrever_status(config.EXCEL_PATH, config.SHEET_NAME, resultados)

        extrato_path = report.save()
        log.info("=" * 60)
        log.info("RESUMO: %d OK | %d nao-OK | %d total", ok, nao_ok, total)
        log.info("CONCLUSAO DO LOTE: %d%% (%d de %d registros 100%% concluidos)",
                 perc_lote, completos, total)
        log.info("Extrato: %s", extrato_path)
        log.info("Estado:  logs/estado_processados.json")
        log.info("Log:     %s", LOG_FILE)
        log.info("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        get_logger("main").warning("Interrompido pelo usuario.")
        sys.exit(1)
