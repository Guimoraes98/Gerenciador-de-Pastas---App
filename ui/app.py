# =============================================================
#  ui/app.py — Janela principal + roteamento de telas
# =============================================================

import customtkinter as ctk
from config import (
    COLORS, WINDOW_WIDTH, WINDOW_HEIGHT,
    MIN_WIDTH, MIN_HEIGHT,
    APP_NAME, CTK_APPEARANCE, CTK_COLOR_THEME
)
from services import auth_service
from ui.components.sidebar import Sidebar

# Base com suporte a drag-and-drop (opcional — app funciona sem o pacote)
try:
    import tkinterdnd2 as _dnd
    _AppBase = type("_AppBase", (_dnd.DnDMixin, ctk.CTk), {})
except Exception:
    _AppBase = ctk.CTk

# Importação lazy das telas — retorna None para telas ainda não implementadas
def _load_screen(nome: str):
    try:
        if nome == "home":
            from ui.screens.home_screen import HomeScreen
            return HomeScreen
        if nome == "pastas":
            from ui.screens.folders_screen import FoldersScreen
            return FoldersScreen
        if nome == "status":
            from ui.screens.status_screen import StatusScreen
            return StatusScreen
        if nome == "sync":
            from ui.screens.sync_screen import SyncScreen
            return SyncScreen
        if nome == "sync":
            from ui.screens.sync_screen import SyncScreen
            return SyncScreen
        if nome == "drive":
            from ui.screens.drive_screen import DriveScreen
            return DriveScreen
        if nome == "usuarios":
            from ui.screens.admin.users_screen import UsersScreen
            return UsersScreen
    except ImportError:
        pass
    return None


