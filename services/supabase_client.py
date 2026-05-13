# =============================================================
#  services/supabase_client.py — Sync com Supabase
# =============================================================
#
#  Estratégia:
#    - Push: envia registros locais para o Supabase (backup + visibilidade ADM)
#    - Os registros com supabase_id já preenchido são atualizados (UPDATE)
#    - Os sem supabase_id são inseridos (INSERT) e o ID retornado é salvo
#
#  Ordem: usuarios → metas → pastas → documentos (respeita FKs)
# =============================================================

from config import SUPABASE_URL, SUPABASE_KEY
from database import local_db


# ------------------------------------------------------------------
# Cliente
# ------------------------------------------------------------------

def _get_client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def testar_conexao() -> bool:
    """Retorna True se o Supabase está acessível."""
    try:
        _get_client().table("metas").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def puxar_usuarios_do_supabase() -> int:
    """
    Busca todos os usuários do Supabase e cria/atualiza no banco local.
    Usado em PCs novos para permitir login antes da primeira sincronização.
    Retorna o número de registros processados.
    """
    from datetime import datetime
    _now = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        client = _get_client()
        r = client.table("usuarios").select(
            "id, nome, email, senha_hash, tipo, ativo"
        ).execute()
        count = 0
        for u in (r.data or []):
            try:
                with local_db.get_conn() as conn:
                    row = conn.execute(
                        "SELECT id FROM usuarios WHERE email = ?", (u["email"],)
                    ).fetchone()
                    if row:
                        conn.execute("""
                            UPDATE usuarios
                            SET nome=?, senha_hash=?, tipo=?, ativo=?,
                                supabase_id=?, atualizado_em=?
                            WHERE email=?
                        """, (u["nome"], u["senha_hash"], u["tipo"],
                              1 if u["ativo"] else 0,
                              str(u["id"]), _now(), u["email"]))
                    else:
                        conn.execute("""
                            INSERT INTO usuarios
                                (nome, email, senha_hash, tipo, ativo, supabase_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (u["nome"], u["email"], u["senha_hash"], u["tipo"],
                              1 if u["ativo"] else 0, str(u["id"])))
                count += 1
            except Exception:
                pass
        return count
    except Exception:
        return 0


# ------------------------------------------------------------------
# Sync principal
# ------------------------------------------------------------------

def sincronizar_tudo() -> dict:
    """
    Push de todos os registros locais para o Supabase.
    Retorna dict com: ok, erros, detalhes_erro.
    """
    client = _get_client()
    resultado = {"ok": 0, "erros": 0, "detalhes_erro": []}

    _sync_usuarios(client, resultado)
    _sync_metas(client, resultado)
    _sync_pastas(client, resultado)
    _sync_documentos(client, resultado)

    return resultado


# ------------------------------------------------------------------
# Push por tabela
# ------------------------------------------------------------------

def _sync_usuarios(client, res: dict):
    for u in local_db.listar_usuarios():
        try:
            dados = {
                "nome":       u["nome"],
                "email":      u["email"],
                "senha_hash": u["senha_hash"],
                "tipo":       u["tipo"],
                "ativo":      bool(u["ativo"]),
                "local_id":   u["id"],
            }
            sid = u.get("supabase_id")
            if sid:
                client.table("usuarios").update(dados).eq("id", sid).execute()
            else:
                r = client.table("usuarios").upsert(
                    dados, on_conflict="email"
                ).execute()
                if r.data:
                    local_db.set_supabase_id("usuarios", u["id"], str(r.data[0]["id"]))
            res["ok"] += 1
        except Exception as e:
            res["erros"] += 1
            res["detalhes_erro"].append(str(e))


def _sync_metas(client, res: dict):
    with local_db.get_conn() as conn:
        metas = [dict(r) for r in conn.execute("SELECT * FROM metas").fetchall()]

    for m in metas:
        try:
            dados = {
                "mes":        m["mes"],
                "ano":        m["ano"],
                "meta_vendas": m["meta_vendas"],
                "meta_valor": float(m["meta_valor"]),
            }
            sid = m.get("supabase_id")
            if sid:
                client.table("metas").update(dados).eq("id", sid).execute()
            else:
                r = client.table("metas").upsert(dados, on_conflict="mes,ano").execute()
                if r.data:
                    local_db.set_supabase_id("metas", m["id"], str(r.data[0]["id"]))
            res["ok"] += 1
        except Exception as e:
            res["erros"] += 1
            res["detalhes_erro"].append(str(e))


def _sync_pastas(client, res: dict):
    for p in local_db.listar_pastas():
        try:
            vend = local_db.get_usuario(p["vendedor_id"])
            dados = {
                "nome_pasta":     p["nome_pasta"],
                "nome_cliente":   p["nome_cliente"],
                "cidade":         p["cidade"],
                "kwp":            float(p["kwp"]),
                "valor_venda":    float(p["valor_venda"]) if p.get("valor_venda") else None,
                "sdr":            p.get("sdr"),
                "id_crm":         p.get("id_crm"),
                "vendedor_id":    vend.get("supabase_id") if vend else None,
                "vendedor_nome":  p["vendedor_nome"],
                "drive_folder_id": p.get("drive_folder_id"),
                "mes":            p["mes"],
                "ano":            p["ano"],
                "status":         p["status"],
                "local_id":       p["id"],
            }
            sid = p.get("supabase_id")
            if sid:
                client.table("pastas").update(dados).eq("id", sid).execute()
            else:
                r = client.table("pastas").insert(dados).execute()
                if r.data:
                    local_db.set_supabase_id("pastas", p["id"], str(r.data[0]["id"]))
            res["ok"] += 1
        except Exception as e:
            res["erros"] += 1
            res["detalhes_erro"].append(str(e))


def _sync_documentos(client, res: dict):
    for p in local_db.listar_pastas():
        pasta_sid = p.get("supabase_id")
        if not pasta_sid:
            continue  # pasta ainda não está no Supabase

        for d in local_db.listar_documentos(p["id"]):
            try:
                dados = {
                    "pasta_id":     pasta_sid,
                    "tipo":         d["tipo"],
                    "subtipo":      d.get("subtipo"),
                    "nome_original": d["nome_original"],
                    "nome_final":   d["nome_final"],
                    "extensao":     d["extensao"],
                    "drive_file_id": d.get("drive_file_id"),
                    "local_id":     d["id"],
                }
                sid = d.get("supabase_id")
                if sid:
                    client.table("documentos").update(dados).eq("id", sid).execute()
                else:
                    r = client.table("documentos").insert(dados).execute()
                    if r.data:
                        local_db.set_supabase_id("documentos", d["id"], str(r.data[0]["id"]))
                res["ok"] += 1
            except Exception:
                res["erros"] += 1
