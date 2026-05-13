# =============================================================
#  ui/screens/login_screen.py — Tela de Login
# =============================================================

import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from config import COLORS, APP_VERSION, ASSETS_DIR
from database import local_db
from services import auth_service

_BANNER_PATH = os.path.join(ASSETS_DIR, "banner_efitec.png")
_LOGO_PATH   = os.path.join(ASSETS_DIR, "logo_efitec2.png")


class LoginScreen(ctk.CTkFrame):
    """
    Tela de login com layout dividido:
    - Esquerda: banner com imagem e logo da empresa
    - Direita: formulário de login
    """

    def __init__(self, master, on_success, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._on_success = on_success

        self.grid_columnconfigure(0, weight=1)   # esquerda: metade
        self.grid_columnconfigure(1, weight=1)   # direita: metade
        self.grid_rowconfigure(0, weight=1)

        self._build_left()
        self._build_right()

        # Pré-carrega usuários do Supabase silenciosamente enquanto o usuário digita
        import threading
        threading.Thread(target=self._pre_sincronizar_usuarios, daemon=True).start()

    def _pre_sincronizar_usuarios(self):
        try:
            from services import supabase_client
            supabase_client.puxar_usuarios_do_supabase()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Painel esquerdo — banner + logo
    # ------------------------------------------------------------------

    def _build_left(self):
        left = ctk.CTkFrame(self, fg_color="#0A0C10", corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        canvas = tk.Canvas(left, bg="#0A0C10", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Redesenha ao redimensionar
        canvas.bind(
            "<Configure>",
            lambda e: self._desenhar_banner(canvas, e.width, e.height),
        )

    def _desenhar_banner(self, canvas: tk.Canvas, w: int, h: int):
        canvas.delete("all")

        # ---- Fundo: banner de painéis solares -----------------------
        try:
            img = Image.open(_BANNER_PATH).convert("RGBA")
            img = img.resize((w, h), Image.LANCZOS)

            # Overlay escuro para legibilidade
            overlay = Image.new("RGBA", (w, h), (10, 12, 18, 170))
            img = Image.alpha_composite(img, overlay)

            photo = ImageTk.PhotoImage(img)
            canvas._bg = photo          # mantém referência
            canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception:
            canvas.configure(bg="#0A0C10")

        # ---- Logo centralizado --------------------------------------
        logo_h = 60
        try:
            logo = Image.open(_LOGO_PATH).convert("RGBA")
            lw   = max(220, int(w * 0.52))
            lh   = int(lw * logo.height / logo.width)
            logo = logo.resize((lw, lh), Image.LANCZOS)

            logo_photo = ImageTk.PhotoImage(logo)
            canvas._logo = logo_photo   # mantém referência
            logo_h = lh

            logo_y = h // 2 - 18
            canvas.create_image(w // 2, logo_y, anchor="center", image=logo_photo)
        except Exception:
            canvas.create_text(
                w // 2, h // 2 - 18,
                text="EFITECSOLAR",
                fill=COLORS["accent"],
                font=("Segoe UI", 28, "bold"),
                anchor="center",
            )

        # ---- Tagline abaixo do logo ---------------------------------
        tag_y = h // 2 - 18 + logo_h // 2 + 18
        canvas.create_text(
            w // 2, tag_y,
            text="Gerenciador de Pastas",
            fill="#CCCCCC",
            font=("Segoe UI", 13),
            anchor="center",
        )

        # ---- Rodapé -------------------------------------------------
        canvas.create_text(
            w // 2, h - 18,
            text="© Efitecsolar — Energia Solar",
            fill="#666666",
            font=("Segoe UI", 9),
            anchor="center",
        )

    # ------------------------------------------------------------------
    # Painel direito — formulário
    # ------------------------------------------------------------------

    def _build_right(self):
        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        # Centraliza o card verticalmente
        card = ctk.CTkFrame(right, fg_color="transparent", width=360)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(
            card,
            text="Bem-vindo de volta 👋",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            card,
            text="Insira suas credenciais para continuar",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 32))

        _ent_kw = dict(
            height=44, corner_radius=10,
            border_color=COLORS["stroke"], fg_color=COLORS["card"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=ctk.CTkFont("Segoe UI", 13),
        )

        # E-mail
        ctk.CTkLabel(card, text="E-mail",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        self._email_var   = ctk.StringVar()
        self._email_entry = ctk.CTkEntry(
            card, textvariable=self._email_var,
            placeholder_text="seuemail@efitecsolar.com.br",
            **_ent_kw,
        )
        self._email_entry.grid(row=3, column=0, sticky="ew")

        # Senha
        ctk.CTkLabel(card, text="Senha",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=(20, 6))

        self._senha_var   = ctk.StringVar()
        self._senha_entry = ctk.CTkEntry(
            card, textvariable=self._senha_var,
            placeholder_text="••••••••", show="•",
            **_ent_kw,
        )
        self._senha_entry.grid(row=5, column=0, sticky="ew")

        # Mostrar senha
        self._show_senha = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            card, text="Mostrar senha",
            variable=self._show_senha,
            command=self._toggle_senha,
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            checkmark_color="white",
        ).grid(row=6, column=0, sticky="w", pady=(12, 0))

        # Mensagem de erro
        self._erro_lbl = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["danger"],
            anchor="w",
        )
        self._erro_lbl.grid(row=7, column=0, sticky="w", pady=(8, 0))

        # Botão Entrar
        self._btn_login = ctk.CTkButton(
            card, text="Entrar",
            height=48, corner_radius=12,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._confirmar_login,
        )
        self._btn_login.grid(row=8, column=0, sticky="ew", pady=(28, 0))

        # Versão
        ctk.CTkLabel(
            right, text=f"v{APP_VERSION}",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=COLORS["text_dim"],
        ).grid(row=1, column=0, sticky="se", padx=18, pady=(0, 14))

        # Binds
        self._senha_entry.bind("<Return>", lambda _: self._confirmar_login())
        self._email_entry.bind("<Return>", lambda _: self._senha_entry.focus())

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _toggle_senha(self):
        self._senha_entry.configure(show="" if self._show_senha.get() else "•")

    def _confirmar_login(self):
        email = self._email_var.get().strip().lower()
        senha = self._senha_var.get()

        if not email or not senha:
            self._erro_lbl.configure(text="Preencha e-mail e senha.")
            return

        self._btn_login.configure(state="disabled", text="Verificando...")
        self.update()

        ok, usuario = local_db.autenticar(email, senha)

        if not ok:
            # Usuário não encontrado localmente — tenta sincronizar do Supabase
            self._erro_lbl.configure(text="Verificando na nuvem...")
            self.update()
            try:
                from services import supabase_client
                supabase_client.puxar_usuarios_do_supabase()
                ok, usuario = local_db.autenticar(email, senha)
            except Exception:
                pass

        self._btn_login.configure(state="normal", text="Entrar")

        if not ok:
            self._erro_lbl.configure(text="E-mail ou senha incorretos.")
            self._senha_var.set("")
            self._senha_entry.focus()
            return

        self._erro_lbl.configure(text="")
        auth_service.salvar_sessao(usuario)
        self._on_success(usuario)
