# =============================================================
#  services/updater.py — Auto-updater via GitHub Releases
# =============================================================

import json
import os
import subprocess
import tempfile
import urllib.request
from urllib.error import URLError

from config import APP_VERSION, GITHUB_OWNER, GITHUB_REPO

_API_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)


def _versao_tuple(v: str) -> tuple:
    """Converte '1.2.3' em (1, 2, 3) para comparação."""
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except Exception:
        return (0,)


def verificar_atualizacao() -> dict | None:
    """
    Consulta o GitHub e retorna um dict com os dados da nova versão,
    ou None se já estiver na versão mais recente ou offline.
    """
    try:
        req = urllib.request.Request(
            _API_URL,
            headers={
                "Accept":     "application/vnd.github.v3+json",
                "User-Agent": "EfitecSolar-App",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        tag = data.get("tag_name", "").lstrip("v")
        if not tag:
            return None

        if _versao_tuple(tag) <= _versao_tuple(APP_VERSION):
            return None

        # Localiza o primeiro .exe nos assets
        assets = data.get("assets", [])
        exe = next((a for a in assets if a["name"].lower().endswith(".exe")), None)
        if not exe:
            return None

        return {
            "versao":      tag,
            "url":         exe["browser_download_url"],
            "nome_arquivo": exe["name"],
            "notas":       (data.get("body") or "").strip(),
        }
    except (URLError, Exception):
        return None


def baixar_e_instalar(url: str, nome_arquivo: str, on_progress=None) -> bool:
    """
    Baixa o instalador e o executa em modo silencioso.
    Fecha o app após iniciar o instalador.

    on_progress: callable(float 0.0–1.0) chamado durante o download.
    Retorna True se o instalador foi iniciado com sucesso.
    """
    dest = os.path.join(tempfile.gettempdir(), nome_arquivo)

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "EfitecSolar-App"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            baixado = 0

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    baixado += len(chunk)
                    if on_progress and total:
                        on_progress(baixado / total)
    except Exception:
        return False

    # Valida que o download é um exe real (header MZ), não uma página HTML
    try:
        with open(dest, "rb") as f:
            if f.read(2) != b"MZ":
                return False
    except Exception:
        return False

    # Script .bat que espera o app fechar e abre o instalador visivelmente
    # (sem /SILENT para evitar bloqueio do Windows Defender / SmartScreen)
    bat = os.path.join(tempfile.gettempdir(), "efitec_update.bat")
    with open(bat, "w") as f:
        f.write(
            f'@echo off\n'
            f'timeout /t 6 /nobreak > nul\n'
            f'"{dest}"\n'
        )

    subprocess.Popen(["cmd", "/c", bat], creationflags=subprocess.CREATE_NO_WINDOW)
    return True
