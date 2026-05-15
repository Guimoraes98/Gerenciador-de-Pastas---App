# =============================================================
#  ui/components/folder_card.py — Card individual de pasta
# =============================================================

import webbrowser
import customtkinter as ctk
from config import COLORS
from services.folder_service import abrir_pasta_local


class FolderCard(ctk.CTkFrame):
    """
    Card de uma pasta de cliente. Exibe dados resumidos e botões de ação.

    Parâmetros:
        pasta   — dict com os campos da tabela pastas
        on_delete(pasta_id) — callback para excluir
        on_refresh()        — callback para recarregar a grade após ações
    """

    def __init__(self, master, pasta: dict, on_delete, on_refresh, on_rename=None, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["stroke"],
            **kwargs,
        )
        self._pasta      = pasta
        self._on_delete  = on_delete
        self._on_refresh = on_refresh
        self._on_rename  = on_rename

        self._build()
        self._bind_hover()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        pasta = self._pasta
        status = pasta.get("status", "incompleta")
        cor_status  = COLORS["success"] if status == "completa" else COLORS["danger"]
        texto_status = "✓ Completa"     if status == "completa" else "✗ Incompleta"

        # ---- Cabeçalho: nome do cliente + badge de status --------
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=pasta.get("nome_cliente", "—"),
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text=texto_status,
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=cor_status,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        # ---- Linha divisória fina colorida -----------------------
        ctk.CTkFrame(self, height=2, fg_color=cor_status, corner_radius=1).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 8)
        )

        # ---- Bloco de infos --------------------------------------
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=2, column=0, sticky="ew", padx=16)
        info.grid_columnconfigure(1, weight=1)

        def _info_row(parent, row, icone, valor, cor=COLORS["text_muted"]):
            ctk.CTkLabel(
                parent,
                text=icone,
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=COLORS["text_dim"],
                width=18,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=1)
            ctk.CTkLabel(
                parent,
                text=str(valor) if valor else "—",
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=cor,
                anchor="w",
            ).grid(row=row, column=1, sticky="w", padx=(4, 0), pady=1)

        kwp_str  = f"{pasta.get('kwp', '')} kWp"
        cidade   = pasta.get("cidade", "—")
        vendedor = pasta.get("vendedor_nome", "—")
        sdr      = pasta.get("sdr") or "—"

        from config import MESES_PT
        mes  = pasta.get("mes", 1)
        ano  = pasta.get("ano", "")
        data_str = f"{MESES_PT[mes - 1]} / {ano}"

        _info_row(info, 0, "📍", f"{cidade}  •  {kwp_str}")
        _info_row(info, 1, "👤", f"Vendedor: {vendedor}")
        _info_row(info, 2, "🤝", f"SDR: {sdr}")
        _info_row(info, 3, "📅", data_str)

        # ---- Botões de ação --------------------------------------
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=12, pady=(10, 12))
        btns.grid_columnconfigure(0, weight=1)

        # Linha 0: botão principal — Documentos
        ctk.CTkButton(
            btns,
            text="📄  Documentos",
            height=34,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="white",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self._abrir_documentos,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        # Linha 1: ações secundárias (4 colunas)
        btns.grid_columnconfigure((0, 1, 2, 3), weight=1)

        id_crm = pasta.get("id_crm")

        ctk.CTkButton(
            btns,
            text="📂  Pasta",
            height=30,
            corner_radius=8,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 11),
            command=self._abrir_local,
        ).grid(row=1, column=0, padx=(0, 2), sticky="ew")

        ctk.CTkButton(
            btns,
            text="🌐  CRM",
            height=30,
            corner_radius=8,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["accent2"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 11),
            state="normal" if id_crm else "disabled",
            command=lambda: self._abrir_crm(id_crm),
        ).grid(row=1, column=1, padx=2, sticky="ew")

        ctk.CTkButton(
            btns,
            text="✏️",
            height=30,
            corner_radius=8,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["accent2"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 13),
            command=self._abrir_editor,
        ).grid(row=1, column=2, padx=2, sticky="ew")

        ctk.CTkButton(
            btns,
            text="🗑️",
            height=30,
            corner_radius=8,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["danger"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 13),
            command=self._confirmar_exclusao,
        ).grid(row=1, column=3, padx=(2, 0), sticky="ew")

    # ------------------------------------------------------------------
    def _bind_hover(self):
        """Efeito de highlight ao passar o mouse no card."""
        def _enter(_):
            self.configure(fg_color=COLORS["card_hover"], border_color=COLORS["accent"])
        def _leave(_):
            self.configure(fg_color=COLORS["card"], border_color=COLORS["stroke"])

        for w in self.winfo_children():
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
        self.bind("<Enter>", _enter)
        self.bind("<Leave>", _leave)

    # ------------------------------------------------------------------
    def _abrir_documentos(self):
        from ui.screens.document_modal import ModalDocumentos
        ModalDocumentos(self, pasta=self._pasta, on_close=self._on_refresh)

    def _abrir_local(self):
        caminho = self._pasta.get("caminho_local", "")
        if caminho:
            abrir_pasta_local(caminho)

    def _abrir_crm(self, id_crm):
        if id_crm:
            webbrowser.open(f"https://efitecsolar.groner.app/negocio/{id_crm}/contato")

    def _abrir_editor(self):
        if self._on_rename:
            self._on_rename(self._pasta)

    def _confirmar_exclusao(self):
        from tkinter import messagebox
        nome = self._pasta.get("nome_cliente", "este cliente")
        if messagebox.askyesno(
            "Excluir Pasta",
            f"Deseja excluir a pasta de '{nome}'?\n\nO diretório no disco NÃO será apagado.",
        ):
            self._on_delete(self._pasta["id"])
