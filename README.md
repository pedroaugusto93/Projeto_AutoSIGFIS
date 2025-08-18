Projeto AutoSIGFIS / AutoSIGFIS Project
Descrição (Português)
Automação em Python + Selenium para preenchimento de cadastros no sistema SIGFIS (Sistema de Gestão de Fiscalização). O sistema lê dados de uma planilha Excel (cadastro.xlsx) e realiza o preenchimento automático das abas: Dados Básicos, Itens, Documentos e Empenhos.
Estrutura do Projeto
Projeto_AutoSIGFIS/
├── config.py             # Configurações fixas e leitura da planilha
├── helpers.py            # Funções utilitárias (inputs, selects, waits…)
├── main.py               # Fluxo principal da automação
├── page_dados_basicos.py # Lógica da aba "Dados Básicos"
├── page_itens.py         # Lógica da aba "Itens"
├── page_empenhos.py      # Lógica da aba "Empenhos"
├── page_documentos.py    # Lógica da aba "Documentos"
├── cadastro.xlsx         # Planilha de entrada
└── requirements.txt      # Dependências do projeto
Instalação
# 1) Clone o repositório
git clone https://github.com/seu-usuario/Projeto_AutoSIGFIS.git
cd Projeto_AutoSIGFIS

# 2) Crie e ative a venv
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
# ou
source venv/bin/activate    # Linux/Mac

# 3) Instale as dependências
pip install -r requirements.txt
Execução
1) Inicie o Google Chrome em modo depuração:
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
2) Execute o script:
python main.py
Tecnologias
Python 3.9+, Selenium, Pandas, OpenPyXL, WebDriver Manager
Autor
Pedro - Projeto desenvolvido para automatizar cadastros no SIGFIS e compor portfólio público.
Description (English)
Automation in Python + Selenium for filling out records in the SIGFIS system. The bot reads data from an Excel file (cadastro.xlsx) and automatically fills in the tabs: Basic Data, Items, Documents and Commitments.
Project Structure
Projeto_AutoSIGFIS/
├── config.py             # Fixed settings and Excel loading
├── helpers.py            # Utility functions (inputs, selects, waits…)
├── main.py               # Main automation flow
├── page_dados_basicos.py # "Basic Data" tab logic
├── page_itens.py         # "Items" tab logic
├── page_empenhos.py      # "Commitments" tab logic
├── page_documentos.py    # "Documents" tab logic
├── cadastro.xlsx         # Input spreadsheet
└── requirements.txt      # Project dependencies
Installation
# 1) Clone repository
git clone https://github.com/your-user/Projeto_AutoSIGFIS.git
cd Projeto_AutoSIGFIS

# 2) Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
# or
source venv/bin/activate    # Linux/Mac

# 3) Install dependencies
pip install -r requirements.txt
Execution
1) Launch Google Chrome in debug mode:
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
2) Run the script:
python main.py
Technologies
Python 3.9+, Selenium, Pandas, OpenPyXL, WebDriver Manager
Author
Pedro - Project developed to automate SIGFIS records and serve as a public portfolio.
