# =============================================================
#  services/sync_manager.py — Sync automático em background
# =============================================================
#
#  Comportamento:
#    - Loop a cada INTERVALO_SEGUNDOS (default 5 min):
#        1. Drive: processa a fila de upload (só se conectado)
#        2. Supabase: push de todos os registros pendentes
#    - push_supabase_agora(): dispara sync Supabase imediato (não bloqueia)
#    - sincronizar_tudo_agora(): força Drive + Supabase (usado pelo botão)
# =============================================================

import threading
import time

INTERVALO_SEGUNDOS = 300  # 5 minutos


class SyncManager:

    def __init__(self):
        self._rodando  = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def iniciar(self):
        if self._rodando:
            return
        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self._rodando = False

    def _loop(self):
        """Executa Drive + Supabase a cada INTERVALO_SEGUNDOS."""
        # Aguarda um pouco antes da primeira execução para o app terminar de carregar
        time.sleep(30)
        while self._rodando:
            self._sync_drive()
            self._sync_supabase()
            time.sleep(INTERVALO_SEGUNDOS)

    # ------------------------------------------------------------------
    # Sync Drive (processa sync_queue)
    # ------------------------------------------------------------------

    def _sync_drive(self):
        try:
            from services.drive_service import sincronizar_fila, esta_autenticado
            if esta_autenticado():
                sincronizar_fila()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Sync Supabase
    # ------------------------------------------------------------------

    def _sync_supabase(self):
        try:
            from services.supabase_client import sincronizar_tudo
            sincronizar_tudo()
        except Exception:
            pass

    def push_supabase_agora(self):
        """Dispara push Supabase imediato em background. Não bloqueia a UI."""
        threading.Thread(target=self._sync_supabase, daemon=True).start()

    # ------------------------------------------------------------------
    # Força sync completo (usado pelo botão "Sincronizar Agora")
    # ------------------------------------------------------------------

    def sincronizar_tudo_agora(self) -> tuple[dict, dict]:
        """
        Executa Drive + Supabase de forma bloqueante.
        Retorna (resultado_drive, resultado_supa).
        Deve ser chamado em uma thread separada.
        """
        res_drive = {"ok": 0, "erros": 0, "ignorados": 0}
        res_supa  = {"ok": 0, "erros": 0}

        try:
            from services.drive_service import sincronizar_fila, esta_autenticado
            if esta_autenticado():
                res_drive = sincronizar_fila()
        except Exception:
            pass

        try:
            from services.supabase_client import sincronizar_tudo
            res_supa = sincronizar_tudo()
        except Exception:
            pass

        return res_drive, res_supa


# Instância global — importada pelos módulos que precisam disparar sync
sync_manager = SyncManager()
