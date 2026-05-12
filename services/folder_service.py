# =============================================================
#  services/folder_service.py — Criação e gestão de pastas locais
# =============================================================

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from config import BASE_LOCAL_DIR, MESES_PT
from database import local_db


# ------------------------------------------------------------------
# Utilitários de nome
# ------------------------------------------------------------------

def _sanitize(texto: str) -> str:
    """Remove acentos e caracteres inválidos para nomes de pasta."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    ascii_str = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # Mantém letras, números, espaços e hífen
    limpo = re.sub(r"[^\w\s\-]", "", ascii_str)
    # Colapsa espaços múltiplos
    return re.sub(r"\s+", " ", limpo).strip()


def gerar_nome_pasta(nome_cliente: str, cidade: str, kwp: float, nome_vendedor: str) -> str:
    """
    Gera o nome padronizado da pasta.
    Ex: "Joao Silva - Niteroi - 7.35kwp - Carlos"
    """
    nc = _sanitize(nome_cliente).title()
    ci = _sanitize(cidade).title()
    kw = str(kwp).replace(".", ",") + "kwp"
    vd = _sanitize(nome_vendedor).split()[0].title()  # só o primeiro nome
    return f"{nc} - {ci} - {kw} - {vd}"


def gerar_caminho_local(nome_pasta: str, mes: int, ano: int) -> Path:
    """
    Retorna o Path completo onde a pasta deve ser criada localmente.
    Ex: Desktop/Pastas_Clientes/2025/Abril/nome_pasta
    """
    mes_nome = MESES_PT[mes - 1]
    return BASE_LOCAL_DIR / str(ano) / mes_nome / nome_pasta


def criar_pasta_local(nome_pasta: str, mes: int, ano: int) -> tuple[bool, str, str]:
    """
    Cria a pasta física no disco.
    Retorna (sucesso, caminho_str, mensagem).
    """
    caminho = gerar_caminho_local(nome_pasta, mes, ano)
    try:
        caminho.mkdir(parents=True, exist_ok=True)
        return True, str(caminho), ""
    except Exception as e:
        return False, "", str(e)


def abrir_pasta_local(caminho: str):
    """Abre a pasta no Explorer do Windows."""
    import subprocess
    try:
        subprocess.Popen(f'explorer "{caminho}"')
    except Exception:
        pass


def nova_pasta(dados: dict) -> tuple[bool, int, str]:
    """
    Fluxo completo de criação de pasta:
    1. Gera nome padronizado
    2. Cria diretório local
    3. Persiste no banco

    dados deve conter:
        nome_cliente, cidade, kwp, valor_venda (opt),
        sdr (opt), id_crm (opt),
        vendedor_id, vendedor_nome

    Retorna (sucesso, pasta_id, mensagem)
    """
    agora = datetime.now()
    mes = dados.get("mes", agora.month)
    ano = dados.get("ano", agora.year)

    nome_pasta = gerar_nome_pasta(
        dados["nome_cliente"],
        dados["cidade"],
        dados["kwp"],
        dados["vendedor_nome"],
    )

    # Verifica duplicata local
    pastas_existentes = local_db.listar_pastas(mes=mes, ano=ano)
    for p in pastas_existentes:
        if p["nome_pasta"].lower() == nome_pasta.lower():
            return False, -1, f"Já existe uma pasta com o nome '{nome_pasta}' neste mês."

    # Cria no disco
    ok, caminho_local, erro = criar_pasta_local(nome_pasta, mes, ano)
    if not ok:
        return False, -1, f"Não foi possível criar a pasta no disco:\n{erro}"

    # Persiste no banco
    pasta_id = local_db.criar_pasta({
        **dados,
        "nome_pasta":    nome_pasta,
        "caminho_local": caminho_local,
        "mes":           mes,
        "ano":           ano,
    })

    return True, pasta_id, caminho_local
