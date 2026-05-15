# =============================================================
#  ui/screens/status_screen.py — Verificar Status das Pastas
# =============================================================

from datetime import datetime
import customtkinter as ctk

from config import COLORS, MESES_PT, DOCS_CONFIG
from database import local_db


class StatusScreen(ctk.CTkFrame):
    """
    Lista todas as pastas do mês com seus documentos presentes e faltando.
    ADM vê todas; Vendedor vê apenas as suas.
    """

    def __init__(self, master, usuario: dict, on_navigate, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._usuario    = usuario
        self._on_navigate = on_navigate
        self._eh_adm     = usuario.get("tipo") == "ADM"

        agora = datetime.now()
        self._mes_nome_var = ctk.StringVar(value=MESES_PT[agora.month - 1])
        self._ano_str_var  = ctk.StringVar(value=str(agora.year))

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
            text="📋  Verificar Status",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._subtitulo = ctk.CTkLabel(
            titulo_box, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._subtitulo.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctrl = ctk.CTkFrame(bar, fg_color="transparent")
        ctrl.grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(ctrl, text="Mês:", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_muted"]).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkOptionMenu(
            ctrl, variable=self._mes_nome_var, values=MESES_PT,
            width=110, corner_radius=8,
            fg_color=COLORS["card"], button_color=COLORS["stroke"],
            button_hover_color=COLORS["card_hover"], text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"], dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["card_hover"],
            command=lambda _: self._carregar(),
        ).grid(row=0, column=1, padx=(0, 10))

        anos = [str(a) for a in range(datetime.now().year, datetime.now().year - 4, -1)]
        ctk.CTkLabel(ctrl, text="Ano:", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_muted"]).grid(row=0, column=2, padx=(0, 4))

        ctk.CTkOptionMenu(
            ctrl, variable=self._ano_str_var, values=anos,
            width=80, corner_radius=8,
            fg_color=COLORS["card"], button_color=COLORS["stroke"],
            button_hover_color=COLORS["card_hover"], text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"], dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["card_hover"],
            command=lambda _: self._carregar(),
        ).grid(row=0, column=3)

        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=0, column=0, sticky="sew", padx=20)

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------

    def _build_scroll(self):
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["stroke"],
            scrollbar_button_hover_color=COLORS["card_hover"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        self._scroll.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self):
        try:
            local_db.recalcular_status_todas_pastas()
        except Exception:
            pass
        mes = MESES_PT.index(self._mes_nome_var.get()) + 1
        ano = int(self._ano_str_var.get())

        vendedor_id = None if self._eh_adm else self._usuario["id"]
        pastas = local_db.listar_pastas(vendedor_id=vendedor_id, mes=mes, ano=ano)

        completas   = sum(1 for p in pastas if p["status"] == "completa")
        incompletas = len(pastas) - completas
        mes_nome    = MESES_PT[mes - 1]

        self._subtitulo.configure(
            text=f"{mes_nome} {ano}  •  {len(pastas)} pasta{'s' if len(pastas) != 1 else ''}  "
                 f"•  {completas} completa{'s' if completas != 1 else ''}  "
                 f"•  {incompletas} incompleta{'s' if incompletas != 1 else ''}"
        )

        for w in self._scroll.winfo_children():
            w.destroy()

        if not pastas:
            self._mostrar_vazio(mes_nome, ano)
            return

        # Incompletas primeiro, depois completas
        ordenadas = sorted(pastas, key=lambda p: (p["status"] == "completa", p["nome_pasta"]))
        for idx, pasta in enumerate(ordenadas):
            self._build_row(idx, pasta)

    def _mostrar_vazio(self, mes_nome, ano):
        box = ctk.CTkFrame(self._scroll, fg_color="transparent")
        box.grid(row=0, column=0, pady=60)
        ctk.CTkLabel(box, text="📋", font=ctk.CTkFont("Segoe UI", 52),
                     text_color=COLORS["text_dim"]).pack()
        ctk.CTkLabel(box, text=f"Nenhuma pasta em {mes_nome} / {ano}",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(8, 4))

    # ------------------------------------------------------------------
    # Linha de pasta
    # ------------------------------------------------------------------

    def _build_row(self, idx: int, pasta: dict):
        completa   = pasta["status"] == "completa"
        cor_status = COLORS["success"] if completa else COLORS["danger"]
        bg_card    = COLORS["card"]

        card = ctk.CTkFrame(
            self._scroll, fg_color=bg_card,
            corner_radius=12, border_width=1,
            border_color=cor_status if not completa else COLORS["stroke"],
        )
        card.grid(row=idx, column=0, sticky="ew", padx=8, pady=4)
        card.grid_columnconfigure(1, weight=1)

        # ---- Barra lateral colorida ----------------------------------
        ctk.CTkFrame(card, width=4, fg_color=cor_status, corner_radius=2).grid(
            row=0, column=0, rowspan=3, sticky="ns", padx=(8, 12), pady=8)

        # ---- Cabeçalho da pasta -------------------------------------
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=1, sticky="ew", pady=(10, 2))
        hdr.grid_columnconfigure(0, weight=1)

        status_txt = "✓  Completa" if completa else "✗  Incompleta"
        ctk.CTkLabel(
            hdr, text=pasta["nome_pasta"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr, text=status_txt,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=cor_status, anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 12))

        # Sub-info (vendedor, se ADM)
        info_parts = []
        if self._eh_adm:
            info_parts.append(f"Vendedor: {pasta.get('vendedor_nome', '—')}")
        if pasta.get("sdr"):
            info_parts.append(f"SDR: {pasta['sdr']}")
        if info_parts:
            ctk.CTkLabel(
                hdr, text="  •  ".join(info_parts),
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=COLORS["text_muted"], anchor="w",
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))

        # ---- Chips de documentos ------------------------------------
        docs       = local_db.listar_documentos(pasta["id"])
        presentes  = {d["tipo"] for d in docs}
        todos      = list(DOCS_CONFIG.keys())
        faltando   = [t for t in todos if t not in presentes]

        CHIPS_POR_LINHA = 4

        chips_frame = ctk.CTkFrame(card, fg_color="transparent")
        chips_frame.grid(row=1, column=1, sticky="ew", pady=(0, 2))

        for i, tipo in enumerate(todos):
            ok       = tipo in presentes
            cor_chip = "#1C3327" if ok else "#2D1A1A"
            cor_txt  = COLORS["success"] if ok else COLORS["danger"]
            icone    = "✓" if ok else "✗"
            crow     = i // CHIPS_POR_LINHA
            ccol     = i % CHIPS_POR_LINHA

            chip = ctk.CTkFrame(chips_frame, fg_color=cor_chip, corner_radius=6, height=22)
            chip.grid(row=crow, column=ccol, padx=2, pady=2, sticky="w")
            chip.grid_propagate(False)
            chip.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(chip, text=icone,
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=cor_txt, width=14).grid(row=0, column=0, padx=(4, 1))

            nome_curto = tipo if len(tipo) <= 14 else tipo[:12] + "…"
            ctk.CTkLabel(chip, text=nome_curto,
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=cor_txt, anchor="w").grid(row=0, column=1, padx=(0, 6))

        # ---- Botão abrirdocs (só se incompleta) ---------------------
        if not completa:
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=2, column=1, sticky="e", padx=(0, 12), pady=(0, 10))

            ctk.CTkLabel(
                btn_frame,
                text=f"Faltando {len(faltando)} documento{'s' if len(faltando) != 1 else ''}",
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=COLORS["danger"],
            ).pack(side="left", padx=(0, 12))

            ctk.CTkButton(
                btn_frame,
                text="📄  Adicionar Documentos",
                height=30, corner_radius=8,
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                command=lambda p=pasta: self._abrir_docs(p),
            ).pack(side="left")
        else:
            ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=2, column=1)

    # ------------------------------------------------------------------

    def _abrir_docs(self, pasta: dict):
        from ui.screens.document_modal import ModalDocumentos
        ModalDocumentos(self, pasta=pasta, on_close=self._carregar)
