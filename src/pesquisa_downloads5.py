# pesquisa_downloads.py
# -*- coding: utf-8 -*-
"""
Integração completa + robustez contra StaleElement + pular linhas sem recibo (só com lupa):
- Lê processos da planilha (Sheet2, coluna 'Processos' ou 'Processo');
- Conecta ao MESMO Chrome aberto (remote debugging 9222);
- Para CADA processo: preenche o campo "Número do Processo" > Pesquisar;
- Em todas as páginas do grid, para cada linha:
    * se houver recibo (ícone 📋), abre o modal;
    * clona o HTML do modal numa aba temporária e imprime com Page.printToPDF;
    * salva como C:\\Users\\pedro\\Downloads\\Teste\\<número do processo>-<n>.pdf;
    * fecha o modal;
  Caso a linha tenha apenas a lupa (sem 📋), o script LOGA "[SKIP] ... sem recibo" e segue.
- Avança páginas; ao terminar o processo atual, clica "Limpar" e passa para o próximo.
"""

import os
import time
import base64
import unicodedata
from pathlib import Path
from typing import Dict

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException


# ===== Config =====
BASE_DIR   = Path(__file__).resolve().parent
# EXCEL_PATH = r"C:\Users\pedro\Projeto_AutoSIGIFIS\Projeto_AutoSIGFIS\src\cadastro.xlsx"
# EXCEL_PATH = str((Path(__file__).resolve().parent / "src" / "cadastro.xlsx").resolve())
EXCEL_PATH = str((BASE_DIR / "cadastro.xlsx").resolve())
# SAVE_DIR = r"C:\Users\pedro\Downloads\Teste"
SAVE_DIR   = r"C:\Users\pedro\Downloads\Teste"
SHEET_NAME = "Sheet2"

SIGFIS_CONSULTA_URL = "https://www.tcerj.tc.br/sigfis-atosjuridicos/site/admin/dispensas-inexigibilidades/dispensas/consulta"

# Campo de pesquisa e botões
INPUT_NUMERO_PROCESSO = 'input-text[name="NumeroProcesso"] input'
BTN_PESQUISAR         = 'div.col-md-12 > button.btn.btn-outline-primary'
BTN_LIMPAR            = 'div.col-md-12 > button.btn.btn-outline-secondary.ml-1'

# Tabela e paginação
DATAGRID_ROWS    = "#datagrid-0 tbody tr"
PAGINATION_NEXT  = "pagination ul.pagination li.pagination-next.page-item:not(.disabled) a"
PAGINATION_FIRST = "pagination ul.pagination li.pagination-first.page-item:not(.disabled) a"

# Botões na célula de Ações
ACTION_CELL           = "td.action.text-center"
ICON_CLIPBOARD_SEL    = "i.fa.fa-clipboard"

# Modal
MODAL_DIALOG     = ".modal-dialog"
MODAL_CONTENT    = ".modal-dialog .modal-content"
MODAL_BODY       = ".modal-dialog .modal-content .modal-body"
BTN_CANCELAR     = ".modal-footer button.btn.btn-outline-secondary"

# ===== Helpers =====
def wait_for_page_complete(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(0.2)

def scroll_into_view(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

def safe_click(driver, el):
    try:
        scroll_into_view(driver, el)
        el.click()
    except (ElementClickInterceptedException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", el)

def fill_input(driver, wait, css_selector: str, value: str):
    el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    scroll_into_view(driver, el)
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.DELETE)
    if value:
        el.send_keys(value)
    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.CSS_SELECTOR, css_selector).get_attribute("value").strip() == value.strip()
    )

def _norm(s: str) -> str:
    s = str(s or "").strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().replace(" ", "").replace("_", "")
    return s

def carregar_processos(path: str, sheet_name: str) -> list:
    if not Path(path).exists():
        raise FileNotFoundError(f"Planilha não encontrada: {path}")
    df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, header=None).fillna("")
    alvo = None
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            if _norm(df.iat[r, c]) in ("processo", "processos"):
                alvo = (r, c); break
        if alvo: break
    if not alvo:
        preview = df.head(10).to_string(index=False, header=False)
        raise ValueError(f"Não achei a coluna 'Processos' na aba {sheet_name}. Prévia:\n{preview}")
    r0, c0 = alvo
    col_values = df.iloc[r0+1:, c0].astype(str).map(str.strip)
    processos = [v for v in col_values if v and v.lower() != "nan"]
    if not processos:
        raise ValueError("Coluna 'Processos' encontrada, porém sem valores abaixo.")
    return processos

