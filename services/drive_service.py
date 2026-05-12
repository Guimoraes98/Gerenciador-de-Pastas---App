# =============================================================
#  services/drive_service.py — Integração com Google Drive
# =============================================================
#
#  Estrutura criada no Drive:
#    EFITECSOLAR-DRIVE / ANO / MÊS / VENDEDOR / pasta_cliente
#
#  Dependências: google-auth, google-auth-oauthlib,
#                google-auth-httplib2, google-api-python-client
# =============================================================

import os
from pathlib import Path

from config import (
    DRIVE_SCOPES, DRIVE_TOKEN, DRIVE_CREDS,
    DRIVE_ROOT_NAME, MESES_PT,
)
from database import local_db


# ------------------------------------------------------------------
# Autenticação
# ------------------------------------------------------------------

def autenticar_drive(parent=None) -> bool:
    """
    Executa o fluxo OAuth2 (abre o navegador).
    Salva o token em DRIVE_TOKEN e retorna True em caso de sucesso.
    Deve ser chamado em uma thread separada para não travar a UI.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = _carregar_credenciais()

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(DRIVE_CREDS, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        _salvar_token(creds)

    return bool(creds and creds.valid)


def _carregar_credenciais():
    """Carrega e, se necessário, renova as credenciais salvas."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not os.path.exists(DRIVE_TOKEN):
        return None

    try:
        creds = Credentials.from_authorized_user_file(DRIVE_TOKEN, DRIVE_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _salvar_token(creds)
        return creds if creds and creds.valid else None
    except Exception:
        return None


def _salvar_token(creds) -> None:
    with open(DRIVE_TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def _get_service():
    """
    Retorna o serviço autenticado do Drive v3.
    Lança RuntimeError se não houver credenciais válidas.
    """
    from googleapiclient.discovery import build

    creds = _carregar_credenciais()
    if not creds:
        raise RuntimeError(
            "Drive não autenticado. Conecte sua conta em 'Sincronizar Pastas'."
        )
    return build("drive", "v3", credentials=creds)


def esta_autenticado() -> bool:
    """Retorna True se existem credenciais válidas (sem abrir navegador)."""
    return _carregar_credenciais() is not None


# ------------------------------------------------------------------
# Gerenciamento de pastas no Drive
# ------------------------------------------------------------------

def _escapar(nome: str) -> str:
    """Escapa aspas simples para uso em queries da Drive API."""
    return nome.replace("'", "\\'")


def _buscar_ou_criar_pasta(service, nome: str, parent_id: str | None = None) -> str:
    """
    Busca uma pasta com o nome dado sob parent_id.
    Se não encontrar, cria e retorna o ID.
    """
    q = (
        f"name='{_escapar(nome)}' "
        "and mimeType='application/vnd.google-apps.folder' "
        "and trashed=false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"

    result = service.files().list(
        q=q, fields="files(id)", pageSize=1,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()

    arquivos = result.get("files", [])
    if arquivos:
        return arquivos[0]["id"]

    metadata = {
        "name": nome,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    pasta = service.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return pasta["id"]


def _garantir_estrutura(service, pasta: dict) -> str:
    """
    Garante que a estrutura EFITECSOLAR-DRIVE / ANO / MÊS / VENDEDOR
    exista no Drive. Retorna o ID da pasta do vendedor.
    """
    root_id   = _buscar_ou_criar_pasta(service, DRIVE_ROOT_NAME)
    ano_id    = _buscar_ou_criar_pasta(service, str(pasta["ano"]), root_id)
    mes_nome  = MESES_PT[pasta["mes"] - 1]
    mes_id    = _buscar_ou_criar_pasta(service, mes_nome, ano_id)
    vend_id   = _buscar_ou_criar_pasta(service, pasta["vendedor_nome"], mes_id)
    return vend_id


# ------------------------------------------------------------------
# Upload de arquivo
# ------------------------------------------------------------------

def _mime_type(extensao: str) -> str:
    mapa = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
        ".doc":  "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls":  "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return mapa.get(extensao.lower(), "application/octet-stream")


def _upload_documento(service, doc: dict, folder_id: str) -> None:
    """Faz upload do arquivo e salva o drive_file_id no banco."""
    from googleapiclient.http import MediaFileUpload

    caminho = doc.get("caminho_local")
    if not caminho or not os.path.exists(caminho):
        return

    mime = _mime_type(doc["extensao"])
    metadata = {"name": doc["nome_final"], "parents": [folder_id]}
    media = MediaFileUpload(caminho, mimetype=mime, resumable=True)

    arquivo = service.files().create(
        body=metadata, media_body=media,
        fields="id", supportsAllDrives=True,
    ).execute()

    local_db.atualizar_drive_documento(doc["id"], arquivo["id"])


def _garantir_pasta_no_drive(service, pasta: dict) -> str:
    """
    Retorna o drive_folder_id da pasta.
    Se ainda não tiver sido sincronizada, cria agora.
    """
    if pasta.get("drive_folder_id"):
        return pasta["drive_folder_id"]

    parent_id = _garantir_estrutura(service, pasta)
    folder_id = _buscar_ou_criar_pasta(service, pasta["nome_pasta"], parent_id)
    local_db.atualizar_drive_pasta(pasta["id"], folder_id)
    return folder_id


# ------------------------------------------------------------------
# Processamento da fila de sync
# ------------------------------------------------------------------

def sincronizar_fila() -> dict:
    """
    Processa todos os itens pendentes na sync_queue.
    Retorna dict com: ok, erros, ignorados.
    """
    service = _get_service()
    itens   = local_db.listar_pendentes_sync()

    resultado = {"ok": 0, "erros": 0, "ignorados": 0}

    for item in itens:
        try:
            op   = item["operacao"]
            tipo = item["tipo"]

            if op == "create":
                if tipo == "pasta":
                    _sync_criar_pasta(service, item)
                else:
                    _sync_criar_documento(service, item)

            elif op == "delete":
                _sync_deletar(service, item)

            else:
                resultado["ignorados"] += 1
                continue

            local_db.marcar_sync_ok(item["id"])
            resultado["ok"] += 1

        except Exception as e:
            local_db.marcar_sync_erro(item["id"], str(e))
            resultado["erros"] += 1

    return resultado


def _sync_criar_pasta(service, item: dict) -> None:
    pasta = local_db.get_pasta(item["ref_id"])
    if not pasta:
        return  # pasta foi deletada antes de sincronizar

    if pasta.get("drive_folder_id"):
        return  # já sincronizada

    folder_id = _garantir_pasta_no_drive(service, pasta)

    # Sobe também os documentos existentes ainda não sincronizados
    docs = local_db.listar_documentos(pasta["id"])
    for doc in docs:
        if not doc.get("drive_file_id"):
            _upload_documento(service, doc, folder_id)


def _sync_criar_documento(service, item: dict) -> None:
    doc = local_db.get_documento(item["ref_id"])
    if not doc:
        return

    if doc.get("drive_file_id"):
        return  # já enviado (ex: subido junto com a pasta)

    pasta = local_db.get_pasta(doc["pasta_id"])
    if not pasta:
        return

    folder_id = _garantir_pasta_no_drive(service, pasta)
    _upload_documento(service, doc, folder_id)


def _sync_deletar(service, item: dict) -> None:
    """
    Para operações 'delete', o drive_id foi salvo em ultimo_erro
    antes de o registro ser removido do banco.
    """
    drive_id = item.get("ultimo_erro")
    if not drive_id:
        return

    try:
        service.files().delete(
            fileId=drive_id, supportsAllDrives=True
        ).execute()
    except Exception as e:
        # 404 = já foi deletado do Drive — não é erro
        if "404" not in str(e) and "notFound" not in str(e):
            raise
