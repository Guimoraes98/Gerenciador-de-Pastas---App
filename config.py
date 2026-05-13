# =============================================================
#  config.py — Configurações globais do App Efitecsolar
# =============================================================

import os
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Versão
# ------------------------------------------------------------------
APP_VERSION = "1.0.1"
APP_NAME    = "Efitecsolar – Gerenciador de Pastas"

# ------------------------------------------------------------------
# Caminhos base (funciona tanto em .py quanto em .exe via PyInstaller)
# ------------------------------------------------------------------
if getattr(sys, "frozen", False):
    RUNTIME_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR  = getattr(sys, "_MEIPASS", RUNTIME_DIR)
else:
    RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR  = RUNTIME_DIR

APP_DIR    = RUNTIME_DIR                                  # arquivos persistentes (db, sessão, token)
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")          # imagens, ícones (empacotados)

# ------------------------------------------------------------------
# Arquivos persistentes
# ------------------------------------------------------------------
LOCAL_DB_PATH  = os.path.join(APP_DIR, "efitec_local.db")
SESSION_FILE   = os.path.join(APP_DIR, "session.json")
DRIVE_TOKEN    = os.path.join(APP_DIR, "drive_token.json")
DRIVE_CREDS    = os.path.join(ASSETS_DIR, "credentials.json")

# ------------------------------------------------------------------
# Estrutura local de pastas
# ------------------------------------------------------------------
# Desktop\Pastas_Clientes\ANO\MÊS\nome_pasta_cliente
DESKTOP_PATH      = Path.home() / "Desktop"
BASE_LOCAL_DIR    = DESKTOP_PATH / "Pastas_Clientes"

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# ------------------------------------------------------------------
# Estrutura no Google Drive
# ------------------------------------------------------------------
# EFITECSOLAR-DRIVE / ANO / MÊS / VENDEDOR / pasta_cliente
DRIVE_ROOT_NAME = "EFITECSOLAR-DRIVE"

# ------------------------------------------------------------------
# Documentos obrigatórios e seus subtipos
# ------------------------------------------------------------------
DOCS_CONFIG = {
    "CNH":                  {"subtipos": ["Principal", "Rateio"],              "nome_base": "CNH"},
    "Conta de Luz":         {"subtipos": ["Principal", "Rateio"],              "nome_base": "Conta de Luz"},
    "Contrato":             {"subtipos": [],                                   "nome_base": "Contrato"},
    "Proposta Comercial":   {"subtipos": [],                                   "nome_base": "Proposta Comercial"},
    "Procuração":           {"subtipos": [],                                   "nome_base": "Procuração"},
    "Projeto 2D":           {"subtipos": [],                                   "nome_base": "Projeto 2D"},
    "Nota Fiscal":          {"subtipos": [],                                   "nome_base": "Nota Fiscal"},
    "Lista de Equipamento": {"subtipos": [],                                   "nome_base": "Lista de Equipamento"},
    "Checklist":            {"subtipos": [],                                   "nome_base": "Checklist"},
    "Pagamento Serviço":    {"subtipos": ["Entrada", "50%", "Quitação"],       "nome_base": "Pagamento Serviço"},
    "Pagamento Equipamento":{"subtipos": ["Entrada", "50%", "Quitação"],       "nome_base": "Pagamento Equipamento"},
}

DOCS_OBRIGATORIOS = list(DOCS_CONFIG.keys())

# Palavras-chave para sugestão automática de tipo de documento
DOCS_KEYWORDS = {
    "CNH":                  ["cnh", "carteira", "habilitacao", "rg", "identidade", "cpf"],
    "Conta de Luz":         ["conta", "luz", "energia", "eletrica", "fatura", "cemig", "coelba", "copel", "enel"],
    "Contrato":             ["contrato", "contract"],
    "Proposta Comercial":   ["proposta", "comercial", "orcamento", "cotacao"],
    "Procuração":           ["procuracao", "procuracao", "mandato"],
    "Projeto 2D":           ["projeto", "2d", "planta", "layout"],
    "Nota Fiscal":          ["nota", "fiscal", "nf", "nfe", "danfe", "invoice"],
    "Lista de Equipamento": ["lista", "equipamento", "material", "kit"],
    "Checklist":            ["checklist", "check", "vistoria", "inspecao"],
    "Pagamento Serviço":    ["pagamento", "servico", "servico", "recibo", "comprovante"],
    "Pagamento Equipamento":["pagamento", "equipamento", "produto", "compra"],
}

# ------------------------------------------------------------------
# Google Drive — escopos de acesso
# ------------------------------------------------------------------
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# ------------------------------------------------------------------
# Auto-updater — GitHub Releases
# ------------------------------------------------------------------
GITHUB_OWNER = "Guimoraes98"
GITHUB_REPO  = "Gerenciador-de-Pastas---App"

# ------------------------------------------------------------------
# Supabase (preenchido com as credenciais do projeto)
# ------------------------------------------------------------------
SUPABASE_URL = "https://jsstkajizawcmijxurvl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impzc3RrYWppemF3Y21panh1cnZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg1ODY1NDIsImV4cCI6MjA5NDE2MjU0Mn0.pjRWhJsabRiKAA5mZLAgBalc2dmmnIcnzUvVKC2Dj50"

# ------------------------------------------------------------------
# Tema / Cores (CustomTkinter)
# ------------------------------------------------------------------
CTK_APPEARANCE = "dark"          # "dark" | "light" | "system"
CTK_COLOR_THEME = "blue"         # tema base do CTk

# Paleta personalizada
COLORS = {
    "bg":           "#0F1117",   # fundo principal
    "sidebar":      "#16181F",   # fundo da sidebar
    "card":         "#1E2029",   # fundo dos cards
    "card_hover":   "#252836",   # card ao passar o mouse
    "stroke":       "#2A2D3A",   # bordas
    "accent":       "#F97316",   # laranja Efitecsolar (botões principais)
    "accent_hover": "#EA6A0A",
    "accent2":      "#3B82F6",   # azul (botões secundários)
    "accent2_hover":"#2563EB",
    "success":      "#22C55E",   # verde (pasta completa)
    "warning":      "#EAB308",   # amarelo
    "danger":       "#EF4444",   # vermelho (pasta incompleta)
    "text":         "#F1F5F9",   # texto principal
    "text_muted":   "#94A3B8",   # texto secundário
    "text_dim":     "#475569",   # texto apagado
}

# ------------------------------------------------------------------
# Janela principal
# ------------------------------------------------------------------
WINDOW_WIDTH  = 1300
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 260
MIN_WIDTH     = 1100
MIN_HEIGHT    = 680
