# =============================================================
#  database/local_db.py — Banco de dados local SQLite
# =============================================================
#
#  Responsável por toda persistência offline do app.
#  Supabase é usado para sync online, mas tudo funciona sem internet.
# =============================================================

import sqlite3
import hashlib
import json
import os
from datetime import datetime
from contextlib import contextmanager

from config import LOCAL_DB_PATH


# ------------------------------------------------------------------
# Conexão
# ------------------------------------------------------------------

@contextmanager
def get_conn():
    """Context manager para conexão SQLite com foreign keys ativas."""
    conn = sqlite3.connect(LOCAL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------
# Inicialização — cria todas as tabelas se não existirem
# ------------------------------------------------------------------

def init_db():
    """Cria o schema do banco local na primeira execução."""
    with get_conn() as conn:
        conn.executescript("""
        -- --------------------------------------------------------
        -- Usuários do sistema
        -- --------------------------------------------------------
        CREATE TABLE IF NOT EXISTS usuarios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            senha_hash      TEXT    NOT NULL,
            tipo            TEXT    NOT NULL DEFAULT 'Vendedor',  -- 'Vendedor' | 'ADM'
            ativo           INTEGER NOT NULL DEFAULT 1,
            avatar_path     TEXT,
            supabase_id     TEXT,                                 -- ID no Supabase para sync
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            atualizado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- --------------------------------------------------------
        -- Pastas de clientes
        -- --------------------------------------------------------
        CREATE TABLE IF NOT EXISTS pastas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_pasta      TEXT    NOT NULL,       -- nome gerado automaticamente
            nome_cliente    TEXT    NOT NULL,
            cidade          TEXT    NOT NULL,
            kwp             REAL    NOT NULL,
            valor_venda     REAL,
            sdr             TEXT,
            id_crm          TEXT,
            vendedor_id     INTEGER NOT NULL REFERENCES usuarios(id),
            vendedor_nome   TEXT    NOT NULL,
            caminho_local   TEXT,                   -- caminho absoluto no PC
            drive_folder_id TEXT,                   -- ID da pasta no Google Drive
            mes             INTEGER NOT NULL,       -- 1-12
            ano             INTEGER NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'incompleta',  -- 'completa' | 'incompleta'
            sync_status     TEXT    NOT NULL DEFAULT 'pendente',    -- 'ok' | 'pendente' | 'erro'
            supabase_id     TEXT,
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            atualizado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- --------------------------------------------------------
        -- Documentos dentro das pastas
        -- --------------------------------------------------------
        CREATE TABLE IF NOT EXISTS documentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pasta_id        INTEGER NOT NULL REFERENCES pastas(id) ON DELETE CASCADE,
            tipo            TEXT    NOT NULL,       -- ex: "CNH", "Contrato"
            subtipo         TEXT,                   -- ex: "Principal", "Rateio"
            nome_original   TEXT    NOT NULL,       -- nome original do arquivo
            nome_final      TEXT    NOT NULL,       -- nome padronizado
            extensao        TEXT    NOT NULL,       -- .pdf, .jpg, etc.
            caminho_local   TEXT,                   -- caminho absoluto no PC
            drive_file_id   TEXT,                   -- ID do arquivo no Drive
            sync_status     TEXT    NOT NULL DEFAULT 'pendente',  -- 'ok' | 'pendente' | 'erro'
            supabase_id     TEXT,
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- --------------------------------------------------------
        -- Metas mensais (configuradas pelo ADM)
        -- --------------------------------------------------------
        CREATE TABLE IF NOT EXISTS metas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            mes             INTEGER NOT NULL,
            ano             INTEGER NOT NULL,
            meta_vendas     INTEGER NOT NULL DEFAULT 0,   -- nº de pastas completas
            meta_valor      REAL    NOT NULL DEFAULT 0.0, -- valor total em R$
            supabase_id     TEXT,
            UNIQUE(mes, ano)
        );

        -- --------------------------------------------------------
        -- Fila de sincronização (itens pendentes de envio ao Drive)
        -- --------------------------------------------------------
        CREATE TABLE IF NOT EXISTS sync_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT    NOT NULL,  -- 'pasta' | 'documento'
            ref_id          INTEGER NOT NULL,  -- id da pasta ou documento
            operacao        TEXT    NOT NULL,  -- 'create' | 'update' | 'delete'
            tentativas      INTEGER NOT NULL DEFAULT 0,
            ultimo_erro     TEXT,
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """)

    # Garante que existe ao menos um usuário ADM
    _garantir_adm_padrao()


def _garantir_adm_padrao():
    """Cria o usuário ADM padrão se o banco estiver vazio."""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM usuarios").fetchone()
        if row["cnt"] == 0:
            conn.execute("""
                INSERT INTO usuarios (nome, email, senha_hash, tipo)
                VALUES (?, ?, ?, ?)
            """, ("Administrador", "adm@efitecsolar.com.br", _hash("adm123"), "ADM"))


# ------------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------------

def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------
# Usuários
# ------------------------------------------------------------------

def autenticar(email: str, senha: str):
    """
    Retorna (True, dict_usuario) se credenciais válidas e usuário ativo,
    ou (False, None) caso contrário.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE email = ? AND ativo = 1",
            (email.lower().strip(),)
        ).fetchone()
    if row and row["senha_hash"] == _hash(senha):
        return True, dict(row)
    return False, None


def listar_usuarios():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM usuarios ORDER BY nome"
        ).fetchall()
    return [dict(r) for r in rows]


def criar_usuario(nome: str, email: str, senha: str, tipo: str = "Vendedor", avatar_path: str = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO usuarios (nome, email, senha_hash, tipo, avatar_path)
            VALUES (?, ?, ?, ?, ?)
        """, (nome.strip(), email.lower().strip(), _hash(senha), tipo, avatar_path))


