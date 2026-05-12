# =============================================================
#  services/document_service.py — Documentos: nomeação e adição
# =============================================================

import os
import re
import shutil
import unicodedata
from pathlib import Path

from config import DOCS_CONFIG, DOCS_KEYWORDS
from database import local_db


# ------------------------------------------------------------------
# Detecção automática de tipo por palavras-chave
# ------------------------------------------------------------------

def _norm(texto: str) -> str:
    """Normaliza texto para comparação: lowercase, sem acento, sem pontuação."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    s = nfkd.encode("ASCII", "ignore").decode("ASCII").lower()
    return re.sub(r"[^\w\s]", " ", s)


def sugerir_tipo(nome_arquivo: str) -> str | None:
    """
    Analisa o nome do arquivo e sugere um tipo de documento.
    Retorna o tipo sugerido ou None se não encontrar match.
    """
    nome_norm = _norm(Path(nome_arquivo).stem)
    melhor_tipo  = None
    melhor_score = 0

    for tipo, keywords in DOCS_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in nome_norm)
        if score > melhor_score:
            melhor_score = score
            melhor_tipo  = tipo

    return melhor_tipo if melhor_score > 0 else None


# ------------------------------------------------------------------
# Nomenclatura padronizada
# ------------------------------------------------------------------

def gerar_nome_final(tipo: str, subtipo: str | None, extensao: str) -> str:
    """
    Gera o nome padronizado do arquivo conforme as regras do projeto.
    Ex: "CNH – Principal.pdf", "Contrato.pdf", "Pagamento Serviço – Entrada.pdf"
    """
    cfg = DOCS_CONFIG.get(tipo, {})
    base = cfg.get("nome_base", tipo)

    if subtipo and cfg.get("subtipos"):
        nome = f"{base} – {subtipo}"
    else:
        nome = base

    ext = extensao if extensao.startswith(".") else f".{extensao}"
    return f"{nome}{ext}"


# ------------------------------------------------------------------
# Adição de documento à pasta
# ------------------------------------------------------------------

def adicionar_doc_a_pasta(
    pasta_id:    int,
    caminho_orig: str,
    tipo:        str,
    subtipo:     str | None,
    caminho_pasta_local: str,
) -> tuple[bool, str, str]:
    """
    Copia o arquivo para a pasta local com nome padronizado
    e registra no banco de dados.

    Retorna (sucesso, nome_final, mensagem_erro)
    """
    origem = Path(caminho_orig)
    if not origem.exists():
        return False, "", f"Arquivo não encontrado: {caminho_orig}"

    extensao  = origem.suffix.lower()
    nome_final = gerar_nome_final(tipo, subtipo, extensao)
    destino    = Path(caminho_pasta_local) / nome_final

    # Verifica duplicata
    if destino.exists():
        return False, nome_final, (
            f"Já existe '{nome_final}' nesta pasta.\n"
            "Use a opção de substituir se quiser trocar o arquivo."
        )

    # Copia o arquivo
    try:
        shutil.copy2(str(origem), str(destino))
    except Exception as e:
        return False, "", f"Erro ao copiar arquivo:\n{e}"

    # Registra no banco
    local_db.adicionar_documento({
        "pasta_id":     pasta_id,
        "tipo":         tipo,
        "subtipo":      subtipo,
        "nome_original": origem.name,
        "nome_final":   nome_final,
        "extensao":     extensao,
        "caminho_local": str(destino),
    })

    # Recalcula status da pasta
    local_db.calcular_status_pasta(pasta_id)

    return True, nome_final, ""


def substituir_doc(
    pasta_id:    int,
    caminho_orig: str,
    tipo:        str,
    subtipo:     str | None,
    caminho_pasta_local: str,
) -> tuple[bool, str, str]:
    """
    Substitui um documento existente:
    1. Apaga o arquivo antigo do disco (independente da extensão)
    2. Remove o registro antigo do banco
    3. Copia o novo arquivo e registra
    """
    origem = Path(caminho_orig)
    if not origem.exists():
        return False, "", f"Arquivo não encontrado: {caminho_orig}"

    # Remove arquivo(s) antigo(s) do disco e do banco
    docs = local_db.listar_documentos(pasta_id)
    for d in docs:
        if d["tipo"] == tipo and d.get("subtipo") == subtipo:
            old_path = d.get("caminho_local")
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
            local_db.excluir_documento(d["id"])

    extensao   = origem.suffix.lower()
    nome_final = gerar_nome_final(tipo, subtipo, extensao)
    destino    = Path(caminho_pasta_local) / nome_final

    try:
        shutil.copy2(str(origem), str(destino))
    except Exception as e:
        return False, "", f"Erro ao copiar arquivo:\n{e}"

    local_db.adicionar_documento({
        "pasta_id":     pasta_id,
        "tipo":         tipo,
        "subtipo":      subtipo,
        "nome_original": origem.name,
        "nome_final":   nome_final,
        "extensao":     extensao,
        "caminho_local": str(destino),
    })

    local_db.calcular_status_pasta(pasta_id)
    return True, nome_final, ""


# ------------------------------------------------------------------
# Listagem de documentos faltando
# ------------------------------------------------------------------

def docs_faltando(pasta_id: int) -> list[str]:
    """Retorna lista de tipos obrigatórios ainda não adicionados."""
    return local_db.calcular_status_pasta(pasta_id)["faltando"]
