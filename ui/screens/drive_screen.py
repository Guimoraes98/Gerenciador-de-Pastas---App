# =============================================================
#  ui/screens/drive_screen.py — Acessar Google Drive no navegador
# =============================================================

import os
import webbrowser
import customtkinter as ctk

from config import COLORS, DRIVE_TOKEN, DRIVE_CREDS

_DRIVE_URL = "https://drive.google.com"


def _drive_conectado() -> bool:
    return os.path.exists(DRIVE_TOKEN)


class DriveScreen(ctk.CTkFrame):
    """
    Tela simples que abre o Google Drive no navegador padrão.
    Exibe status de conexão e botões de acesso rápido.
    """

    def __init__(self, master, usuario: dict, on_navigate, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._usuario     = usuario
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build()

    # ------------------------------------------------------------------

    def _build(self):
        # Centraliza o conteúdo
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)
        center.grid_columnconfigure(0, weight=1)

        # ---- Ícone grande -------------------------------------------
        ctk.CTkLabel(
            center, text="☁️",
            font=ctk.CTkFont("Segoe UI", 72),
            text_color=COLORS["accent2"],
        ).grid(row=0, column=0, pady=(0, 8))

        ctk.CTkLabel(
            center, text="Google Drive",
            font=ctk.CTkFont("Segoe UI", 26, "bold"),
            text_color=COLORS["text"],
        ).grid(row=1, column=0)

        # ---- Status de conexão --------------------------------------
        if _drive_conectado():
            cor_st  = COLORS["success"]
            txt_st  = "● Conta conectada"
            subtxt  = "Clique abaixo para abrir o Google Drive no navegador."
        else:
            cor_st  = COLORS["text_dim"]
            txt_st  = "○ Drive não conectado"
            subtxt  = "Conecte sua conta em 'Sincronizar Pastas' para integrar o Drive."

        ctk.CTkLabel(
            center, text=txt_st,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=cor_st,
        ).grid(row=2, column=0, pady=(12, 4))

        ctk.CTkLabel(
            center, text=subtxt,
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        ).grid(row=3, column=0, pady=(0, 28))

        # ---- Botões -------------------------------------------------
        btns = ctk.CTkFrame(center, fg_color="transparent")
        btns.grid(row=4, column=0)

        ctk.CTkButton(
            btns,
            text="🌐  Abrir Google Drive",
            width=220, height=48, corner_radius=12,
            fg_color=COLORS["accent2"], hover_color=COLORS["accent2_hover"],
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=lambda: webbrowser.open(_DRIVE_URL),
        ).pack(side="left", padx=6)

        if not _drive_conectado():
            ctk.CTkButton(
                btns,
                text="🔗  Conectar Drive",
                width=180, height=48, corner_radius=12,
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
                command=lambda: self._on_navigate("sync"),
            ).pack(side="left", padx=6)

        # ---- Card de dica -------------------------------------------
        dica = ctk.CTkFrame(
            center, fg_color=COLORS["card"],
            corner_radius=12, border_width=1,
            border_color=COLORS["stroke"],
            width=480,
        )
        dica.grid(row=5, column=0, pady=(36, 0))
        dica.grid_propagate(False)

        ctk.CTkLabel(
            dica,
            text="💡  Como funciona a sincronização",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(padx=24, pady=(18, 6), anchor="w")

        passos = [
            "1. Conecte sua conta Google em 'Sincronizar Pastas'",
            "2. O app cria automaticamente a estrutura de pastas no Drive",
            "3. Os documentos são enviados conforme são adicionados",
            "4. Use este botão para acessar os arquivos direto no navegador",
        ]
        for passo in passos:
            ctk.CTkLabel(
                dica, text=passo,
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(padx=24, pady=2, anchor="w")

        ctk.CTkFrame(dica, fg_color="transparent", height=16).pack()
