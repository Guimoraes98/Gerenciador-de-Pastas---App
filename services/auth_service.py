# =============================================================
#  services/auth_service.py — Sessão e usuário logado
# =============================================================

import json
import os
from config import SESSION_FILE


# Usuário logado na sessão atual (dicionário em memória)
_sessao_atual: dict | None = None


def salvar_sessao(usuario: dict):
    """Persiste a sessão em disco e em memória."""
    global _sessao_atual
    _sessao_atual = usuario
    campos = {k: usuario[k] for k in ("id", "nome", "email", "tipo", "avatar_path") if k in usuario}
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(campos, f, ensure_ascii=False)
    except Exception:
        pass


def carregar_sessao() -> dict | None:
    """Carrega sessão persistida do disco (para auto-login)."""
    global _sessao_atual
    if _sessao_atual:
        return _sessao_atual
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            _sessao_atual = json.load(f)
        return _sessao_atual
    except Exception:
        return None


def limpar_sessao():
    """Faz logout: limpa memória e arquivo."""
    global _sessao_atual
    _sessao_atual = None
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass


def usuario_logado() -> dict | None:
    return _sessao_atual


def is_adm() -> bool:
    u = usuario_logado()
    return u is not None and u.get("tipo") == "ADM"
