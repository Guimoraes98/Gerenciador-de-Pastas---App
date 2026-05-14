# =============================================================
#  ui/screens/document_modal.py — Modal de Documentos da Pasta
# =============================================================

import os
import re
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import COLORS, DOCS_CONFIG
from database import local_db
from services.document_service import (
    adicionar_doc_a_pasta,
    substituir_doc,
    sugerir_tipo,
)

try:
    import tkinterdnd2 as _dnd
    DND_FILES = _dnd.DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

_TIPOS = list(DOCS_CONFIG.keys())

# Nomes curtos para exibição nos chips de status
_TIPO_CURTO = {
    "CNH":                   "CNH",
    "Conta de Luz":          "Conta de Luz",
    "Contrato":              "Contrato",
    "Proposta Comercial":    "Proposta Com.",
    "Procuração":            "Procuração",
    "Projeto 2D":            "Projeto 2D",
    "Lista de Equipamento":  "Lista Equip.",
    "Checklist":             "Checklist",
    "Pagamento Serviço":     "Pag. Serviço",
    "Pagamento Equipamento": "Pag. Equip.",
}


def _parse_drop(data: str) -> list[str]:
    paths = re.findall(r"\{[^}]+\}|\S+", data)
    return [p.strip("{}") for p in paths if p.strip("{}")]


# ------------------------------------------------------------------
# Modal principal
# ------------------------------------------------------------------