def atualizar_usuario(user_id: int, **kwargs):
    """Atualiza campos do usuário. Aceita: nome, email, senha, ativo, avatar_path, tipo."""
    campos = []
    valores = []
    if "nome" in kwargs:
        campos.append("nome = ?"); valores.append(kwargs["nome"])
    if "email" in kwargs:
        campos.append("email = ?"); valores.append(kwargs["email"].lower().strip())
    if "senha" in kwargs:
        campos.append("senha_hash = ?"); valores.append(_hash(kwargs["senha"]))
    if "ativo" in kwargs:
        campos.append("ativo = ?"); valores.append(int(kwargs["ativo"]))
    if "avatar_path" in kwargs:
        campos.append("avatar_path = ?"); valores.append(kwargs["avatar_path"])
    if "tipo" in kwargs:
        campos.append("tipo = ?"); valores.append(kwargs["tipo"])
    if not campos:
        return
    campos.append("atualizado_em = ?"); valores.append(_now())
    valores.append(user_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?", valores)


def get_usuario(user_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ------------------------------------------------------------------
# Pastas
# ------------------------------------------------------------------

def criar_pasta(dados: dict) -> int:
    """
    Cria uma pasta e a adiciona à fila de sync.
    Retorna o ID da pasta criada.
    """
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO pastas
                (nome_pasta, nome_cliente, cidade, kwp, valor_venda,
                 sdr, id_crm, vendedor_id, vendedor_nome,
                 caminho_local, mes, ano)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["nome_pasta"],
            dados["nome_cliente"],
            dados["cidade"],
            dados["kwp"],
            dados.get("valor_venda"),
            dados.get("sdr"),
            dados.get("id_crm"),
            dados["vendedor_id"],
            dados["vendedor_nome"],
            dados.get("caminho_local"),
            dados["mes"],
            dados["ano"],
        ))
        pasta_id = cur.lastrowid
        # Adiciona à fila de sync
        conn.execute("""
            INSERT INTO sync_queue (tipo, ref_id, operacao)
            VALUES ('pasta', ?, 'create')
        """, (pasta_id,))
    return pasta_id


def listar_pastas(vendedor_id: int = None, mes: int = None, ano: int = None):
    """
    Lista pastas com filtros opcionais.
    Se vendedor_id=None, retorna de todos os vendedores (visão ADM).
    """
    query = "SELECT * FROM pastas WHERE 1=1"
    params = []
    if vendedor_id is not None:
        query += " AND vendedor_id = ?"; params.append(vendedor_id)
    if mes is not None:
        query += " AND mes = ?"; params.append(mes)
    if ano is not None:
        query += " AND ano = ?"; params.append(ano)
    query += " ORDER BY criado_em DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_pasta(pasta_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM pastas WHERE id = ?", (pasta_id,)).fetchone()
    return dict(row) if row else None


def atualizar_status_pasta(pasta_id: int, status: str):
    """status: 'completa' | 'incompleta'"""
    with get_conn() as conn:
        conn.execute("""
            UPDATE pastas SET status = ?, atualizado_em = ? WHERE id = ?
        """, (status, _now(), pasta_id))


