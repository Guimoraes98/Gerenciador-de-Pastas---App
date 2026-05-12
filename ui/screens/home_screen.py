# =============================================================
#  ui/screens/home_screen.py — Corrida de Vendas / Ranking
# =============================================================

import os
import tkinter as tk
from datetime import datetime
import customtkinter as ctk
from PIL import Image, ImageTk

from config import COLORS, MESES_PT, ASSETS_DIR
from database import local_db
from ui.components.sidebar import _avatar_circular, _avatar_iniciais

_BANNER_PATH = os.path.join(ASSETS_DIR, "banner_efitec.png")


# Medalhas para os 3 primeiros
_MEDALHAS = {1: "🥇", 2: "🥈", 3: "🥉"}

# Cores das barras por posição
_BAR_COLORS = {
    1: COLORS["accent"],    # laranja
    2: COLORS["accent2"],   # azul
    3: COLORS["warning"],   # amarelo
}
_BAR_DEFAULT = "#3D4155"


# ------------------------------------------------------------------
class HomeScreen(ctk.CTkFrame):
    """Tela inicial — corrida de vendas, meta do mês e ranking."""

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

        # Título
        titulo_box = ctk.CTkFrame(bar, fg_color="transparent")
        titulo_box.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            titulo_box,
            text="🏆  Corrida de Vendas",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._subtitulo = ctk.CTkLabel(
            titulo_box, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._subtitulo.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Controles
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
        ).grid(row=0, column=3, padx=(0, 12))

        if self._eh_adm:
            ctk.CTkButton(
                ctrl, text="🎯  Definir Meta",
                height=36, corner_radius=10,
                fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont("Segoe UI", 12),
                command=self._abrir_modal_meta,
            ).grid(row=0, column=4)

        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=0, column=0, sticky="sew", padx=20)

    # ------------------------------------------------------------------
    # Área de conteúdo
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
    # Carregar e renderizar
    # ------------------------------------------------------------------

    def _carregar(self):
        mes = MESES_PT.index(self._mes_nome_var.get()) + 1
        ano = int(self._ano_str_var.get())

        ranking = local_db.ranking_vendas(mes, ano)
        meta    = local_db.get_meta(mes, ano)

        mes_nome = MESES_PT[mes - 1]
        total_vendas = sum(v["num_vendas"] for v in ranking)
        self._subtitulo.configure(
            text=f"{mes_nome} {ano}  •  {total_vendas} venda{'s' if total_vendas != 1 else ''} no total"
        )

        # Limpa conteúdo anterior
        for w in self._scroll.winfo_children():
            w.destroy()

        self._build_hero_card(mes, ano, total_vendas, meta)
        self._build_meta_card(meta, mes, ano)
        self._build_pista(ranking, meta)
        self._build_tabela(ranking)

    # ------------------------------------------------------------------
    # Card de Meta
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Hero banner
    # ------------------------------------------------------------------

    def _build_hero_card(self, mes: int, ano: int, total_vendas: int, meta: dict):
        HERO_H = 160

        outer = ctk.CTkFrame(
            self._scroll, fg_color=COLORS["card"],
            corner_radius=14, border_width=1, border_color=COLORS["stroke"],
        )
        outer.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 8))

        canvas = tk.Canvas(outer, height=HERO_H, bg=COLORS["card"],
                           highlightthickness=0)
        canvas.pack(fill="x", expand=False)

        def _draw(_event=None):
            w = canvas.winfo_width()
            if w < 10:
                return
            canvas.delete("all")

            # Fundo: banner
            try:
                img = Image.open(_BANNER_PATH).convert("RGBA")
                img = img.resize((w, HERO_H), Image.LANCZOS)
                ov  = Image.new("RGBA", (w, HERO_H), (10, 12, 18, 185))
                img = Image.alpha_composite(img, ov)
                photo = ImageTk.PhotoImage(img)
                canvas._bg = photo
                canvas.create_image(0, 0, anchor="nw", image=photo)
            except Exception:
                canvas.configure(bg="#0F1117")

            # Gradiente lateral esquerdo (faixa accent)
            canvas.create_rectangle(0, 0, 4, HERO_H, fill=COLORS["accent"], outline="")

            # Texto principal
            mes_nome = MESES_PT[mes - 1]
            canvas.create_text(
                24, HERO_H // 2 - 18,
                text=f"🏆  Corrida de Vendas — {mes_nome} {ano}",
                fill=COLORS["text"],
                font=("Segoe UI", 15, "bold"),
                anchor="w",
            )

            meta_v = meta.get("meta_vendas", 0)
            sub = f"{total_vendas} venda{'s' if total_vendas != 1 else ''} registrada{'s' if total_vendas != 1 else ''}"
            if meta_v:
                pct = min(int(total_vendas / meta_v * 100), 100)
                sub += f"  •  {pct}% da meta mensal"
            canvas.create_text(
                24, HERO_H // 2 + 10,
                text=sub,
                fill="#AAAAAA",
                font=("Segoe UI", 12),
                anchor="w",
            )

        canvas.bind("<Configure>", lambda _e: _draw())
        outer.after(50, _draw)

    # ------------------------------------------------------------------
    # Card de Meta
    # ------------------------------------------------------------------

    def _build_meta_card(self, meta: dict, mes: int, ano: int):
        card = ctk.CTkFrame(
            self._scroll, fg_color=COLORS["card"],
            corner_radius=14, border_width=1, border_color=COLORS["stroke"],
        )
        card.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 12))
        card.grid_columnconfigure(1, weight=1)

        meta_v = meta.get("meta_vendas", 0)
        meta_r = meta.get("meta_valor", 0.0)

        # Título do card
        ctk.CTkLabel(
            card, text="🎯  Meta do Mês",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(14, 6))

        if meta_v == 0 and meta_r == 0:
            ctk.CTkLabel(
                card,
                text="Nenhuma meta definida para este mês." + (" Clique em 'Definir Meta' para configurar." if self._eh_adm else ""),
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=COLORS["text_dim"], anchor="w",
            ).grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 16))
            return

        # Busca total atual
        ranking  = local_db.ranking_vendas(mes, ano)
        total_v  = sum(r["num_vendas"] for r in ranking)
        total_r  = sum(r["valor_total"] for r in ranking)

        barras = ctk.CTkFrame(card, fg_color="transparent")
        barras.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 16))
        barras.grid_columnconfigure(1, weight=1)

        def _barra(parent, row, label, atual, meta_tot, fmt_atual, fmt_meta):
            pct  = min(atual / meta_tot, 1.0) if meta_tot > 0 else 0
            cor  = COLORS["success"] if pct >= 1.0 else COLORS["accent"]

            ctk.CTkLabel(
                parent, text=label,
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=COLORS["text_muted"], width=90, anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=4)

            ctk.CTkProgressBar(
                parent, height=10, corner_radius=5,
                fg_color=COLORS["stroke"], progress_color=cor,
            ).grid(row=row, column=1, sticky="ew", padx=12, pady=4)
            # set value after grid so size is known
            parent.winfo_children()[-1].set(pct)

            ctk.CTkLabel(
                parent,
                text=f"{fmt_atual}  /  {fmt_meta}  ({int(pct*100)}%)",
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=cor if pct >= 1.0 else COLORS["text_muted"],
                width=240, anchor="e",
            ).grid(row=row, column=2, sticky="e", pady=4)

        if meta_v > 0:
            _barra(barras, 0, "Vendas:", total_v, meta_v,
                   f"{total_v} venda{'s' if total_v != 1 else ''}",
                   f"{meta_v} vendas")

        if meta_r > 0:
            _barra(barras, 1, "Valor:", total_r, meta_r,
                   f"R$ {total_r:,.0f}".replace(",", "."),
                   f"R$ {meta_r:,.0f}".replace(",", "."))

    # ------------------------------------------------------------------
    # Pista de corrida
    # ------------------------------------------------------------------

    def _build_pista(self, ranking: list, meta: dict):
        if not ranking:
            box = ctk.CTkFrame(self._scroll, fg_color="transparent")
            box.grid(row=2, column=0, pady=40)
            ctk.CTkLabel(box, text="🏁", font=ctk.CTkFont("Segoe UI", 48),
                         text_color=COLORS["text_dim"]).pack()
            ctk.CTkLabel(box, text="Nenhuma venda registrada neste mês.",
                         font=ctk.CTkFont("Segoe UI", 14),
                         text_color=COLORS["text_muted"]).pack(pady=(8, 0))
            return

        section = ctk.CTkFrame(self._scroll, fg_color="transparent")
        section.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section, text="Pista de Corrida",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        pista = ctk.CTkFrame(
            section, fg_color=COLORS["card"],
            corner_radius=14, border_width=1, border_color=COLORS["stroke"],
        )
        pista.grid(row=1, column=0, sticky="ew")
        pista.grid_columnconfigure(3, weight=1)

        meta_v   = meta.get("meta_vendas", 0)
        max_v    = max(v["num_vendas"] for v in ranking) if ranking else 1
        referencia = max(meta_v, max_v) or 1   # usa meta ou máximo como 100%

        for idx, vendedor in enumerate(ranking):
            pos      = idx + 1
            num_v    = vendedor["num_vendas"]
            pct      = num_v / referencia if referencia > 0 else 0
            cor_bar  = _BAR_COLORS.get(pos, _BAR_DEFAULT)
            medalha  = _MEDALHAS.get(pos, f"#{pos}")
            bg_row   = COLORS["card_hover"] if pos == 1 else "transparent"

            row_frame = ctk.CTkFrame(pista, fg_color=bg_row, corner_radius=10)
            row_frame.grid(row=idx, column=0, columnspan=5, sticky="ew",
                           padx=8, pady=4)
            row_frame.grid_columnconfigure(3, weight=1)

            # Posição / medalha
            ctk.CTkLabel(
                row_frame, text=medalha,
                font=ctk.CTkFont("Segoe UI", 18),
                width=38, anchor="center",
            ).grid(row=0, column=0, padx=(10, 4), pady=10)

            # Avatar
            img = (
                _avatar_circular(vendedor.get("avatar_path"), 38)
                or _avatar_iniciais(vendedor["nome"], 38)
            )
            av_lbl = ctk.CTkLabel(row_frame, image=img, text="", width=40)
            av_lbl.image = img
            av_lbl.grid(row=0, column=1, padx=(0, 10), pady=8)

            # Nome
            ctk.CTkLabel(
                row_frame,
                text=vendedor["nome"].split()[0],   # primeiro nome
                font=ctk.CTkFont("Segoe UI", 13, "bold" if pos == 1 else "normal"),
                text_color=COLORS["text"] if pos == 1 else COLORS["text_muted"],
                width=110, anchor="w",
            ).grid(row=0, column=2, padx=(0, 12), pady=10, sticky="w")

            # Barra de progresso
            bar = ctk.CTkProgressBar(
                row_frame, height=14, corner_radius=6,
                fg_color=COLORS["stroke"], progress_color=cor_bar,
            )
            bar.grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=10)
            bar.set(pct)

            # Contagem
            valor_fmt = f"R$ {vendedor['valor_total']:,.0f}".replace(",", ".")
            ctk.CTkLabel(
                row_frame,
                text=f"{num_v} venda{'s' if num_v != 1 else ''}",
                font=ctk.CTkFont("Segoe UI", 12, "bold" if pos == 1 else "normal"),
                text_color=cor_bar,
                width=80, anchor="e",
            ).grid(row=0, column=4, padx=(0, 8), pady=10)

            ctk.CTkLabel(
                row_frame,
                text=valor_fmt,
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=COLORS["text_dim"],
                width=90, anchor="e",
            ).grid(row=0, column=5, padx=(0, 12), pady=10)

    # ------------------------------------------------------------------
    # Tabela de resultados
    # ------------------------------------------------------------------

    def _build_tabela(self, ranking: list):
        if not ranking:
            return

        section = ctk.CTkFrame(self._scroll, fg_color="transparent")
        section.grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 16))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section, text="Resultados",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        tabela = ctk.CTkFrame(
            section, fg_color=COLORS["card"],
            corner_radius=14, border_width=1, border_color=COLORS["stroke"],
        )
        tabela.grid(row=1, column=0, sticky="ew")
        tabela.grid_columnconfigure(2, weight=1)

        # Cabeçalho
        hdr = ctk.CTkFrame(tabela, fg_color=COLORS["stroke"], corner_radius=10, height=36)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(2, weight=1)

        for col, (txt, w, anchor) in enumerate([
            ("#",          40,  "center"),
            ("Vendedor",  180,  "w"),
            ("",            0,  "w"),      # espaço flex
            ("Vendas",     80,  "center"),
            ("Valor Total",150, "e"),
        ]):
            ctk.CTkLabel(
                hdr, text=txt, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                text_color=COLORS["text_muted"],
                width=w if w else 0, anchor=anchor,
            ).grid(row=0, column=col, padx=6, pady=6, sticky=anchor if anchor != "center" else "")

        # Linhas
        for idx, v in enumerate(ranking):
            pos     = idx + 1
            bg      = "#1A1D27" if idx % 2 == 0 else "transparent"
            medalha = _MEDALHAS.get(pos, str(pos))

            lr = ctk.CTkFrame(tabela, fg_color=bg, corner_radius=8, height=44)
            lr.grid(row=idx + 1, column=0, sticky="ew", padx=8, pady=1)
            lr.grid_propagate(False)
            lr.grid_columnconfigure(2, weight=1)

            # Pos
            ctk.CTkLabel(lr, text=medalha,
                         font=ctk.CTkFont("Segoe UI", 13),
                         width=40, anchor="center").grid(
                row=0, column=0, padx=6, pady=10)

            # Avatar pequeno
            img = (
                _avatar_circular(v.get("avatar_path"), 28)
                or _avatar_iniciais(v["nome"], 28)
            )
            av = ctk.CTkLabel(lr, image=img, text="", width=30)
            av.image = img
            av.grid(row=0, column=1, padx=(4, 6), pady=8)

            # Nome
            ctk.CTkLabel(
                lr, text=v["nome"],
                font=ctk.CTkFont("Segoe UI", 12, "bold" if pos <= 3 else "normal"),
                text_color=COLORS["text"] if pos <= 3 else COLORS["text_muted"],
                anchor="w",
            ).grid(row=0, column=2, sticky="w", padx=4, pady=10)

            # Vendas
            ctk.CTkLabel(
                lr, text=str(v["num_vendas"]),
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
                text_color=_BAR_COLORS.get(pos, COLORS["text_muted"]),
                width=80, anchor="center",
            ).grid(row=0, column=3, padx=6, pady=10)

            # Valor
            valor_fmt = f"R$ {v['valor_total']:,.0f}".replace(",", ".")
            ctk.CTkLabel(
                lr, text=valor_fmt,
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=COLORS["text_muted"],
                width=150, anchor="e",
            ).grid(row=0, column=4, padx=(0, 12), pady=10)

        # Espaço final
        ctk.CTkFrame(tabela, fg_color="transparent", height=8).grid(
            row=len(ranking) + 1, column=0)

    # ------------------------------------------------------------------
    # Modal Editar Meta (ADM)
    # ------------------------------------------------------------------

    def _abrir_modal_meta(self):
        mes = MESES_PT.index(self._mes_nome_var.get()) + 1
        ano = int(self._ano_str_var.get())
        meta = local_db.get_meta(mes, ano)
        ModalEditarMeta(self, mes=mes, ano=ano, meta=meta, on_salvar=self._carregar)


