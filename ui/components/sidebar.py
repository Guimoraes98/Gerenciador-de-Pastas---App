# =============================================================
#  ui/components/sidebar.py — Sidebar de navegação
# =============================================================

import os
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps
from config import COLORS, SIDEBAR_WIDTH, APP_VERSION, ASSETS_DIR


def _avatar_circular(path: str | None, size: int = 72) -> ctk.CTkImage | None:
    """Carrega imagem, recorta em círculo e retorna CTkImage."""
    try:
        if path and os.path.exists(path):
            img = Image.open(path).convert("RGBA")
        else:
            # Avatar padrão: círculo com iniciais (gerado abaixo)
            return None

        img = ImageOps.fit(img, (size, size), method=Image.LANCZOS)

        # Máscara circular
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(img, mask=mask)

        return ctk.CTkImage(light_image=output, dark_image=output, size=(size, size))
    except Exception:
        return None


def _avatar_iniciais(nome: str, size: int = 72) -> ctk.CTkImage:
    """Gera avatar colorido com as iniciais do nome."""
    iniciais = "".join(p[0].upper() for p in nome.split()[:2]) if nome else "?"

    # Cor de fundo baseada no nome (determinística)
    cores_bg = ["#F97316", "#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444"]
    cor = cores_bg[sum(ord(c) for c in nome) % len(cores_bg)]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo circular
    draw.ellipse((0, 0, size, size), fill=cor)

    # Texto centralizado — usa fonte padrão do Pillow
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", size // 3)
    except Exception:
        font = None

    bbox  = draw.textbbox((0, 0), iniciais, font=font)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    tx    = (size - tw) // 2
    ty    = (size - th) // 2
    draw.text((tx, ty), iniciais, fill="white", font=font)

    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

class Sidebar(ctk.CTkFrame):
    """
    Sidebar lateral com:
    - Avatar + nome + tipo do usuário
    - Botões de navegação
    - Versão + botão de logout na base
    """

    # Mapeamento tela -> label, ícone unicode
    MENU_VENDEDOR = [
        ("home",      "🏠  Início"),
        ("pastas",    "📁  Minhas Pastas"),
        ("status",    "📋  Verificar Status"),
        ("sync",      "🔄  Sincronizar Pastas"),
        ("drive",     "☁️  Acessar Drive"),
    ]

    MENU_EXTRA_ADM = [
        ("usuarios",  "👥  Gerenciar Usuários"),
    ]

    def __init__(self, master, usuario: dict, on_navigate, on_logout, **kwargs):
        super().__init__(
            master,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            **kwargs
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)   # itens expandem horizontalmente
        self.grid_rowconfigure(3, weight=1)       # menu ocupa o espaço disponível

        self._usuario    = usuario
        self._on_navigate = on_navigate
        self._on_logout   = on_logout
        self._botoes: dict[str, ctk.CTkButton] = {}
        self._tela_ativa  = "home"

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        nome  = self._usuario.get("nome", "Usuário")
        tipo  = self._usuario.get("tipo", "Vendedor")
        avatar_path = self._usuario.get("avatar_path")

        # ---- Logo / Empresa ----------------------------------------
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 0))

        _logo_lbl = None
        try:
            _logo_path = os.path.join(ASSETS_DIR, "logo_efitec2.png")
            _img = Image.open(_logo_path).convert("RGBA")
            _lw  = 148
            _lh  = int(_lw * _img.height / _img.width)
            _img = _img.resize((_lw, _lh), Image.LANCZOS)
            _logo_ctk = ctk.CTkImage(light_image=_img, dark_image=_img, size=(_lw, _lh))
            _logo_lbl = ctk.CTkLabel(logo_frame, image=_logo_ctk, text="",
                                     fg_color="transparent")
            _logo_lbl.image = _logo_ctk
        except Exception:
            pass

        if _logo_lbl:
            _logo_lbl.pack(anchor="center")
        else:
            ctk.CTkLabel(
                logo_frame,
                text="☀  EFITECSOLAR",
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
                text_color=COLORS["accent"],
            ).pack(anchor="center")

        # ---- Divisor -----------------------------------------------
        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=1, column=0, sticky="ew", padx=16, pady=14
        )

        # ---- Perfil do usuário -------------------------------------
        perfil_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=12)
        perfil_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        perfil_frame.grid_columnconfigure(1, weight=1)

        # Avatar
        img = _avatar_circular(avatar_path, 48) or _avatar_iniciais(nome, 48)
        avatar_lbl = ctk.CTkLabel(perfil_frame, image=img, text="")
        avatar_lbl.image = img
        avatar_lbl.grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10)

        ctk.CTkLabel(
            perfil_frame,
            text=nome,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(10, 0), padx=(0, 8))

        cor_tipo = COLORS["accent"] if tipo == "ADM" else COLORS["accent2"]
        ctk.CTkLabel(
            perfil_frame,
            text=tipo,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=cor_tipo,
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 10), padx=(0, 8))

        # ---- Menu de navegação -------------------------------------
        menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        menu_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=8)
        menu_frame.grid_columnconfigure(0, weight=1)

        itens = list(self.MENU_VENDEDOR)
        if tipo == "ADM":
            itens += self.MENU_EXTRA_ADM

        for i, (tela, label) in enumerate(itens):
            btn = ctk.CTkButton(
                menu_frame,
                text=label,
                height=42,
                corner_radius=10,
                anchor="w",
                font=ctk.CTkFont("Segoe UI", 13),
                fg_color="transparent",
                text_color=COLORS["text_muted"],
                hover_color=COLORS["card_hover"],
                command=lambda t=tela: self._navegar(t),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self._botoes[tela] = btn

        # Destaca Home como ativo por padrão
        self._set_ativo("home")

        # ---- Rodapé (versão + logout) -------------------------------
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=4, column=0, sticky="sew", padx=14, pady=(8, 16))
        rodape.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            rodape,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=COLORS["text_dim"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkButton(
            rodape,
            text="⎋  Sair",
            height=36,
            corner_radius=10,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["danger"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._on_logout,
        ).grid(row=1, column=0, sticky="ew")

    # ------------------------------------------------------------------
    def _navegar(self, tela: str):
        self._set_ativo(tela)
        self._on_navigate(tela)

    def _set_ativo(self, tela: str):
        self._tela_ativa = tela
        for nome, btn in self._botoes.items():
            if nome == tela:
                btn.configure(
                    fg_color=COLORS["card_hover"],
                    text_color=COLORS["accent"],
                    font=ctk.CTkFont("Segoe UI", 13, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["text_muted"],
                    font=ctk.CTkFont("Segoe UI", 13),
                )

    def set_tela_ativa(self, tela: str):
        """Chamado externamente para sincronizar o estado dos botões."""
        self._set_ativo(tela)