def atualizar_drive_pasta(pasta_id: int, drive_folder_id: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE pastas SET drive_folder_id = ?, sync_status = 'ok', atualizado_em = ?
            WHERE id = ?
        """, (drive_folder_id, _now(), pasta_id))


def excluir_pasta(pasta_id: int):
    with get_conn() as conn:
        # Salva drive_folder_id antes de deletar para o sync remover do Drive
        row = conn.execute(
            "SELECT drive_folder_id FROM pastas WHERE id = ?", (pasta_id,)
        ).fetchone()
        drive_id = row["drive_folder_id"] if row else None
        if drive_id:
            conn.execute("""
                INSERT INTO sync_queue (tipo, ref_id, operacao, ultimo_erro)
                VALUES ('pasta', ?, 'delete', ?)
            """, (pasta_id, drive_id))
        conn.execute("DELETE FROM pastas WHERE id = ?", (pasta_id,))


# ------------------------------------------------------------------
# Documentos
# ------------------------------------------------------------------

def adicionar_documento(dados: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO documentos
                (pasta_id, tipo, subtipo, nome_original, nome_final,
                 extensao, caminho_local)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["pasta_id"],
            dados["tipo"],
            dados.get("subtipo"),
            dados["nome_original"],
            dados["nome_final"],
            dados["extensao"],
            dados.get("caminho_local"),
        ))
        doc_id = cur.lastrowid
        conn.execute("""
            INSERT INTO sync_queue (tipo, ref_id, operacao)
            VALUES ('documento', ?, 'create')
        """, (doc_id,))
    return doc_id


def listar_documentos(pasta_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documentos WHERE pasta_id = ? ORDER BY tipo",
            (pasta_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def set_supabase_id(tabela: str, local_id: int, supabase_id: str):
    """Salva o ID retornado pelo Supabase no registro local."""
    _TABELAS = {"usuarios", "pastas", "documentos", "metas"}
    if tabela not in _TABELAS:
        raise ValueError(f"Tabela inválida: {tabela}")
    extra = ", atualizado_em = ?" if tabela in ("usuarios", "pastas") else ""
    params = [supabase_id]
    if extra:
        params.append(_now())
    params.append(local_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {tabela} SET supabase_id = ?{extra} WHERE id = ?", params
        )


def get_documento(doc_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documentos WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def atualizar_drive_documento(doc_id: int, drive_file_id: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE documentos SET drive_file_id = ?, sync_status = 'ok' WHERE id = ?
        """, (drive_file_id, doc_id))


def excluir_documento(doc_id: int):
    with get_conn() as conn:
        # Salva drive_file_id antes de deletar para o sync remover do Drive
        row = conn.execute(
            "SELECT drive_file_id FROM documentos WHERE id = ?", (doc_id,)
        ).fetchone()
        drive_id = row["drive_file_id"] if row else None
        if drive_id:
            conn.execute("""
                INSERT INTO sync_queue (tipo, ref_id, operacao, ultimo_erro)
                VALUES ('documento', ?, 'delete', ?)
            """, (doc_id, drive_id))
        conn.execute("DELETE FROM documentos WHERE id = ?", (doc_id,))


# ------------------------------------------------------------------
# Status / documentos faltando
# ------------------------------------------------------------------

def calcular_status_pasta(pasta_id: int) -> dict:
    """
    Retorna dict com:
      - status: 'completa' | 'incompleta'
      - presentes: lista de tipos já adicionados
      - faltando: lista de tipos obrigatórios ausentes
    """
    from config import DOCS_CONFIG

    docs = listar_documentos(pasta_id)
    tipos_presentes = set(d["tipo"] for d in docs)

    faltando = []
    for tipo, cfg in DOCS_CONFIG.items():
        if tipo not in tipos_presentes:
            faltando.append(tipo)

    status = "completa" if not faltando else "incompleta"
    # Atualiza o status no banco
    atualizar_status_pasta(pasta_id, status)

    return {
        "status":    status,
        "presentes": sorted(tipos_presentes),
        "faltando":  faltando,
    }


# ------------------------------------------------------------------
# Metas
# ------------------------------------------------------------------

def salvar_meta(mes: int, ano: int, meta_vendas: int, meta_valor: float):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO metas (mes, ano, meta_vendas, meta_valor)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mes, ano) DO UPDATE SET
                meta_vendas = excluded.meta_vendas,
                meta_valor  = excluded.meta_valor
        """, (mes, ano, meta_vendas, meta_valor))


def get_meta(mes: int, ano: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM metas WHERE mes = ? AND ano = ?", (mes, ano)
        ).fetchone()
    return dict(row) if row else {"meta_vendas": 0, "meta_valor": 0.0}


# ------------------------------------------------------------------
# Ranking de vendas (para a corrida na Home)
# ------------------------------------------------------------------

def ranking_vendas(mes: int, ano: int) -> list:
    """
    Retorna lista de dicts ordenada por nº de vendas (pastas completas),
    incluindo nome, avatar e valor total.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                u.id,
                u.nome,
                u.avatar_path,
                COUNT(p.id)    AS num_vendas,
                COALESCE(SUM(p.valor_venda), 0) AS valor_total
            FROM usuarios u
            LEFT JOIN pastas p ON p.vendedor_id = u.id
                AND p.mes    = ?
                AND p.ano    = ?
                AND p.status = 'completa'
            WHERE u.tipo = 'Vendedor' AND u.ativo = 1
            GROUP BY u.id
            ORDER BY num_vendas DESC, valor_total DESC
        """, (mes, ano)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# Fila de Sync
# ------------------------------------------------------------------

def listar_pendentes_sync() -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM sync_queue
            WHERE tentativas < 5
            ORDER BY criado_em
        """).fetchall()
    return [dict(r) for r in rows]


def marcar_sync_ok(queue_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM sync_queue WHERE id = ?", (queue_id,))


def marcar_sync_erro(queue_id: int, erro: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE sync_queue
            SET tentativas = tentativas + 1, ultimo_erro = ?
            WHERE id = ?
        """, (erro, queue_id))


def adicionar_sync_manual(pasta_id: int):
    """Força nova tentativa de sync para uma pasta."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO sync_queue (tipo, ref_id, operacao)
            VALUES ('pasta', ?, 'create')
        """, (pasta_id,))
