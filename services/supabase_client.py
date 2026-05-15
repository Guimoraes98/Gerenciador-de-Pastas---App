# =============================================================
#  services/supabase_client.py — Sync bidirecional com Supabase
# =============================================================
#
#  Estratégia:
#    PULL (Supabase → local): traz dados de outros PCs/usuários
#      Ordem: usuarios → pastas → documentos
#    PUSH (local → Supabase): envia dados locais como backup
#      Ordem: usuarios → metas → pastas → documentos
#
#  sincronizar_tudo() = pull + push (chamado pelo loop de 5 min
#  e pelo botão "Sincronizar Agora")
# =============================================================

from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY
from database import local_db


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


# ------------------------------------------------------------------
# Pull por tabela (Supabase → local)
# ------------------------------------------------------------------

def _pull_usuarios(client, res: dict):
    """Puxa todos os usuários do Supabase e cria/atualiza localmente."""
    try:
        r = client.table("usuarios").select(
            "id, nome, email, senha_hash, tipo, ativo"
        ).execute()
        for u in (r.data or []):
            try:
                with local_db.get_conn() as conn:
                    row = conn.execute(
                        "SELECT id FROM usuarios WHERE supabase_id = ? OR email = ?",
                        (str(u["id"]), u["email"])
                    ).fetchone()
                    if row:
                        conn.execute("""
                            UPDATE usuarios
                            SET nome=?, senha_hash=?, tipo=?, ativo=?,
                                supabase_id=?, atualizado_em=?
                            WHERE id=?
                        """, (u["nome"], u["senha_hash"], u["tipo"],
                              1 if u["ativo"] else 0,
                              str(u["id"]), _now(), row["id"]))
                    else:
                        conn.execute("""
                            INSERT INTO usuarios
                                (nome, email, senha_hash, tipo, ativo, supabase_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (u["nome"], u["email"], u["senha_hash"], u["tipo"],
                              1 if u["ativo"] else 0, str(u["id"])))
                res["ok"] += 1
            except Exception as e:
                res["erros"] += 1
                res["detalhes_erro"].append(f"pull_usuario: {e}")
    except Exception as e:
        res["erros"] += 1
        res["detalhes_erro"].append(f"pull_usuarios: {e}")


def _pull_pastas(client, res: dict):
    """Puxa todas as pastas do Supabase e cria/atualiza/remove localmente."""
    try:
        r = client.table("pastas").select("*").execute()
        supabase_ids: set[str] = set()
        for p in (r.data or []):
            try:
                pid_str = str(p["id"])
                supabase_ids.add(pid_str)
                with local_db.get_conn() as conn:
                    vend_row = conn.execute(
                        "SELECT id FROM usuarios WHERE supabase_id = ?",
                        (str(p["vendedor_id"]),)
                    ).fetchone()
                    if not vend_row:
                        continue

                    local_vend_id = vend_row["id"]

                    existing = conn.execute(
                        "SELECT id FROM pastas WHERE supabase_id = ?", (pid_str,)
                    ).fetchone()

                    if existing:
                        conn.execute("""
                            UPDATE pastas
                            SET nome_pasta=?, nome_cliente=?, cidade=?, kwp=?,
                                valor_venda=?, sdr=?, id_crm=?, vendedor_id=?,
                                vendedor_nome=?, drive_folder_id=?, mes=?, ano=?,
                                atualizado_em=?
                            WHERE supabase_id=?
                        """, (p["nome_pasta"], p["nome_cliente"], p["cidade"],
                              float(p["kwp"]), p.get("valor_venda"), p.get("sdr"),
                              p.get("id_crm"), local_vend_id, p["vendedor_nome"],
                              p.get("drive_folder_id"), p["mes"], p["ano"],
                              _now(), pid_str))
                    else:
                        conn.execute("""
                            INSERT INTO pastas
                            (nome_pasta, nome_cliente, cidade, kwp, valor_venda, sdr,
                             id_crm, vendedor_id, vendedor_nome, drive_folder_id,
                             mes, ano, status, sync_status, supabase_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?)
                        """, (p["nome_pasta"], p["nome_cliente"], p["cidade"],
                              float(p["kwp"]), p.get("valor_venda"), p.get("sdr"),
                              p.get("id_crm"), local_vend_id, p["vendedor_nome"],
                              p.get("drive_folder_id"), p["mes"], p["ano"],
                              p.get("status", "incompleta"), pid_str))
                res["ok"] += 1
            except Exception as e:
                res["erros"] += 1
                res["detalhes_erro"].append(f"pull_pasta: {e}")

        # Sync de exclusões: remove localmente pastas que sumiram do Supabase
        if supabase_ids:
            try:
                placeholders = ",".join("?" * len(supabase_ids))
                with local_db.get_conn() as conn:
                    conn.execute(
                        f"DELETE FROM pastas WHERE supabase_id IS NOT NULL "
                        f"AND supabase_id NOT IN ({placeholders})",
                        list(supabase_ids),
                    )
            except Exception:
                pass
    except Exception as e:
        res["erros"] += 1
        res["detalhes_erro"].append(f"pull_pastas: {e}")


def _pull_documentos(client, res: dict):
    """Puxa todos os documentos do Supabase e cria/atualiza localmente."""
    try:
        r = client.table("documentos").select("*").execute()
        for d in (r.data or []):
            try:
                with local_db.get_conn() as conn:
                    # Mapeia supabase pasta_id → id local da pasta
                    pasta_row = conn.execute(
                        "SELECT id FROM pastas WHERE supabase_id = ?", (str(d["pasta_id"]),)
                    ).fetchone()
                    if not pasta_row:
                        continue

                    local_pasta_id = pasta_row["id"]

                    existing = conn.execute(
                        "SELECT id FROM documentos WHERE supabase_id = ?", (str(d["id"]),)
                    ).fetchone()

                    if existing:
                        conn.execute("""
                            UPDATE documentos
                            SET tipo=?, subtipo=?, nome_original=?, nome_final=?,
                                extensao=?, drive_file_id=?
                            WHERE supabase_id=?
                        """, (d["tipo"], d.get("subtipo"), d["nome_original"],
                              d["nome_final"], d["extensao"], d.get("drive_file_id"),
                              str(d["id"])))
                    else:
                        # sync_status='ok' pois já existe no Supabase
                        conn.execute("""
                            INSERT INTO documentos
                            (pasta_id, tipo, subtipo, nome_original, nome_final,
                             extensao, drive_file_id, sync_status, supabase_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'ok', ?)
                        """, (local_pasta_id, d["tipo"], d.get("subtipo"),
                              d["nome_original"], d["nome_final"], d["extensao"],
                              d.get("drive_file_id"), str(d["id"])))
                res["ok"] += 1
            except Exception as e:
                res["erros"] += 1
                res["detalhes_erro"].append(f"pull_doc: {e}")
    except Exception as e:
        res["erros"] += 1
        res["detalhes_erro"].append(f"pull_documentos: {e}")


# ------------------------------------------------------------------
# Funções públicas de pull
# ------------------------------------------------------------------

def puxar_usuarios_do_supabase() -> int:
    """
    Puxa usuários do Supabase para o banco local.
    Usado na tela de login de PCs novos antes da primeira sync completa.
    """
    try:
        client = _get_client()
        res = {"ok": 0, "erros": 0, "detalhes_erro": []}
        _pull_usuarios(client, res)
        return res["ok"]
    except Exception:
        return 0


def excluir_pasta_remota(supabase_id: str):
    """Remove pasta e documentos do Supabase. Chamado em background após exclusão local."""
    try:
        client = _get_client()
        client.table("documentos").delete().eq("pasta_id", supabase_id).execute()
        client.table("pastas").delete().eq("id", supabase_id).execute()
    except Exception:
        pass


def puxar_tudo_do_supabase() -> dict:
    """
    Pull completo: usuarios → pastas → documentos → recalcula status.
    Chamado ao iniciar o app para ter dados frescos imediatamente.
    """
    resultado = {"ok": 0, "erros": 0, "detalhes_erro": []}
    try:
        client = _get_client()
        _pull_usuarios(client, resultado)
        _pull_pastas(client, resultado)
        _pull_documentos(client, resultado)
    except Exception as e:
        resultado["erros"] += 1
        resultado["detalhes_erro"].append(str(e))
    try:
        from database.local_db import recalcular_status_todas_pastas
        recalcular_status_todas_pastas()
    except Exception:
        pass
    return resultado


# ------------------------------------------------------------------
# Sync principal (pull + push)
# ------------------------------------------------------------------

def sincronizar_tudo() -> dict:
    """
    Sincronização bidirecional completa:
      1. Pull: traz dados de outros PCs do Supabase para local
      2. Push: envia dados locais para o Supabase
    Retorna dict com: ok, erros, detalhes_erro.
    """
    client = _get_client()
    resultado = {"ok": 0, "erros": 0, "detalhes_erro": []}

    # 1. Pull — garante que dados de outros PCs estão disponíveis localmente
    _pull_usuarios(client, resultado)
    _pull_pastas(client, resultado)
    _pull_documentos(client, resultado)

    # 2. Push — envia dados locais para o Supabase
    _sync_usuarios(client, resultado)
    _sync_metas(client, resultado)
    _sync_pastas(client, resultado)
    _sync_documentos(client, resultado)

    return resultado


# ------------------------------------------------------------------
# Push por tabela (local → Supabase)
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
                "mes":         m["mes"],
                "ano":         m["ano"],
                "meta_vendas": m["meta_vendas"],
                "meta_valor":  float(m["meta_valor"]),
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
                "nome_pasta":      p["nome_pasta"],
                "nome_cliente":    p["nome_cliente"],
                "cidade":          p["cidade"],
                "kwp":             float(p["kwp"]),
                "valor_venda":     float(p["valor_venda"]) if p.get("valor_venda") else None,
                "sdr":             p.get("sdr"),
                "id_crm":          p.get("id_crm"),
                "vendedor_id":     vend.get("supabase_id") if vend else None,
                "vendedor_nome":   p["vendedor_nome"],
                "drive_folder_id": p.get("drive_folder_id"),
                "mes":             p["mes"],
                "ano":             p["ano"],
                "status":          p["status"],
                "local_id":        p["id"],
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
            continue

        for d in local_db.listar_documentos(p["id"]):
            try:
                dados = {
                    "pasta_id":      pasta_sid,
                    "tipo":          d["tipo"],
                    "subtipo":       d.get("subtipo"),
                    "nome_original": d["nome_original"],
                    "nome_final":    d["nome_final"],
                    "extensao":      d["extensao"],
                    "drive_file_id": d.get("drive_file_id"),
                    "local_id":      d["id"],
                }
                sid = d.get("supabase_id")
                if sid:
                    client.table("documentos").update(dados).eq("id", sid).execute()
                else:
                    r = client.table("documentos").insert(dados).execute()
                    if r.data:
                        local_db.set_supabase_id("documentos", d["id"], str(r.data[0]["id"]))
                res["ok"] += 1
            except Exception as e:
                res["erros"] += 1
                res["detalhes_erro"].append(str(e))