class App(_AppBase):
    """Janela principal do aplicativo Efitecsolar."""

    def __init__(self):
        ctk.set_appearance_mode(CTK_APPEARANCE)
        ctk.set_default_color_theme(CTK_COLOR_THEME)
        super().__init__()

        # Inicializa tkdnd via _require do tkinterdnd2, que detecta a plataforma
        # (win-x64, win-x86, etc.) e adiciona o path correto ao auto_path do Tcl.
        try:
            from tkinterdnd2 import TkinterDnD as _TkDnD
            _TkDnD._require(self)
        except Exception:
            pass

        self.title(APP_NAME)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.configure(fg_color=COLORS["bg"])

        # Centraliza na tela
        self._centralizar()

        # Ícone (se disponível)
        try:
            from config import ASSETS_DIR
            import os
            ico = os.path.join(ASSETS_DIR, "icon.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            pass

        self._sidebar: Sidebar | None = None
        self._tela_atual: ctk.CTkFrame | None = None
        self._usuario: dict | None = None

        # Tenta retomar sessão anterior; só vai para o login se não houver
        sessao = auth_service.carregar_sessao()
        if sessao and self._validar_sessao(sessao):
            self._usuario = sessao
            self._mostrar_app_principal()
        else:
            auth_service.limpar_sessao()
            self._mostrar_login()

    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # Adapta ao tamanho da tela: até 92% da resolução, dentro dos limites configurados
        w = max(MIN_WIDTH,  min(WINDOW_WIDTH,  int(sw * 0.92)))
        h = max(MIN_HEIGHT, min(WINDOW_HEIGHT, int(sh * 0.92)))
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _validar_sessao(self, sessao: dict) -> bool:
        """Confirma que o usuário da sessão ainda existe e está ativo no banco."""
        from database import local_db
        try:
            usuario = local_db.get_usuario(sessao.get("id", -1))
            return usuario is not None and usuario.get("ativo", 0) == 1
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _mostrar_login(self):
        """Exibe a tela de login limpando tudo que existia."""
        self._limpar_tela()
        from ui.screens.login_screen import LoginScreen
        login = LoginScreen(self, on_success=self._apos_login)
        login.pack(fill="both", expand=True)

    def _apos_login(self, usuario: dict):
        """Callback chamado quando o login é bem-sucedido."""
        self._usuario = usuario
        self._mostrar_app_principal()

    # ------------------------------------------------------------------
    # App principal (pós-login)
    # ------------------------------------------------------------------

    def _mostrar_app_principal(self):
        """Monta o layout sidebar + área de conteúdo."""
        self._limpar_tela()

        # Layout: sidebar (fixo) + conteúdo (expande)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = Sidebar(
            self,
            usuario=self._usuario,
            on_navigate=self._navegar,
            on_logout=self._logout,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # Frame de conteúdo
        self._content_frame = ctk.CTkFrame(
            self, corner_radius=0, fg_color=COLORS["bg"]
        )
        self._content_frame.grid(row=0, column=1, sticky="nsew")
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._content_frame.grid_rowconfigure(0, weight=1)

        # Inicia sync automático em background
        from services.sync_manager import sync_manager
        sync_manager.iniciar(on_pull_done=lambda: self.after(0, self._refresh_tela_atual))

        # Verifica atualizações 8 segundos após o login
        self.after(8000, self._verificar_atualizacao)

        # Navega para a Home
        self._navegar("home")

    def _refresh_tela_atual(self):
        """Recarrega a tela atual após pull inicial completar."""
        tela = getattr(self, "_tela_atual_nome", "home")
        self._navegar(tela)

    def _navegar(self, tela: str):
        """Troca a tela de conteúdo."""
        self._tela_atual_nome = tela
        # Limpa conteúdo anterior
        for widget in self._content_frame.winfo_children():
            widget.destroy()

        # Sincroniza botão ativo na sidebar
        if self._sidebar:
            self._sidebar.set_tela_ativa(tela)

        # Instancia a nova tela
        ScreenClass = _load_screen(tela)
        if ScreenClass is None:
            # Tela ainda não implementada — placeholder
            _PlaceholderScreen(
                self._content_frame,
                nome=tela,
            ).grid(row=0, column=0, sticky="nsew")
            return

        screen = ScreenClass(
            self._content_frame,
            usuario=self._usuario,
            on_navigate=self._navegar,
        )
        screen.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def _verificar_atualizacao(self):
        def _worker():
            try:
                from services.updater import verificar_atualizacao
                release = verificar_atualizacao()
                if release:
                    self.after(0, lambda: self._mostrar_update(release))
                    return
            except Exception:
                pass
            # Sem atualização ou erro — tenta de novo em 30 minutos
            self.after(30 * 60 * 1000, self._verificar_atualizacao)
        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _mostrar_update(self, release: dict):
        from ui.components.update_dialog import UpdateDialog
        UpdateDialog(self, release=release)

    def _logout(self):
        from tkinter import messagebox
        if messagebox.askyesno("Sair", "Deseja realmente sair do sistema?"):
            from services.sync_manager import sync_manager
            sync_manager.parar()
            auth_service.limpar_sessao()
            self._usuario = None
            self._sidebar = None
            # Remove o grid layout do app principal
            for widget in self.winfo_children():
                widget.destroy()
            self.grid_columnconfigure(1, weight=0)
            self._mostrar_login()

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _limpar_tela(self):
        for widget in self.winfo_children():
            widget.destroy()
        # Reseta o grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)


# ------------------------------------------------------------------
# Placeholder para telas ainda não implementadas
# ------------------------------------------------------------------

class _PlaceholderScreen(ctk.CTkFrame):
    def __init__(self, master, nome: str, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        box = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16, width=360)
        box.grid(row=0, column=0)

        ctk.CTkLabel(
            box,
            text="🚧",
            font=ctk.CTkFont("Segoe UI", 48),
        ).pack(padx=48, pady=(40, 8))

        ctk.CTkLabel(
            box,
            text=f"Tela '{nome}' em construção",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=COLORS["text"],
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            box,
            text="Esta seção será implementada em breve.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        ).pack(pady=(0, 40))
