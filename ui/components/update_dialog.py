# =============================================================
#  ui/components/update_dialog.py — Dialog de atualização
# =============================================================

import os
import threading
import sys
import customtkinter as ctk

from config import COLORS, APP_VERSION, ASSETS_DIR


class UpdateDialog(ctk.CTkToplevel):
    """
    Dialog exibido quando uma nova versão está disponível.
    Mostra versão atual vs nova, notas de release e botões
    "Atualizar Agora" / "Mais Tarde".
    """

    def __init__(self, master, release: dict, **kwargs):
        super().__init__(master, **kwargs)
        self._release    = release
        self._baixando   = False

        self.title("Atualização disponível")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()

        try:
            _icon = os.path.join(ASSETS_DIR, "icon.ico")
            if os.path.exists(_icon):
                self.after(100, lambda: self.iconbitmap(_icon))
        except Exception:
            pass

        self.update_idletasks()
        px = master.winfo_rootx() + (master.winfo_width()  - 440) // 2
        py = master.winfo_rooty() + (master.winfo_height() - 360) // 2
        self.geometry(f"440x360+{px}+{py}")

        self._build()

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16)
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        card.grid_columnconfigure(0, weight=1)

        # Ícone
        ctk.CTkLabel(
            card, text="🚀",
            font=ctk.CTkFont("Segoe UI", 42),
        ).grid(row=0, column=0, pady=(24, 4))

        # Título
        ctk.CTkLabel(
            card,
            text="Nova versão disponível!",
            font=ctk.CTkFont("Segoe UI", 17, "bold"),
            text_color=COLORS["text"],
        ).grid(row=1, column=0)

        # Versões
        vers_frame = ctk.CTkFrame(card, fg_color=COLORS["bg"], corner_radius=8)
        vers_frame.grid(row=2, column=0, padx=24, pady=12, sticky="ew")
        vers_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            vers_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont("Segoe UI", 13),
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=0, padx=8, pady=10)

        ctk.CTkLabel(
            vers_frame, text="→",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            vers_frame,
            text=f"v{self._release['versao']}",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=COLORS["success"],
        ).grid(row=0, column=2, padx=8, pady=10)

        # Notas de release (se houver)
        notas = self._release.get("notas", "")
        if notas:
            txt = ctk.CTkTextbox(
                card, height=70, corner_radius=8,
                fg_color=COLORS["bg"],
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont("Segoe UI", 11),
                wrap="word",
            )
            txt.grid(row=3, column=0, padx=24, sticky="ew")
            txt.insert("0.0", notas[:400])
            txt.configure(state="disabled")

        # Barra de progresso (oculta inicialmente)
        self._progress = ctk.CTkProgressBar(
            card, corner_radius=4,
            progress_color=COLORS["accent"],
            fg_color=COLORS["stroke"],
        )
        self._progress.grid(row=4, column=0, padx=24, pady=(12, 0), sticky="ew")
        self._progress.set(0)
        self._progress.grid_remove()

        self._status_lbl = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=COLORS["text_muted"],
        )
        self._status_lbl.grid(row=5, column=0, pady=(4, 0))

        # Botões
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=6, column=0, padx=24, pady=(12, 24), sticky="ew")
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btns, text="Mais Tarde",
            height=40, corner_radius=10,
            fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 13),
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_update = ctk.CTkButton(
            btns, text="⬇  Atualizar Agora",
            height=40, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._iniciar_download,
        )
        self._btn_update.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # ------------------------------------------------------------------

    def _iniciar_download(self):
        if self._baixando:
            return
        self._baixando = True
        self._btn_update.configure(state="disabled", text="Baixando…")
        self._progress.grid()
        self._status_lbl.configure(text="Baixando atualização…")

        def _worker():
            from services.updater import baixar_e_instalar

            def _progresso(p: float):
                self.after(0, lambda: self._progress.set(p))
                pct = int(p * 100)
                self.after(0, lambda: self._status_lbl.configure(
                    text=f"Baixando… {pct}%"
                ))

            ok = baixar_e_instalar(
                self._release["url"],
                self._release["nome_arquivo"],
                on_progress=_progresso,
            )

            if ok:
                self.after(0, self._fechar_e_atualizar)
            else:
                self.after(0, self._erro_download)

        threading.Thread(target=_worker, daemon=True).start()

    def _fechar_e_atualizar(self):
        self._status_lbl.configure(
            text="Instalando… o app será reiniciado automaticamente.",
            text_color=COLORS["success"]
        )
        self.after(1500, lambda: sys.exit(0))

    def _erro_download(self):
        self._baixando = False
        self._progress.grid_remove()
        self._status_lbl.configure(
            text="Erro ao baixar. Tente novamente.", text_color=COLORS["danger"]
        )
        self._btn_update.configure(state="normal", text="⬇  Tentar Novamente")