# ------------------------------------------------------------------
class ModalEditarMeta(ctk.CTkToplevel):
    """Modal simples para o ADM definir a meta mensal."""

    def __init__(self, master, mes: int, ano: int, meta: dict, on_salvar, **kwargs):
        super().__init__(master, **kwargs)
        self._mes      = mes
        self._ano      = ano
        self._on_salvar = on_salvar

        self.title(f"Meta — {MESES_PT[mes - 1]} / {ano}")
        self.geometry("380x300")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()

        self.update_idletasks()
        try:
            px = master.winfo_rootx() + (master.winfo_width()  - 380) // 2
            py = master.winfo_rooty() + (master.winfo_height() - 300) // 2
            self.geometry(f"380x300+{px}+{py}")
        except Exception:
            pass

        self._vendas_var = ctk.StringVar(value=str(meta.get("meta_vendas", 0) or ""))
        self._valor_var  = ctk.StringVar(value=str(int(meta.get("meta_valor", 0) or 0)) if meta.get("meta_valor") else "")

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(padx=28, pady=24, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(outer, text="Definir Meta Mensal",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(outer, text="Defina os objetivos do time para o mês.",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 20))

        _ent_kw = dict(height=42, corner_radius=9,
                       border_color=COLORS["stroke"], fg_color=COLORS["card"],
                       text_color=COLORS["text"],
                       placeholder_text_color=COLORS["text_dim"],
                       font=ctk.CTkFont("Segoe UI", 13))

        ctk.CTkLabel(outer, text="Meta de vendas (nº de pastas completas)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        ctk.CTkEntry(outer, textvariable=self._vendas_var,
                     placeholder_text="Ex: 20", **_ent_kw,
        ).grid(row=3, column=0, sticky="ew")

        ctk.CTkLabel(outer, text="Meta de valor total (R$)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=(14, 4))

        ctk.CTkEntry(outer, textvariable=self._valor_var,
                     placeholder_text="Ex: 500000", **_ent_kw,
        ).grid(row=5, column=0, sticky="ew")

        self._erro = ctk.CTkLabel(outer, text="",
                                  font=ctk.CTkFont("Segoe UI", 11),
                                  text_color=COLORS["danger"], anchor="w")
        self._erro.grid(row=6, column=0, sticky="w", pady=(6, 0))

        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.grid(row=7, column=0, sticky="ew", pady=(14, 0))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btns, text="Cancelar", height=40, corner_radius=9,
                      fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
                      text_color=COLORS["text_muted"],
                      command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(btns, text="Salvar Meta", height=40, corner_radius=9,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      font=ctk.CTkFont("Segoe UI", 13, "bold"),
                      command=self._salvar,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.bind("<Return>", lambda _: self._salvar())

    def _salvar(self):
        try:
            vendas = int(self._vendas_var.get().strip() or 0)
        except ValueError:
            self._erro.configure(text="Meta de vendas deve ser um número inteiro.")
            return
        try:
            valor = float(self._valor_var.get().strip().replace(",", ".") or 0)
        except ValueError:
            self._erro.configure(text="Meta de valor deve ser um número (ex: 500000).")
            return

        local_db.salvar_meta(self._mes, self._ano, vendas, valor)
        self.destroy()
        self._on_salvar()
