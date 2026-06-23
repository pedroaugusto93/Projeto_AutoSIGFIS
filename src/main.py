# main.py
# -*- coding: utf-8 -*-

# Dica: se quiser abrir o Chrome em modo debug, rode manualmente no PowerShell:
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"

import sys
import time
import traceback

import config
from helpers import wait_for_page_complete
from logger import setup_logging, get_logger, dump_failure, ExecutionReport, LOG_FILE
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from page_dados_basicos import preencher_dados_basicos
from page_itens import preencher_itens
from page_documentos import preencher_documentos
from page_empenhos import preencher_empenhos

log = get_logger("main")


def selecionar_aba(driver, wait, titulo: str):
    """
    Clica na aba cujo <fa-icon> tem atributo title igual a `titulo`.
    Para 'Enviar', tenta achar a aba; se não existir, apenas registra e segue.
    """
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


def main():
    setup_logging()
    log.info("=" * 60)
    log.info("AutoSIGFIS iniciado (modo: preenchimento; NAO envia ao TCE)")
    log.info("=" * 60)

    report = ExecutionReport()

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
            log.info("--- Registro %d/%d | PROCESSO: %s | Fornecedor: %s ---",
                     idx, len(cfgs), proc, forn)

            ultima_aba = "-"
            status = "OK"
            etapa_falha = ""
            erro_tipo = ""
            erro_msg = ""

            try:
                driver.get(config.URL_DISPENSA)
                wait_for_page_complete(driver, wait)

                # === Aba 1: Dados Básicos ===
                ultima_aba = "1 - Dados Basicos"
                selecionar_aba(driver, wait, "1 - Dados Básicos")
                preencher_dados_basicos(driver, wait, cfg)
                try:
                    valor_p1 = driver.find_element(By.NAME, 'Valor').get_attribute('value')
                except Exception:
                    valor_p1 = cfg.get('VALOR', '')
                log.debug("Valor (pagina 1): %s", valor_p1)

                # === Aba 2: Itens ===
                ultima_aba = "2 - Itens"
                selecionar_aba(driver, wait, "Itens")
                preencher_itens(driver, wait, cfg)

                # === Aba 3: Documentos ===
                ultima_aba = "3 - Documentos"
                selecionar_aba(driver, wait, "3 - Documentos")
                preencher_documentos(driver, wait, cfg)

                # === Aba 4: Empenhos ===
                ultima_aba = "4 - Empenhos"
                selecionar_aba(driver, wait, "4 - Empenhos")
                preencher_empenhos(driver, wait, cfg, valor_p1)

                # === Envio ao TCE: desativado de propósito (dry-run) ===
                # Para habilitar, implemente aqui o clique em 'Enviar ao TCE'.

                log.info("[OK] Registro %d concluido: %s", idx, proc)

            except Exception as e:
                status = "ERRO"
                etapa_falha = ultima_aba
                erro_tipo = type(e).__name__
                erro_msg = (str(e).strip() or repr(e))
                # Loga tipo + mensagem (resolve o 'Message:' vazio do Selenium)
                log.error("[ERRO] Registro %d falhou na aba '%s' -> %s: %s",
                          idx, ultima_aba, erro_tipo, erro_msg)
                log.debug("Traceback:\n%s", traceback.format_exc())
                dump_failure(driver, prefixo=f"falha_reg{idx}")

            finally:
                report.add(
                    registro=idx,
                    processo=proc,
                    nome_fornecedor=forn,
                    cnpj_fornecedor=cfg.get('CNPJ_FORNECEDOR'),
                    valor=cfg.get('VALOR'),
                    num_empenho=cfg.get('NUM_EMPENHO'),
                    status=status,
                    ultima_aba=ultima_aba,
                    etapa_falha=etapa_falha,
                    erro_tipo=erro_tipo,
                    erro_msg=erro_msg,
                    duracao_s=round(time.time() - t0, 1),
                    inicio=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0)),
                )

    finally:
        log.info("Fechando driver...")
        try:
            driver.quit()
        except Exception:
            pass

        ok, erros, total = report.resumo()
        extrato_path = report.save()
        log.info("=" * 60)
        log.info("RESUMO: %d OK | %d ERRO | %d total", ok, erros, total)
        log.info("Extrato: %s", extrato_path)
        log.info("Log:     %s", LOG_FILE)
        log.info("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        get_logger("main").warning("Interrompido pelo usuario.")
        sys.exit(1)