class ModalDocumentos(ctk.CTkToplevel):
    """
    Fluxo:
    1. Usuário vê quais docs já estão presentes/faltando (chips de status)
    2. Arrasta N arquivos (ou clica em Selecionar) → entram na fila
    3. Para cada arquivo da fila: ajusta Tipo e Subtipo se necessário
    4. Clica em Confirmar → todos são copiados/renomeados na pasta
    """

    WIDTH  = 740
    HEIGHT = 700

    def __init__(self, master, pasta: dict, on_close=None, **kwargs):
        super().__init__(master, **kwargs)
        self._pasta    = pasta
        self._on_close = on_close
        self._fila: list[dict] = []   # [{caminho, nome_original, tipo_var, subtipo_var, obs_var}]

        self.title(f"Documentos — {pasta.get('nome_pasta', '')}")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(640, 580)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._centralizar(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)   # fila expande

        # Limpa registros de arquivos deletados manualmente do disco
        self._sincronizar_com_disco()

        self._build_header()   # row 0
        self._build_status()   # row 1
        self._build_dropzone() # row 2
        self._build_fila()     # row 3
        self._build_footer()   # row 4

        self.protocol("WM_DELETE_WINDOW", self._fechar)

    # ------------------------------------------------------------------
    def _centralizar(self, master):
        self.update_idletasks()
        try:
            px = master.winfo_rootx() + (master.winfo_width()  - self.WIDTH)  // 2
            py = master.winfo_rooty() + (master.winfo_height() - self.HEIGHT) // 2
            self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{px}+{py}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.grid(sticky="ew", padx=24, pady=14)
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            inner,
            text=f"📄  {self._pasta.get('nome_cliente', '')}",
            font=ctk.CTkFont("Segoe UI", 17, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            inner,
            text=self._pasta.get("nome_pasta", ""),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(1, 6))

        self._progresso_lbl = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=COLORS["text_muted"],
            anchor="e",
        )
        self._progresso_lbl.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

        self._progress_bar = ctk.CTkProgressBar(
            inner, height=6, corner_radius=3,
            fg_color=COLORS["stroke"],
            progress_color=COLORS["success"],
        )
        self._progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        self._atualizar_progresso()

    # ------------------------------------------------------------------
    # Chips de status dos 11 tipos
    # ------------------------------------------------------------------

    def _build_status(self):
        wrap = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        for c in range(4):
            wrap.grid_columnconfigure(c, weight=1)

        self._status_frame = wrap
        self._renderizar_chips()

    def _renderizar_chips(self):
        for w in self._status_frame.winfo_children():
            w.destroy()

        docs = local_db.listar_documentos(self._pasta["id"])
        # dict tipo → doc para chips clicáveis (substituição)
        tipos_presentes = {d["tipo"]: d for d in docs}

        for idx, tipo in enumerate(_TIPOS):
            doc_existente = tipos_presentes.get(tipo)
            presente      = doc_existente is not None
            row = idx // 4
            col = idx % 4

            cor_bg    = "#1C3327" if presente else "#2D1A1A"
            cor_text  = COLORS["success"] if presente else COLORS["danger"]
            icone     = "✓" if presente else "✗"
            nome_curto = _TIPO_CURTO.get(tipo, tipo)
            cursor    = "hand2" if presente else ""

            chip = ctk.CTkFrame(
                self._status_frame,
                fg_color=cor_bg,
                corner_radius=8,
                height=28,
                cursor=cursor,
            )
            chip.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            chip.grid_columnconfigure(1, weight=1)
            chip.grid_propagate(False)

            lbl_ico = ctk.CTkLabel(
                chip,
                text=icone,
                font=ctk.CTkFont("Segoe UI", 10, "bold"),
                text_color=cor_text,
                width=18,
                cursor=cursor,
            )
            lbl_ico.grid(row=0, column=0, padx=(6, 2))

            lbl_nome = ctk.CTkLabel(
                chip,
                text=nome_curto,
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=cor_text,
                anchor="w",
                cursor=cursor,
            )
            lbl_nome.grid(row=0, column=1, sticky="w", padx=(0, 4))

            # Chips verdes são clicáveis para substituir o documento
            if presente:
                def _hl_on(_e, c=chip):
                    c.configure(border_width=1, border_color=COLORS["warning"])
                def _hl_off(_e, c=chip):
                    c.configure(border_width=0)
                def _click(_e, t=tipo, d=doc_existente):
                    self._substituir_chip(t, d)

                for widget in (chip, lbl_ico, lbl_nome):
                    widget.bind("<Enter>",    _hl_on)
                    widget.bind("<Leave>",    _hl_off)
                    widget.bind("<Button-1>", _click)

    # ------------------------------------------------------------------
    # Sincronização com o disco (remove registros de arquivos deletados)
    # ------------------------------------------------------------------

    def _sincronizar_com_disco(self):
        """
        Verifica cada documento registrado no banco.
        Se o arquivo não existir mais no disco, remove o registro
        e recalcula o status da pasta.
        """
        docs = local_db.listar_documentos(self._pasta["id"])
        removidos = 0
        for d in docs:
            caminho = d.get("caminho_local")
            if caminho and not os.path.exists(caminho):
                local_db.excluir_documento(d["id"])
                removidos += 1
        if removidos:
            local_db.calcular_status_pasta(self._pasta["id"])
            self._pasta = local_db.get_pasta(self._pasta["id"])

    # ------------------------------------------------------------------
    # Substituição via chip clicável
    # ------------------------------------------------------------------

    def _substituir_chip(self, tipo: str, doc: dict):
        """Fluxo de substituição de um documento já enviado."""
        subtipo       = doc.get("subtipo")
        label_subtipo = f" – {subtipo}" if subtipo else ""

        path = filedialog.askopenfilename(
            title=f"Substituir: {tipo}{label_subtipo}",
            filetypes=[
                ("Documentos", "*.pdf *.jpg *.jpeg *.png *.docx *.doc *.xlsx"),
                ("Todos os arquivos", "*.*"),
            ],
            parent=self,
        )
        if not path:
            return

        nome = os.path.basename(path)

        if not messagebox.askyesno(
            "Confirmar substituição",
            f"Substituir  '{tipo}{label_subtipo}'\n\n"
            f"Arquivo atual:  {doc.get('nome_final', '—')}\n"
            f"Novo arquivo:   {nome}\n\n"
            "Esta ação não pode ser desfeita.",
            parent=self,
        ):
            return

        caminho_pasta = self._pasta.get("caminho_local", "")
        if not caminho_pasta or not os.path.isdir(caminho_pasta):
            messagebox.showerror(
                "Pasta não encontrada",
                f"O diretório da pasta não existe no disco:\n{caminho_pasta}",
                parent=self,
            )
            return

        ok, _, erro = substituir_doc(
            self._pasta["id"], path, tipo, subtipo, caminho_pasta
        )
        if not ok:
            messagebox.showerror("Erro ao substituir", erro, parent=self)
            return

        self._pasta = local_db.get_pasta(self._pasta["id"])
        self._atualizar_progresso()
        self._renderizar_chips()

    # ------------------------------------------------------------------
    # Drop zone
    # ------------------------------------------------------------------

    def _build_dropzone(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 0))
        outer.grid_columnconfigure(0, weight=1)

        zone = ctk.CTkFrame(
            outer,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=2,
            border_color=COLORS["stroke"],
            height=72,
        )
        zone.grid(row=0, column=0, sticky="ew")
        zone.grid_columnconfigure(0, weight=1)
        zone.grid_propagate(False)

        # Texto central
        txt_frame = ctk.CTkFrame(zone, fg_color="transparent")
        txt_frame.place(relx=0.5, rely=0.5, anchor="center")

        if HAS_DND:
            ctk.CTkLabel(
                txt_frame,
                text="📂  Arraste os arquivos aqui",
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
                text_color=COLORS["text_muted"],
            ).pack(side="left", padx=(0, 12))
            ctk.CTkLabel(
                txt_frame,
                text="ou",
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=COLORS["text_dim"],
            ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            txt_frame,
            text="📎  Selecionar arquivos",
            height=34,
            corner_radius=9,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._selecionar_arquivos,
        ).pack(side="left")

        # Hover visual
        def _hl_on(_):
            zone.configure(border_color=COLORS["accent"])
        def _hl_off(_):
            zone.configure(border_color=COLORS["stroke"])

        zone.bind("<Enter>", _hl_on)
        zone.bind("<Leave>", _hl_off)

        # Drag & drop
        if HAS_DND:
            try:
                zone.drop_target_register(DND_FILES)
                zone.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        self._drop_zone = zone

    # ------------------------------------------------------------------
    # Fila de arquivos pendentes
    # ------------------------------------------------------------------

    def _build_fila(self):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 0))
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        # Título da fila (só aparece quando há itens)
        self._fila_titulo = ctk.CTkLabel(
            wrap,
            text="",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._fila_titulo.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._scroll_fila = ctk.CTkScrollableFrame(
            wrap,
            fg_color="transparent",
            scrollbar_button_color=COLORS["stroke"],
            scrollbar_button_hover_color=COLORS["card_hover"],
        )
        self._scroll_fila.grid(row=1, column=0, sticky="nsew")
        self._scroll_fila.grid_columnconfigure(0, weight=1)

    def _renderizar_fila(self):
        for w in self._scroll_fila.winfo_children():
            w.destroy()

        n = len(self._fila)
        self._fila_titulo.configure(
            text=f"Fila de envio — {n} arquivo{'s' if n != 1 else ''}" if n else ""
        )

        for idx, item in enumerate(self._fila):
            self._build_item_fila(idx, item)

        self._btn_confirmar.configure(
            text=f"✓  Confirmar envio  ({n})" if n else "✓  Confirmar envio",
            state="normal" if n else "disabled",
        )

    def _build_item_fila(self, idx: int, item: dict):
        from services.document_service import gerar_nome_final

        ROW_H = 54
        PAD_Y = (ROW_H - 30) // 2   # centraliza widgets de height=30

        row_frame = ctk.CTkFrame(
            self._scroll_fila,
            fg_color=COLORS["card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["stroke"],
            height=ROW_H,
        )
        row_frame.grid(row=idx, column=0, sticky="ew", pady=3)
        row_frame.grid_propagate(False)
        # col 0: nome original | col 1: tipo | col 2: subtipo | col 3: preview | col 4: remover
        row_frame.grid_columnconfigure(3, weight=1)

        ext = os.path.splitext(item["nome_original"])[1].lower() or ".pdf"

        # ---- Col 0: nome original -----------------------------------
        nome_orig = item["nome_original"]
        nome_curto = nome_orig if len(nome_orig) <= 22 else nome_orig[:19] + "…"
        ctk.CTkLabel(
            row_frame,
            text=f"📎  {nome_curto}",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=COLORS["text_muted"],
            anchor="w",
            width=175,
        ).grid(row=0, column=0, padx=(10, 4), pady=PAD_Y, sticky="w")

        # ---- Col 1: tipo --------------------------------------------
        _opt_kw = dict(
            height=30, corner_radius=8,
            fg_color=COLORS["bg"],
            button_color=COLORS["stroke"],
            button_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["card_hover"],
            font=ctk.CTkFont("Segoe UI", 11),
            dropdown_font=ctk.CTkFont("Segoe UI", 11),
        )

        tipo_menu = ctk.CTkOptionMenu(
            row_frame, variable=item["tipo_var"],
            values=_TIPOS, width=155, **_opt_kw,
        )
        tipo_menu.grid(row=0, column=1, padx=4, pady=PAD_Y)

        # ---- Col 2: subtipo + obs (frame fixo, mais largo para caber os dois) ----
        sub_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=235, height=30)
        sub_frame.grid(row=0, column=2, padx=4, pady=PAD_Y)
        sub_frame.grid_propagate(False)

        # ---- Col 3: preview do nome final ---------------------------
        preview_var = ctk.StringVar()
        ctk.CTkLabel(
            row_frame,
            textvariable=preview_var,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=COLORS["accent2"],
            anchor="w",
        ).grid(row=0, column=3, padx=(4, 4), pady=PAD_Y, sticky="ew")

        # ---- Col 4: remover -----------------------------------------
        ctk.CTkButton(
            row_frame,
            text="✕", width=30, height=30, corner_radius=8,
            fg_color="transparent", hover_color=COLORS["danger"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=lambda i=idx: self._remover_da_fila(i),
        ).grid(row=0, column=4, padx=(2, 8), pady=PAD_Y)

        # ---- Lógica de atualização (subtipo + obs + preview) --------
        def _refresh_preview(*_):
            tipo    = item["tipo_var"].get()
            subtipo = item["subtipo_var"].get() or None
            obs     = item["obs_var"].get().strip()
            if subtipo and obs:
                subtipo = f"{subtipo} - {obs}"
            nome_f  = gerar_nome_final(tipo, subtipo, ext)
            max_c   = 32
            preview_var.set("→  " + (nome_f if len(nome_f) <= max_c else nome_f[:max_c - 1] + "…"))

        # Trace no obs_var (adiciona apenas uma vez por renderização)
        for _mode, _cbname in item["obs_var"].trace_info():
            if _mode == "write":
                try:
                    item["obs_var"].trace_remove(_mode, _cbname)
                except Exception:
                    pass
        item["obs_var"].trace_add("write", lambda *_: _refresh_preview())

        def _update_subtipo(tipo_nome, _sf=sub_frame, _sv=item["subtipo_var"], _ov=item["obs_var"]):
            for w in _sf.winfo_children():
                w.destroy()
            subs = DOCS_CONFIG.get(tipo_nome, {}).get("subtipos", [])
            if subs:
                _sv.set(subs[0])
                ctk.CTkOptionMenu(
                    _sf, variable=_sv, values=subs,
                    width=118, **_opt_kw,  # _opt_kw já tem height=30
                    command=lambda _: _refresh_preview(),
                ).place(x=0, y=0, height=30)
                _ov.set("")
                ctk.CTkEntry(
                    _sf, textvariable=_ov,
                    width=108, height=30,
                    placeholder_text="Obs…",
                    fg_color=COLORS["bg"],
                    border_color=COLORS["stroke"],
                    text_color=COLORS["text"],
                    font=ctk.CTkFont("Segoe UI", 11),
                ).place(x=122, y=0, height=30)
            else:
                _sv.set("")
                _ov.set("")
            _refresh_preview()

        tipo_menu.configure(command=_update_subtipo)
        _update_subtipo(item["tipo_var"].get())   # inicializa

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0, height=62)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        if not HAS_DND:
            ctk.CTkLabel(
                footer,
                text="⚠  Instale tkinterdnd2 para habilitar drag & drop",
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=COLORS["warning"],
            ).grid(row=0, column=0, sticky="w", padx=20)

        btns = ctk.CTkFrame(footer, fg_color="transparent")
        btns.grid(row=0, column=1, padx=20, pady=12)

        ctk.CTkButton(
            btns,
            text="Fechar",
            width=100,
            height=36,
            corner_radius=9,
            fg_color=COLORS["stroke"],
            hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._fechar,
        ).pack(side="left", padx=(0, 8))

        self._btn_confirmar = ctk.CTkButton(
            btns,
            text="✓  Confirmar envio",
            width=180,
            height=36,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            state="disabled",
            command=self._confirmar,
        )
        self._btn_confirmar.pack(side="left")

    # ------------------------------------------------------------------
    # Handlers de arquivo
    # ------------------------------------------------------------------

    def _on_drop(self, event):
        paths = _parse_drop(event.data)
        self._adicionar_na_fila(paths)

    def _selecionar_arquivos(self):
        paths = filedialog.askopenfilenames(
            title="Selecionar documentos",
            filetypes=[
                ("Documentos", "*.pdf *.jpg *.jpeg *.png *.docx *.doc *.xlsx"),
                ("Todos os arquivos", "*.*"),
            ],
            parent=self,
        )
        if paths:
            self._adicionar_na_fila(list(paths))

    def _adicionar_na_fila(self, paths: list[str]):
        for path in paths:
            nome = os.path.basename(path)
            tipo_sugerido = sugerir_tipo(nome) or _TIPOS[0]
            subs = DOCS_CONFIG.get(tipo_sugerido, {}).get("subtipos", [])

            item = {
                "caminho":       path,
                "nome_original": nome,
                "tipo_var":      ctk.StringVar(value=tipo_sugerido),
                "subtipo_var":   ctk.StringVar(value=subs[0] if subs else ""),
                "obs_var":       ctk.StringVar(value=""),
            }
            self._fila.append(item)

        self._renderizar_fila()

    def _remover_da_fila(self, idx: int):
        if 0 <= idx < len(self._fila):
            self._fila.pop(idx)
        self._renderizar_fila()

    # ------------------------------------------------------------------
    # Confirmar envio
    # ------------------------------------------------------------------

    def _confirmar(self):
        if not self._fila:
            return

        pasta = self._pasta
        caminho_pasta = pasta.get("caminho_local", "")

        if not caminho_pasta or not os.path.isdir(caminho_pasta):
            messagebox.showerror(
                "Pasta não encontrada",
                f"O diretório da pasta não existe no disco:\n{caminho_pasta}",
                parent=self,
            )
            return

        # Valida subtipos obrigatórios antes de processar qualquer coisa
        for item in self._fila:
            tipo   = item["tipo_var"].get()
            subtipo = item["subtipo_var"].get()
            subs   = DOCS_CONFIG.get(tipo, {}).get("subtipos", [])
            if subs and not subtipo:
                messagebox.showwarning(
                    "Subtipo obrigatório",
                    f"Selecione o subtipo para o arquivo:\n{item['nome_original']} ({tipo})",
                    parent=self,
                )
                return

        self._btn_confirmar.configure(state="disabled", text="Enviando…")
        self.update()

        enviados  = 0
        erros     = []

        for item in list(self._fila):
            tipo    = item["tipo_var"].get()
            subtipo = item["subtipo_var"].get() or None
            obs     = item["obs_var"].get().strip()
            if subtipo and obs:
                subtipo = f"{subtipo} - {obs}"

            ok, _, erro = adicionar_doc_a_pasta(
                pasta["id"], item["caminho"], tipo, subtipo, caminho_pasta
            )

            if not ok and "Já existe" in erro:
                resp = messagebox.askyesno(
                    "Substituir documento?",
                    f"Já existe um arquivo para '{tipo}"
                    + (f" – {subtipo}" if subtipo else "")
                    + f"'.\n\nSubstituir por '{item['nome_original']}'?",
                    parent=self,
                )
                if resp:
                    ok, _, erro = substituir_doc(
                        pasta["id"], item["caminho"], tipo, subtipo, caminho_pasta
                    )

            if ok:
                enviados += 1
            else:
                erros.append(f"• {item['nome_original']}: {erro}")

        # Feedback
        if erros:
            msg = "\n".join(erros)
            if enviados:
                messagebox.showwarning(
                    "Envio parcial",
                    f"{enviados} arquivo(s) enviado(s) com sucesso.\n\nErros:\n{msg}",
                    parent=self,
                )
            else:
                messagebox.showerror("Erro no envio", msg, parent=self)

        # Atualiza estado
        self._pasta = local_db.get_pasta(pasta["id"])
        self._fila.clear()
        self._atualizar_progresso()
        self._renderizar_chips()
        self._renderizar_fila()

        if enviados:
            try:
                from services.sync_manager import sync_manager
                sync_manager.push_supabase_agora()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Progresso
    # ------------------------------------------------------------------

    def _atualizar_progresso(self):
        info      = local_db.calcular_status_pasta(self._pasta["id"])
        presentes = len(info["presentes"])
        total     = len(DOCS_CONFIG)
        pct       = presentes / total if total else 0

        self._progress_bar.set(pct)
        self._progress_bar.configure(
            progress_color=COLORS["success"] if pct == 1.0 else COLORS["accent"]
        )
        self._progresso_lbl.configure(
            text=f"{presentes} / {total}",
            text_color=COLORS["success"] if pct == 1.0 else COLORS["text_muted"],
        )

    # ------------------------------------------------------------------

    def _fechar(self):
        if self._on_close:
            self._on_close()
        self.destroy()
