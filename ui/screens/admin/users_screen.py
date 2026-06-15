# =============================================================
#  ui/screens/admin/users_screen.py — Gerenciar Usuários (ADM)
# =============================================================

import os
import shutil
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps

from config import COLORS, ASSETS_DIR
from database import local_db
from ui.components.sidebar import _avatar_circular, _avatar_iniciais


# ------------------------------------------------------------------
# Tela principal
# ------------------------------------------------------------------

class UsersScreen(ctk.CTkFrame):
    """Grade de cards de usuários com opções de criar, editar, ativar/desativar e excluir."""

    COLUNAS = 3

    def __init__(self, master, usuario: dict, on_navigate, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._usuario    = usuario
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_scroll()
        self._carregar()

    # ------------------------------------------------------------------
    # Topbar
    # ------------------------------------------------------------------

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))
        bar.grid_columnconfigure(1, weight=1)

        titulo_box = ctk.CTkFrame(bar, fg_color="transparent")
        titulo_box.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            titulo_box,
            text="👥  Gerenciar Usuários",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._subtitulo = ctk.CTkLabel(
            titulo_box, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._subtitulo.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            bar,
            text="+ Novo Usuário",
            height=38, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._abrir_modal_criar,
        ).grid(row=0, column=2, sticky="e")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=0, column=0, sticky="sew", padx=20)

    # ------------------------------------------------------------------
    # Scroll + grade
    # ------------------------------------------------------------------

    def _build_scroll(self):
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["stroke"],
            scrollbar_button_hover_color=COLORS["card_hover"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        for c in range(self.COLUNAS):
            self._scroll.grid_columnconfigure(c, weight=1, uniform="col")

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self):
        usuarios = local_db.listar_usuarios()
        ativos   = sum(1 for u in usuarios if u["ativo"])

        self._subtitulo.configure(
            text=f"{len(usuarios)} usuário{'s' if len(usuarios) != 1 else ''}  •  {ativos} ativo{'s' if ativos != 1 else ''}"
        )

        for w in self._scroll.winfo_children():
            w.destroy()

        for idx, u in enumerate(usuarios):
            row = idx // self.COLUNAS
            col = idx % self.COLUNAS
            self._build_card(row, col, u)

    # ------------------------------------------------------------------
    # Card de usuário
    # ------------------------------------------------------------------

    def _build_card(self, row: int, col: int, usuario: dict):
        ativo        = bool(usuario.get("ativo", 1))
        eh_adm_u    = usuario.get("tipo") == "ADM"
        cor_tipo    = COLORS["accent"] if eh_adm_u else COLORS["accent2"]
        cor_tipo_bg = "#2D1507" if eh_adm_u else "#071528"
        eh_eu       = usuario["id"] == self._usuario["id"]

        card = ctk.CTkFrame(
            self._scroll,
            fg_color=COLORS["card"] if ativo else "#16181F",
            corner_radius=12,
            border_width=1,
            border_color=COLORS["stroke"] if ativo else COLORS["text_dim"],
        )
        card.grid(row=row, column=col, padx=8, pady=6, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # ---- Seção superior: avatar + info (layout horizontal) ------
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        top.grid_columnconfigure(1, weight=1)

        img = (
            _avatar_circular(usuario.get("avatar_path"), 48)
            or _avatar_iniciais(usuario["nome"], 48)
        )
        if not ativo:
            img = _avatar_iniciais(usuario["nome"], 48)

        av_lbl = ctk.CTkLabel(top, image=img, text="")
        av_lbl.image = img
        av_lbl.grid(row=0, column=0, rowspan=3, padx=(0, 12))

        ctk.CTkLabel(
            top,
            text=usuario["nome"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=COLORS["text"] if ativo else COLORS["text_dim"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            top,
            text=usuario["email"],
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=COLORS["text_muted"] if ativo else COLORS["text_dim"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(1, 4))

        # Badges na linha de baixo
        badges = ctk.CTkFrame(top, fg_color="transparent")
        badges.grid(row=2, column=1, sticky="w")

        ctk.CTkLabel(
            badges,
            text=usuario.get("tipo", "Vendedor"),
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color=cor_tipo,
            fg_color=cor_tipo_bg,
            corner_radius=5,
            width=64, height=18,
        ).pack(side="left", padx=(0, 4))

        status_txt = "● Ativo" if ativo else "○ Inativo"
        cor_st     = COLORS["success"] if ativo else COLORS["text_dim"]
        ctk.CTkLabel(
            badges,
            text=status_txt,
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color=cor_st,
            fg_color=COLORS["stroke"],
            corner_radius=5,
            width=64, height=18,
        ).pack(side="left")

        # ---- Divisor ------------------------------------------------
        ctk.CTkFrame(card, height=1, fg_color=COLORS["stroke"]).grid(
            row=1, column=0, sticky="ew", padx=12, pady=(12, 0))

        # ---- Botões em linha completa --------------------------------
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 12))
        btns.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btns, text="✏️  Editar", height=30, corner_radius=8,
            fg_color=COLORS["stroke"], hover_color=COLORS["accent2"],
            text_color=COLORS["text_muted"], font=ctk.CTkFont("Segoe UI", 11),
            command=lambda u=usuario: self._abrir_modal_editar(u),
        ).grid(row=0, column=0, padx=(0, 3), sticky="ew")

        toggle_txt = "🔕  Desativar" if ativo else "✅  Ativar"
        ctk.CTkButton(
            btns, text=toggle_txt, height=30, corner_radius=8,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["warning"] if ativo else COLORS["success"],
            text_color=COLORS["text_muted"], font=ctk.CTkFont("Segoe UI", 11),
            state="disabled" if eh_eu else "normal",
            command=lambda u=usuario, a=ativo: self._toggle_ativo(u, a),
        ).grid(row=0, column=1, padx=3, sticky="ew")

        ctk.CTkButton(
            btns, text="🗑️", height=30, corner_radius=8,
            fg_color=COLORS["stroke"], hover_color=COLORS["danger"],
            text_color=COLORS["text_muted"], font=ctk.CTkFont("Segoe UI", 11),
            state="disabled" if eh_eu else "normal",
            command=lambda u=usuario: self._excluir(u),
        ).grid(row=0, column=2, padx=(3, 0), sticky="ew")

    # ------------------------------------------------------------------
    # Ações diretas
    # ------------------------------------------------------------------

    def _toggle_ativo(self, usuario: dict, ativo_atual: bool):
        novo = not ativo_atual
        acao = "ativar" if novo else "desativar"
        if not messagebox.askyesno(
            f"{'Ativar' if novo else 'Desativar'} Usuário",
            f"Deseja {acao} o acesso de '{usuario['nome']}'?",
        ):
            return
        local_db.atualizar_usuario(usuario["id"], ativo=novo)
        self._carregar()
        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass

    def _excluir(self, usuario: dict):
        if not messagebox.askyesno(
            "Excluir Usuário",
            f"Excluir permanentemente '{usuario['nome']}'?\n\n"
            "As pastas criadas por ele serão mantidas no banco.",
        ):
            return
        # Remove avatar do disco se existir
        if usuario.get("avatar_path") and os.path.exists(usuario["avatar_path"]):
            try:
                os.remove(usuario["avatar_path"])
            except Exception:
                pass
        local_db.atualizar_usuario(usuario["id"], ativo=0)   # soft-delete
        self._carregar()
        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Modais
    # ------------------------------------------------------------------

    def _abrir_modal_criar(self):
        ModalUsuario(self, usuario=None, on_salvar=self._carregar)

    def _abrir_modal_editar(self, usuario: dict):
        ModalUsuario(self, usuario=usuario, on_salvar=self._carregar)


# ------------------------------------------------------------------
# Modal criar / editar usuário
# ------------------------------------------------------------------

class ModalUsuario(ctk.CTkToplevel):
    """Modal para criar ou editar um usuário."""

    def __init__(self, master, usuario: dict | None, on_salvar, **kwargs):
        super().__init__(master, **kwargs)
        self._usuario_orig = usuario
        self._on_salvar    = on_salvar
        self._editando     = usuario is not None
        self._avatar_novo: str | None = None   # caminho temporário do novo avatar

        titulo = f"Editar — {usuario['nome']}" if self._editando else "Novo Usuário"
        self.title(titulo)
        self.geometry("420x580")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()

        self.update_idletasks()
        try:
            px = master.winfo_rootx() + (master.winfo_width()  - 420) // 2
            py = master.winfo_rooty() + (master.winfo_height() - 580) // 2
            self.geometry(f"420x580+{px}+{py}")
        except Exception:
            pass

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(padx=28, pady=20, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)

        u = self._usuario_orig or {}

        # ---- Cabeçalho + avatar -------------------------------------
        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        top.grid_columnconfigure(1, weight=1)

        # Avatar clicável
        self._av_img = (
            _avatar_circular(u.get("avatar_path"), 64)
            or _avatar_iniciais(u.get("nome", "?"), 64)
        )
        self._av_label = ctk.CTkLabel(top, image=self._av_img, text="",
                                      cursor="hand2")
        self._av_label.image = self._av_img
        self._av_label.grid(row=0, column=0, padx=(0, 16))
        self._av_label.bind("<Button-1>", lambda _: self._trocar_avatar())

        ctk.CTkLabel(top, text="Clique no avatar\npara alterar a foto",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["text_dim"], anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # ---- Campos -------------------------------------------------
        _ent_kw = dict(
            height=40, corner_radius=9,
            border_color=COLORS["stroke"], fg_color=COLORS["card"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=ctk.CTkFont("Segoe UI", 13),
        )

        def _label(row, txt):
            ctk.CTkLabel(outer, text=txt,
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=COLORS["text_muted"], anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(10, 3))

        self._nome_var  = ctk.StringVar(value=u.get("nome", ""))
        self._email_var = ctk.StringVar(value=u.get("email", ""))
        self._senha_var = ctk.StringVar()
        self._tipo_var  = ctk.StringVar(value=u.get("tipo", "Vendedor"))

        _label(1, "Nome completo")
        ctk.CTkEntry(outer, textvariable=self._nome_var,
                     placeholder_text="Ex: Carlos Silva", **_ent_kw,
        ).grid(row=2, column=0, sticky="ew")

        _label(3, "E-mail")
        ctk.CTkEntry(outer, textvariable=self._email_var,
                     placeholder_text="seuemail@efitecsolar.com.br", **_ent_kw,
        ).grid(row=4, column=0, sticky="ew")

        hint_senha = "Nova senha (deixe em branco para manter)" if self._editando else "Senha"
        _label(5, hint_senha)
        ctk.CTkEntry(outer, textvariable=self._senha_var,
                     placeholder_text="••••••••", show="•", **_ent_kw,
        ).grid(row=6, column=0, sticky="ew")

        _label(7, "Tipo de acesso")
        ctk.CTkSegmentedButton(
            outer,
            values=["Vendedor", "ADM"],
            variable=self._tipo_var,
            height=36, corner_radius=9,
            fg_color=COLORS["card"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["stroke"],
            unselected_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).grid(row=8, column=0, sticky="ew")

        # ---- Erro + botões ------------------------------------------
        self._erro = ctk.CTkLabel(outer, text="",
                                  font=ctk.CTkFont("Segoe UI", 11),
                                  text_color=COLORS["danger"], anchor="w",
                                  wraplength=360)
        self._erro.grid(row=9, column=0, sticky="w", pady=(8, 0))

        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.grid(row=10, column=0, sticky="ew", pady=(12, 0))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btns, text="Cancelar", height=40, corner_radius=9,
            fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        label_salvar = "Salvar Alterações" if self._editando else "Criar Usuário"
        ctk.CTkButton(
            btns, text=label_salvar, height=40, corner_radius=9,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._salvar,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.bind("<Return>", lambda _: self._salvar())

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

    def _trocar_avatar(self):
        path = filedialog.askopenfilename(
            title="Selecionar foto de perfil",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp")],
            parent=self,
        )
        if not path:
            return

        self._avatar_novo = path

        # Atualiza preview
        img = _avatar_circular(path, 64) or _avatar_iniciais(
            self._nome_var.get() or "?", 64)
        self._av_label.configure(image=img)
        self._av_label.image = img

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def _salvar(self):
        nome  = self._nome_var.get().strip()
        email = self._email_var.get().strip().lower()
        senha = self._senha_var.get()
        tipo  = self._tipo_var.get()

        if not nome:
            self._erro.configure(text="Nome é obrigatório.")
            return
        if not email or "@" not in email:
            self._erro.configure(text="E-mail inválido.")
            return
        if not self._editando and not senha:
            self._erro.configure(text="Senha é obrigatória para novo usuário.")
            return

        # Copia avatar novo para assets/avatars/
        avatar_path = self._usuario_orig.get("avatar_path") if self._editando else None
        if self._avatar_novo:
            try:
                os.makedirs(os.path.join(ASSETS_DIR, "avatars"), exist_ok=True)
                ext    = os.path.splitext(self._avatar_novo)[1].lower()
                dest   = os.path.join(
                    ASSETS_DIR, "avatars",
                    f"user_{self._usuario_orig['id'] if self._editando else 'new'}_{nome.replace(' ', '_')}{ext}"
                )
                shutil.copy2(self._avatar_novo, dest)
                avatar_path = dest
            except Exception as e:
                self._erro.configure(text=f"Erro ao salvar foto: {e}")
                return

        self._erro.configure(text="")

        try:
            if self._editando:
                kwargs: dict = {"nome": nome, "email": email, "tipo": tipo}
                if senha:
                    kwargs["senha"] = senha
                if avatar_path is not None:
                    kwargs["avatar_path"] = avatar_path
                local_db.atualizar_usuario(self._usuario_orig["id"], **kwargs)
            else:
                local_db.criar_usuario(nome, email, senha, tipo=tipo, avatar_path=avatar_path)
        except Exception as e:
            msg = str(e)
            if "UNIQUE" in msg:
                self._erro.configure(text="Este e-mail já está cadastrado.")
            else:
                self._erro.configure(text=f"Erro ao salvar: {msg}")
            return

        self.destroy()
        self._on_salvar()
        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass
