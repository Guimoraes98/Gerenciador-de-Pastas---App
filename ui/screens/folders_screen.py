# =============================================================
#  ui/screens/folders_screen.py — Tela "Minhas Pastas"
# =============================================================

from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

from config import COLORS, MESES_PT
from database import local_db
from services.folder_service import nova_pasta
from ui.components.folder_card import FolderCard


# ------------------------------------------------------------------
# Tela principal
# ------------------------------------------------------------------

class FoldersScreen(ctk.CTkFrame):
    """
    Tela de Minhas Pastas.
    - Filtro por mês/ano
    - Botão "+ Nova Pasta" → abre ModalNovaPasta
    - Grade 3 colunas de FolderCard
    """

    COLUNAS = 3

    def __init__(self, master, usuario: dict, on_navigate, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._usuario    = usuario
        self._on_navigate = on_navigate

        agora = datetime.now()
        self._mes_nome_var = ctk.StringVar(value=MESES_PT[agora.month - 1])
        self._ano_var = ctk.IntVar(value=agora.year)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_content()
        self._carregar_pastas()

    # ------------------------------------------------------------------
    # Topbar
    # ------------------------------------------------------------------

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))
        bar.grid_columnconfigure(1, weight=1)

        # ---- Título -------------------------------------------------
        titulo_box = ctk.CTkFrame(bar, fg_color="transparent")
        titulo_box.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            titulo_box,
            text="📁  Minhas Pastas",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._subtitulo = ctk.CTkLabel(
            titulo_box,
            text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._subtitulo.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ---- Filtros + botões ----------------------------------------
        controles = ctk.CTkFrame(bar, fg_color="transparent")
        controles.grid(row=0, column=2, sticky="e")

        # Mês
        ctk.CTkLabel(
            controles,
            text="Mês:",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkOptionMenu(
            controles,
            variable=self._mes_nome_var,
            values=MESES_PT,
            width=110,
            corner_radius=8,
            fg_color=COLORS["card"],
            button_color=COLORS["stroke"],
            button_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["card_hover"],
            command=lambda _: self._carregar_pastas(),
        ).grid(row=0, column=1, padx=(0, 10))

        # Ano
        ctk.CTkLabel(
            controles,
            text="Ano:",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=2, padx=(0, 4))

        anos = [str(a) for a in range(datetime.now().year, datetime.now().year - 4, -1)]
        self._ano_str_var = ctk.StringVar(value=str(self._ano_var.get()))
        ctk.CTkOptionMenu(
            controles,
            variable=self._ano_str_var,
            values=anos,
            width=80,
            corner_radius=8,
            fg_color=COLORS["card"],
            button_color=COLORS["stroke"],
            button_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["card_hover"],
            command=lambda _: self._carregar_pastas(),
        ).grid(row=0, column=3, padx=(0, 16))

        # Botão nova pasta
        ctk.CTkButton(
            controles,
            text="+ Nova Pasta",
            height=38,
            corner_radius=10,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._abrir_modal_nova_pasta,
        ).grid(row=0, column=4)

        # Divisor
        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=0, column=0, sticky="sew", padx=20, pady=(0, 0)
        )

    # ------------------------------------------------------------------
    # Área de conteúdo (scroll)
    # ------------------------------------------------------------------

    def _build_content(self):
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["stroke"],
            scrollbar_button_hover_color=COLORS["card_hover"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        for c in range(self.COLUNAS):
            self._scroll.grid_columnconfigure(c, weight=1, uniform="col")

    # ------------------------------------------------------------------
    # Carregar/renderizar cards
    # ------------------------------------------------------------------

    def _carregar_pastas(self):
        try:
            local_db.recalcular_status_todas_pastas()
        except Exception:
            pass
        mes = MESES_PT.index(self._mes_nome_var.get()) + 1
        ano = int(self._ano_str_var.get())
        self._ano_var.set(ano)

        eh_adm = self._usuario.get("tipo") == "ADM"
        vendedor_id = None if eh_adm else self._usuario["id"]

        pastas = local_db.listar_pastas(vendedor_id=vendedor_id, mes=mes, ano=ano)
        self._renderizar_cards(pastas, mes, ano)

    def _renderizar_cards(self, pastas: list, mes: int, ano: int):
        # Limpa a grade
        for w in self._scroll.winfo_children():
            w.destroy()

        mes_nome = MESES_PT[mes - 1]
        total    = len(pastas)
        completas = sum(1 for p in pastas if p.get("status") == "completa")

        self._subtitulo.configure(
            text=f"{mes_nome} {ano}  •  {total} pasta{'s' if total != 1 else ''}  •  {completas} completa{'s' if completas != 1 else ''}"
        )

        if not pastas:
            self._mostrar_vazio(mes_nome, ano)
            return

        for idx, pasta in enumerate(pastas):
            row = idx // self.COLUNAS
            col = idx % self.COLUNAS
            card = FolderCard(
                self._scroll,
                pasta=pasta,
                on_delete=self._excluir_pasta,
                on_refresh=self._carregar_pastas,
                on_rename=self._abrir_editor,
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    def _mostrar_vazio(self, mes_nome: str, ano: int):
        box = ctk.CTkFrame(self._scroll, fg_color="transparent")
        box.grid(row=0, column=0, columnspan=self.COLUNAS, pady=60)

        ctk.CTkLabel(
            box,
            text="📂",
            font=ctk.CTkFont("Segoe UI", 52),
            text_color=COLORS["text_dim"],
        ).pack()

        ctk.CTkLabel(
            box,
            text=f"Nenhuma pasta em {mes_nome} / {ano}",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(8, 4))

        ctk.CTkLabel(
            box,
            text="Clique em '+ Nova Pasta' para criar a primeira.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_dim"],
        ).pack()

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _excluir_pasta(self, pasta_id: int):
        local_db.excluir_pasta(pasta_id)
        self._carregar_pastas()
        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass

    def _abrir_editor(self, pasta: dict):
        ModalEditarPasta(self, pasta=pasta, on_success=self._carregar_pastas)

    def _abrir_modal_nova_pasta(self):
        ModalNovaPasta(self, usuario=self._usuario, on_success=self._apos_criar_pasta)

    def _apos_criar_pasta(self, pasta_id: int, caminho: str):
        self._carregar_pastas()
        messagebox.showinfo(
            "Pasta Criada",
            f"Pasta criada com sucesso!\n\n{caminho}",
        )
        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass


# ------------------------------------------------------------------
# Modal — Nova Pasta
# ------------------------------------------------------------------

class ModalNovaPasta(ctk.CTkToplevel):
    """
    Modal para criar nova pasta de cliente.
    Campos: nome_cliente, cidade, kwp, valor_venda (opt), sdr (opt), id_crm (opt)
    """

    def __init__(self, master, usuario: dict, on_success, **kwargs):
        super().__init__(master, **kwargs)
        self._usuario    = usuario
        self._on_success = on_success

        self.title("Nova Pasta de Cliente")
        self.geometry("480x780")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()  # modal

        # Centraliza sobre a janela pai
        self.update_idletasks()
        px = master.winfo_rootx() + (master.winfo_width()  - 480) // 2
        py = master.winfo_rooty() + (master.winfo_height() - 780) // 2
        self.geometry(f"480x780+{px}+{py}")

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        outer.grid_columnconfigure(0, weight=1)

        # ---- Cabeçalho -----------------------------------------------
        ctk.CTkLabel(
            outer,
            text="Nova Pasta",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            outer,
            text="Preencha os dados do cliente para criar a pasta.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        # ---- Formulário -----------------------------------------------
        form = ctk.CTkFrame(outer, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        def _label(parent, row, texto, obrigatorio=True):
            sufixo = "  *" if obrigatorio else "  (opcional)"
            cor_suf = COLORS["accent"] if obrigatorio else COLORS["text_dim"]
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.grid(row=row * 2, column=0, sticky="w", pady=(10, 2))
            ctk.CTkLabel(
                f,
                text=texto,
                font=ctk.CTkFont("Segoe UI", 12, "bold"),
                text_color=COLORS["text_muted"],
            ).pack(side="left")
            ctk.CTkLabel(
                f,
                text=sufixo,
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=cor_suf,
            ).pack(side="left")

        def _entry(parent, row, placeholder, **kw):
            e = ctk.CTkEntry(
                parent,
                placeholder_text=placeholder,
                height=40,
                corner_radius=9,
                border_color=COLORS["stroke"],
                fg_color=COLORS["card"],
                text_color=COLORS["text"],
                placeholder_text_color=COLORS["text_dim"],
                font=ctk.CTkFont("Segoe UI", 13),
                **kw,
            )
            e.grid(row=row * 2 + 1, column=0, sticky="ew")
            e.bind("<Return>", lambda _: self._confirmar())
            return e

        _label(form, 0, "Nome do Cliente")
        self._nome    = _entry(form, 0, "Ex: João da Silva")

        _label(form, 1, "Cidade")
        self._cidade  = _entry(form, 1, "Ex: Niterói")

        _label(form, 2, "KWp")
        self._kwp     = _entry(form, 2, "Ex: 7.35")

        # ---- Mês / Ano de Referência (row 3, layout manual dois campos) ----
        _label(form, 3, "Mês / Ano de Referência")

        _mes_ano_f = ctk.CTkFrame(form, fg_color="transparent")
        _mes_ano_f.grid(row=7, column=0, sticky="ew")   # row 3*2+1
        _mes_ano_f.grid_columnconfigure(0, weight=3)
        _mes_ano_f.grid_columnconfigure(1, weight=1)

        _agora = datetime.now()
        self._mes_var = ctk.StringVar(value=MESES_PT[_agora.month - 1])
        ctk.CTkOptionMenu(
            _mes_ano_f,
            variable=self._mes_var,
            values=MESES_PT,
            height=40, corner_radius=9,
            fg_color=COLORS["card"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["card_hover"],
            dropdown_text_color=COLORS["text"],
            font=ctk.CTkFont("Segoe UI", 13),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._ano_entry = ctk.CTkEntry(
            _mes_ano_f,
            height=40, corner_radius=9,
            border_color=COLORS["stroke"],
            fg_color=COLORS["card"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=ctk.CTkFont("Segoe UI", 13),
        )
        self._ano_entry.insert(0, str(_agora.year))
        self._ano_entry.grid(row=0, column=1, sticky="ew")
        self._ano_entry.bind("<Return>", lambda _: self._confirmar())

        _label(form, 4, "Valor da Venda (R$)", obrigatorio=False)
        self._valor   = _entry(form, 4, "Ex: 28000.00")

        _label(form, 5, "SDR Responsável", obrigatorio=False)
        self._sdr     = _entry(form, 5, "Nome do SDR")

        _label(form, 6, "ID CRM", obrigatorio=False)
        self._id_crm  = _entry(form, 6, "Número do negócio no CRM")

        # ---- Mensagem de erro ----------------------------------------
        self._erro_lbl = ctk.CTkLabel(
            outer,
            text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["danger"],
            anchor="w",
            wraplength=420,
        )
        self._erro_lbl.grid(row=3, column=0, sticky="w", pady=(8, 0))

        # ---- Botões --------------------------------------------------
        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btns,
            text="Cancelar",
            height=42,
            corner_radius=10,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 13),
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_criar = ctk.CTkButton(
            btns,
            text="Criar Pasta",
            height=42,
            corner_radius=10,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._confirmar,
        )
        self._btn_criar.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # Enter confirma
        self.bind("<Return>", lambda _: self._confirmar())

    # ------------------------------------------------------------------
    def _set_erro(self, msg: str):
        self._erro_lbl.configure(text=msg)

    def _confirmar(self):
        nome      = self._nome.get().strip()
        cidade    = self._cidade.get().strip()
        kwp_str   = self._kwp.get().strip().replace(",", ".")
        valor_str = self._valor.get().strip().replace(",", ".")
        sdr       = self._sdr.get().strip() or None
        id_crm    = self._id_crm.get().strip() or None
        mes_nome  = self._mes_var.get()
        ano_str   = self._ano_entry.get().strip()

        # Validação
        if not nome:
            self._set_erro("Nome do cliente é obrigatório.")
            self._nome.focus()
            return
        if not cidade:
            self._set_erro("Cidade é obrigatória.")
            self._cidade.focus()
            return
        if not kwp_str:
            self._set_erro("KWp é obrigatório.")
            self._kwp.focus()
            return
        try:
            kwp = float(kwp_str)
            if kwp <= 0:
                raise ValueError
        except ValueError:
            self._set_erro("KWp deve ser um número positivo (ex: 7.35).")
            self._kwp.focus()
            return

        try:
            ano = int(ano_str)
            if ano < 2020 or ano > 2099:
                raise ValueError
        except ValueError:
            self._set_erro("Ano inválido (ex: 2025).")
            self._ano_entry.focus()
            return

        mes = MESES_PT.index(mes_nome) + 1

        valor = None
        if valor_str:
            try:
                valor = float(valor_str)
            except ValueError:
                self._set_erro("Valor da venda deve ser um número (ex: 28000.00).")
                self._valor.focus()
                return

        self._set_erro("")
        self._btn_criar.configure(state="disabled", text="Criando...")
        self.update()

        dados = {
            "nome_cliente":  nome,
            "cidade":        cidade,
            "kwp":           kwp,
            "valor_venda":   valor,
            "sdr":           sdr,
            "id_crm":        id_crm,
            "mes":           mes,
            "ano":           ano,
            "vendedor_id":   self._usuario["id"],
            "vendedor_nome": self._usuario["nome"],
        }

        try:
            ok, pasta_id, resultado = nova_pasta(dados)
        except Exception as e:
            self._btn_criar.configure(state="normal", text="Criar Pasta")
            self._set_erro(f"Erro inesperado: {e}")
            return

        self._btn_criar.configure(state="normal", text="Criar Pasta")

        if not ok:
            self._set_erro(resultado)
            return

        self.destroy()
        self._on_success(pasta_id, resultado)


# ------------------------------------------------------------------
# Modal — Editar Pasta
# ------------------------------------------------------------------

class ModalEditarPasta(ctk.CTkToplevel):
    """Modal para editar dados de uma pasta já existente (não move o diretório)."""

    def __init__(self, master, pasta: dict, on_success, **kwargs):
        super().__init__(master, **kwargs)
        self._pasta      = pasta
        self._on_success = on_success

        self.title("Editar Pasta")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()

        self.update_idletasks()
        px = master.winfo_rootx() + (master.winfo_width()  - 480) // 2
        py = master.winfo_rooty() + (master.winfo_height() - 560) // 2
        self.geometry(f"480x560+{px}+{py}")

        self._build()

        try:
            from config import ASSETS_DIR
            import os as _os
            _ico = _os.path.join(ASSETS_DIR, "icon.ico")
            if _os.path.exists(_ico):
                self.after(200, lambda: self.iconbitmap(_ico))
        except Exception:
            pass

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        outer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            outer,
            text="Editar Pasta",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            outer,
            text="Altere os dados da pasta. O diretório no disco não será renomeado.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=420,
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        form = ctk.CTkFrame(outer, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        _entry_kw = dict(
            height=40, corner_radius=9,
            border_color=COLORS["stroke"],
            fg_color=COLORS["card"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=ctk.CTkFont("Segoe UI", 13),
        )

        def _lbl(row, texto, opt=False):
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.grid(row=row * 2, column=0, sticky="w", pady=(10, 2))
            ctk.CTkLabel(f, text=texto,
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=COLORS["text_muted"]).pack(side="left")
            if opt:
                ctk.CTkLabel(f, text="  (opcional)",
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=COLORS["text_dim"]).pack(side="left")

        def _inp(row, val=""):
            e = ctk.CTkEntry(form, **_entry_kw)
            e.grid(row=row * 2 + 1, column=0, sticky="ew")
            if val:
                e.insert(0, str(val))
            return e

        _lbl(0, "Nome do Cliente")
        self._nome   = _inp(0, self._pasta.get("nome_cliente", ""))

        _lbl(1, "Cidade")
        self._cidade = _inp(1, self._pasta.get("cidade", ""))

        _lbl(2, "KWp")
        self._kwp    = _inp(2, self._pasta.get("kwp", ""))

        _lbl(3, "Valor da Venda (R$)", opt=True)
        self._valor  = _inp(3, self._pasta.get("valor_venda") or "")

        _lbl(4, "SDR Responsável", opt=True)
        self._sdr    = _inp(4, self._pasta.get("sdr") or "")

        _lbl(5, "ID CRM", opt=True)
        self._id_crm = _inp(5, self._pasta.get("id_crm") or "")

        self._erro_lbl = ctk.CTkLabel(
            outer, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["danger"],
            anchor="w", wraplength=420,
        )
        self._erro_lbl.grid(row=3, column=0, sticky="w", pady=(8, 0))

        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btns, text="Cancelar", height=42, corner_radius=10,
            fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 13),
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_salvar = ctk.CTkButton(
            btns, text="Salvar", height=42, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._confirmar,
        )
        self._btn_salvar.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.bind("<Return>", lambda _: self._confirmar())

    def _confirmar(self):
        nome      = self._nome.get().strip()
        cidade    = self._cidade.get().strip()
        kwp_str   = self._kwp.get().strip().replace(",", ".")
        valor_str = self._valor.get().strip().replace(",", ".")
        sdr       = self._sdr.get().strip() or None
        id_crm    = self._id_crm.get().strip() or None

        if not nome:
            self._erro_lbl.configure(text="Nome do cliente é obrigatório.")
            return
        if not cidade:
            self._erro_lbl.configure(text="Cidade é obrigatória.")
            return
        try:
            kwp = float(kwp_str)
            if kwp <= 0:
                raise ValueError
        except ValueError:
            self._erro_lbl.configure(text="KWp deve ser um número positivo (ex: 7.35).")
            return

        valor = None
        if valor_str:
            try:
                valor = float(valor_str)
            except ValueError:
                self._erro_lbl.configure(text="Valor da venda inválido (ex: 28000.00).")
                return

        from services.folder_service import gerar_nome_pasta
        novo_nome_pasta = gerar_nome_pasta(
            nome, cidade, kwp, self._pasta.get("vendedor_nome", "")
        )

        campos = {
            "nome_cliente": nome,
            "cidade":       cidade,
            "kwp":          kwp,
            "valor_venda":  valor,
            "sdr":          sdr,
            "id_crm":       id_crm,
            "nome_pasta":   novo_nome_pasta,
        }

        self._btn_salvar.configure(state="disabled", text="Salvando…")
        self.update()

        local_db.atualizar_pasta(self._pasta["id"], campos)

        try:
            from services.sync_manager import sync_manager
            sync_manager.push_supabase_agora()
        except Exception:
            pass

        self.destroy()
        self._on_success()