# --------- NOVO: robusto contra Stale — lê processo por índice ---------
def obter_numero_processo_da_linha_idx(driver, row_idx: int) -> str:
    for _ in range(4):
        rows = driver.find_elements(By.CSS_SELECTOR, DATAGRID_ROWS)
        if row_idx >= len(rows):
            return ""
        try:
            row = rows[row_idx]
            tds = row.find_elements(By.CSS_SELECTOR, "td")
            if len(tds) < 3:
                return ""
            proc_td = tds[2]
            txt = proc_td.text.strip()
            if not txt:
                spans = proc_td.find_elements(By.CSS_SELECTOR, "span")
                if spans:
                    txt = spans[0].get_attribute("title").strip()
            return txt
        except StaleElementReferenceException:
            time.sleep(0.1)
    return ""

# --------- NOVO: checa se há botão de recibo por índice ---------
def tem_clipboard_na_linha_idx(driver, row_idx: int) -> bool:
    for _ in range(4):
        rows = driver.find_elements(By.CSS_SELECTOR, DATAGRID_ROWS)
        if row_idx >= len(rows):
            return False
        try:
            row_el = rows[row_idx]
            try:
                action_cell = row_el.find_element(By.CSS_SELECTOR, ACTION_CELL)
            except Exception:
                action_cell = row_el
            if action_cell.find_elements(By.CSS_SELECTOR, ICON_CLIPBOARD_SEL):
                return True
            return len(row_el.find_elements(By.CSS_SELECTOR, ICON_CLIPBOARD_SEL)) > 0
        except StaleElementReferenceException:
            time.sleep(0.1)
    return False

# --------- NOVO: clica no recibo por índice, com retry ---------
def clicar_clipboard_da_linha_idx(driver, wait, row_idx: int):
    for _ in range(4):
        rows = driver.find_elements(By.CSS_SELECTOR, DATAGRID_ROWS)
        if row_idx >= len(rows):
            return None
        try:
            row_el = rows[row_idx]
            try:
                action_cell = row_el.find_element(By.CSS_SELECTOR, ACTION_CELL)
            except Exception:
                action_cell = row_el

            icons = action_cell.find_elements(By.CSS_SELECTOR, ICON_CLIPBOARD_SEL)
            if not icons:
                icons = row_el.find_elements(By.CSS_SELECTOR, ICON_CLIPBOARD_SEL)
            if not icons:
                return None

            icon = icons[0]
            btn = icon.find_element(By.XPATH, "./ancestor::button")
            safe_click(driver, btn)

            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, MODAL_DIALOG)))
            try:
                target = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, MODAL_BODY)))
            except TimeoutException:
                target = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, MODAL_CONTENT)))
            time.sleep(0.2)
            return target
        except StaleElementReferenceException:
            time.sleep(0.1)
    return None

def fechar_modal(driver):
    try:
        cancelar = driver.find_element(By.CSS_SELECTOR, BTN_CANCELAR)
        safe_click(driver, cancelar)
        WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, MODAL_DIALOG)))
    except Exception:
        try:
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, MODAL_DIALOG)))
        except Exception:
            pass

def abrir_aba_temporaria_com_html(driver, inner_html: str) -> str:
    """Abre nova aba, injeta HTML simplificado e retorna o handle dessa aba."""
    current_handles = set(driver.window_handles)
    html = f"""
    <html><head>
    <meta charset='utf-8'>
    <style>
      html,body{{margin:0;padding:0}}
      body{{font-family:Arial,Helvetica,sans-serif;font-size:12px;padding:16px}}
      table{{width:100%;border-collapse:collapse}}
      th,td{{border:1px solid #000;padding:4px;vertical-align:top}}
      .text-center{{text-align:center}}
      .text-right{{text-align:right}}
      .text-left{{text-align:left}}
    </style>
    </head><body>{inner_html}</body></html>
    """
    driver.execute_script("window.open('about:blank','_blank');")
    time.sleep(0.1)
    new_handles = [h for h in driver.window_handles if h not in current_handles]
    if not new_handles:
        raise RuntimeError("Falha ao abrir aba temporária.")
    new_handle = new_handles[0]
    driver.switch_to.window(new_handle)
    driver.execute_script("document.open(); document.write(arguments[0]); document.close();", html)
    time.sleep(0.2)
    return new_handle

def print_tab_to_pdf(driver, path_pdf: str):
    res = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True,
        "landscape": False,
        "paperWidth": 8.27,
        "paperHeight": 11.69,
        "scale": 1.0,
        "preferCSSPageSize": True,
        "displayHeaderFooter": False
    })
    data = res.get("data", "")
    if not data:
        raise RuntimeError("Page.printToPDF não retornou dados.")
    pdf_bytes = base64.b64decode(data.encode("utf-8"))
    with open(path_pdf, "wb") as f:
        f.write(pdf_bytes)

def baixar_recibos_em_todas_paginas(driver, processo_atual: str, total_counter: dict):
    """Percorre todas as páginas do grid para o processo pesquisado atual."""
    wait = WebDriverWait(driver, 20, poll_frequency=0.2)

    # Sequenciais por processo (para o nome do arquivo)
    seq_por_processo: Dict[str, int] = {}

    # Volta para a primeira página (se existir)
    first = driver.find_elements(By.CSS_SELECTOR, PAGINATION_FIRST)
    if first:
        driver.execute_script("arguments[0].click();", first[0])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, DATAGRID_ROWS)))
        time.sleep(0.2)

    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, DATAGRID_ROWS)
        num_rows = len(rows)

        for row_idx in range(num_rows):
            # 1) número do processo (robusto)
            numero_processo = obter_numero_processo_da_linha_idx(driver, row_idx)
            if not numero_processo:
                continue

            # 2) pula se não houver botão de recibo
            if not tem_clipboard_na_linha_idx(driver, row_idx):
                print(f"[SKIP] linha {row_idx+1}: sem recibo (só lupa). Processo: {numero_processo}")
                continue

            # 3) abre modal e captura HTML
            body_el = clicar_clipboard_da_linha_idx(driver, wait, row_idx)
            if body_el is None:
                print(f"[SKIP] linha {row_idx+1}: recibo indisponível no momento. Processo: {numero_processo}")
                continue

            inner_html = body_el.get_attribute("innerHTML")

            # 4) sequencial e caminho
            seq_por_processo.setdefault(numero_processo, 0)
            seq_por_processo[numero_processo] += 1
            seq = seq_por_processo[numero_processo]

            filename = f"{numero_processo}-{seq}.pdf"
            dest = os.path.join(SAVE_DIR, filename)

            # 5) imprime via aba temporária
            current_handle = driver.current_window_handle
            temp_handle = abrir_aba_temporaria_com_html(driver, inner_html)
            try:
                print_tab_to_pdf(driver, dest)
            finally:
                driver.close()  # fecha aba temporária
                driver.switch_to.window(current_handle)

            total_counter["n"] += 1
            print(f"[{total_counter['n']}] PDF salvo: {filename} (processo consultado: {processo_atual})")

            # 6) fecha o modal
            fechar_modal(driver)
            time.sleep(0.15)

        # Próxima página?
        next_btns = driver.find_elements(By.CSS_SELECTOR, PAGINATION_NEXT)
        if next_btns:
            driver.execute_script("arguments[0].click();", next_btns[0])
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, DATAGRID_ROWS))
            )
            time.sleep(0.2)
        else:
            break

def main():
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

    # Carrega processos da planilha
    processos = carregar_processos(EXCEL_PATH, SHEET_NAME)
    print(f"[INFO] {len(processos)} processos carregados da planilha.")

    # Conecta ao Chrome existente
    opts = ChromeOptions()
    opts.debugger_address = "127.0.0.1:9222"
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 20, poll_frequency=0.2)

    # Garante que estamos na página correta
    if not driver.current_url.startswith(SIGFIS_CONSULTA_URL):
        driver.get(SIGFIS_CONSULTA_URL)
        wait_for_page_complete(driver)

    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, INPUT_NUMERO_PROCESSO)))

    total_counter = {"n": 0}

    for idx, proc in enumerate(processos, start=1):
        print(f"\n=== [{idx}/{len(processos)}] Consultando processo: {proc} ===")

        # Preenche campo e pesquisa
        fill_input(driver, wait, INPUT_NUMERO_PROCESSO, proc)
        btn_pesq = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, BTN_PESQUISAR)))
        safe_click(driver, btn_pesq)

        # Aguarda carregar a tabela (ou algum retorno)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, DATAGRID_ROWS))
            )
        except TimeoutException:
            pass

        # Baixa recibos em todas as páginas para este processo
        baixar_recibos_em_todas_paginas(driver, proc, total_counter)

        # Limpar para próxima consulta
        try:
            btn_limpar = driver.find_element(By.CSS_SELECTOR, BTN_LIMPAR)
            safe_click(driver, btn_limpar)
            time.sleep(0.3)
        except Exception:
            pass

    print(f"\n[OK] Finalizado. PDFs em: {SAVE_DIR} | Total de arquivos: {total_counter['n']}")

if __name__ == "__main__":
    main()
