# Projeto AutoSIGFIS / AutoSIGFIS Project

**Português**

Automação em **Python + Selenium** para preenchimento de cadastros no sistema **SIGFIS** (Sistema de Gestão de Fiscalização).  
O sistema lê dados de uma planilha Excel (`cadastro.xlsx`) e realiza o preenchimento automático das abas:

- Dados Básicos
- Itens
- Documentos
- Empenhos

---

## 📂 Estrutura do Projeto

```
Projeto_AutoSIGFIS/
├── config.py             # Configurações fixas e leitura da planilha
├── helpers.py            # Funções utilitárias (inputs, selects, waits...)
├── main.py               # Fluxo principal da automação
├── page_dados_basicos.py # Lógica da aba "Dados Básicos"
├── page_itens.py         # Lógica da aba "Itens"
├── page_empenhos.py      # Lógica da aba "Empenhos"
├── page_documentos.py    # Lógica da aba "Documentos"
├── cadastro.xlsx         # Planilha de entrada
└── requirements.txt      # Dependências do projeto
```

---

## 🚀 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/Projeto_AutoSIGFIS.git
   cd Projeto_AutoSIGFIS
   ```

2. Crie e ative o ambiente virtual:
   ```bash
   python -m venv virtual
   .\virtual\Scripts\activate   # Windows
   source virtual/bin/activate     # Linux/Mac
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Uso

1. Abra o Chrome em modo debug:
   ```bash
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
   ```

2. Execute o script principal:
   ```bash
   python src/main.py
   ```

---

## 📌 Observações

- Os campos são preenchidos automaticamente seguindo as regras do SIGFIS.
- O `.gitignore` já está configurado para ignorar arquivos temporários e ambientes virtuais.
