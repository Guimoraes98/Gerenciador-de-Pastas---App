# =============================================================
#  ui/screens/sync_screen.py — Sincronizar Pastas com Google Drive
# =============================================================

import os
import threading
import customtkinter as ctk

from config import COLORS, MESES_PT, DRIVE_TOKEN, DRIVE_CREDS
from database import local_db


def _drive_conectado() -> bool:
    return os.path.exists(DRIVE_TOKEN)


def _drive_credenciais_ok() -> bool:
    return os.path.exists(DRIVE_CREDS)


class SyncScreen(ctk.CTkFrame):
    """
    Tela de sincronização com Google Drive.
    Mostra o status de cada pasta e permite sincronizar manualmente.
    """

    def __init__(self, master, usuario: dict, on_navigate, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLORS["bg"], **kwargs)
        self._usuario     = usuario
        self._on_navigate = on_navigate
        self._eh_adm      = usuario.get("tipo") == "ADM"
        self._sincronizando = False

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
            text="🔄  Sincronizar Pastas",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._subtitulo = ctk.CTkLabel(
            titulo_box, text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._subtitulo.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Painel direito — status de conexão + botão sync
        ctrl = ctk.CTkFrame(bar, fg_color="transparent")
        ctrl.grid(row=0, column=2, sticky="e")

        self._status_supa_lbl = ctk.CTkLabel(
            ctrl, text="",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=COLORS["text_muted"],
        )
        self._status_supa_lbl.pack(side="left", padx=(0, 16))

        self._status_drive_lbl = ctk.CTkLabel(
            ctrl, text="",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=COLORS["text_muted"],
        )
        self._status_drive_lbl.pack(side="left", padx=(0, 12))

        self._btn_conectar = ctk.CTkButton(
            ctrl,
            text="🔗  Conectar Drive",
            height=36, corner_radius=9,
            fg_color=COLORS["accent2"], hover_color=COLORS["accent2_hover"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self._conectar_drive,
        )
        self._btn_conectar.pack(side="left", padx=(0, 8))

        self._btn_sync = ctk.CTkButton(
            ctrl,
            text="▶  Sincronizar Agora",
            height=36, corner_radius=9,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self._sincronizar,
        )
        self._btn_sync.pack(side="left")

        self._btn_update = ctk.CTkButton(
            ctrl,
            text="🔔  Verificar Atualização",
            height=36, corner_radius=9,
            fg_color=COLORS["stroke"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self._verificar_atualizacao_manual,
        )
        self._btn_update.pack(side="left", padx=(8, 0))

        ctk.CTkFrame(self, height=1, fg_color=COLORS["stroke"]).grid(
            row=0, column=0, sticky="sew", padx=20)

        self._atualizar_status_drive()
        self._atualizar_status_supabase()

    # ------------------------------------------------------------------
    # Status de conexão Drive
    # ------------------------------------------------------------------

    def _atualizar_status_drive(self):
        if _drive_conectado():
            self._status_drive_lbl.configure(
                text="● Drive conectado", text_color=COLORS["success"])
            self._btn_conectar.configure(
                text="🔓  Desconectar", fg_color=COLORS["stroke"],
                hover_color=COLORS["danger"], text_color=COLORS["text_muted"],
                command=self._desconectar_drive,
            )
            self._btn_sync.configure(state="normal")
        else:
            self._status_drive_lbl.configure(
                text="○ Drive desconectado", text_color=COLORS["text_dim"])
            self._btn_conectar.configure(
                text="🔗  Conectar Drive", fg_color=COLORS["accent2"],
                hover_color=COLORS["accent2_hover"], text_color=COLORS["text"],
                command=self._conectar_drive,
            )
            self._btn_sync.configure(state="disabled")

    def _atualizar_status_supabase(self):
        try:
            from services.supabase_client import testar_conexao
            if testar_conexao():
                self._status_supa_lbl.configure(
                    text="● Supabase online", text_color=COLORS["success"])
            else:
                self._status_supa_lbl.configure(
                    text="○ Supabase offline", text_color=COLORS["text_dim"])
        except ImportError:
            self._status_supa_lbl.configure(
                text="○ Supabase offline", text_color=COLORS["text_dim"])
        except Exception:
            self._status_supa_lbl.configure(
                text="○ Supabase offline", text_color=COLORS["text_dim"])

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
        vendedor_id = None if self._eh_adm else self._usuario["id"]
        pastas = local_db.listar_pastas(vendedor_id=vendedor_id)

        n_ok      = sum(1 for p in pastas if p["sync_status"] == "ok")
        n_pend    = sum(1 for p in pastas if p["sync_status"] == "pendente")
        n_erro    = sum(1 for p in pastas if p["sync_status"] == "erro")

        self._subtitulo.configure(
            text=f"{len(pastas)} pasta{'s' if len(pastas) != 1 else ''}  •  "
                 f"{n_ok} sincronizada{'s' if n_ok != 1 else ''}  •  "
                 f"{n_pend} pendente{'s' if n_pend != 1 else ''}  •  "
                 f"{n_erro} com erro"
        )

        for w in self._scroll.winfo_children():
            w.destroy()

        if not pastas:
            self._mostrar_vazio()
            return

        # Cabeçalho da tabela
        self._build_header()

        # Erros primeiro, depois pendentes, depois ok
        def _ordem(p):
            order = {"erro": 0, "pendente": 1, "ok": 2}
            return (order.get(p["sync_status"], 9), p["nome_pasta"])

        for idx, pasta in enumerate(sorted(pastas, key=_ordem)):
            self._build_row(idx + 1, pasta)

    def _mostrar_vazio(self):
        box = ctk.CTkFrame(self._scroll, fg_color="transparent")
        box.grid(row=0, column=0, pady=60)
        ctk.CTkLabel(box, text="🔄", font=ctk.CTkFont("Segoe UI", 52),
                     text_color=COLORS["text_dim"]).pack()
        ctk.CTkLabel(box, text="Nenhuma pasta cadastrada ainda",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(8, 4))
        ctk.CTkLabel(box, text="Crie pastas em 'Minhas Pastas' para sincronizá-las.",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"]).pack()

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = ctk.CTkFrame(self._scroll, fg_color=COLORS["card"], corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 4))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_columnconfigure(1, minsize=120)
        hdr.grid_columnconfigure(2, minsize=110)
        hdr.grid_columnconfigure(3, minsize=120)

        _kw = dict(font=ctk.CTkFont("Segoe UI", 10, "bold"),
                   text_color=COLORS["text_dim"])

        ctk.CTkLabel(hdr, text="PASTA", anchor="w", **_kw).grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=8)
        ctk.CTkLabel(hdr, text="MÊS / ANO", anchor="w", **_kw).grid(
            row=0, column=1, sticky="w", padx=8, pady=8)
        ctk.CTkLabel(hdr, text="DOCUMENTOS", anchor="w", **_kw).grid(
            row=0, column=2, sticky="w", padx=8, pady=8)
        ctk.CTkLabel(hdr, text="STATUS DRIVE", anchor="w", **_kw).grid(
            row=0, column=3, sticky="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    # Linha da tabela
    # ------------------------------------------------------------------

    def _build_row(self, idx: int, pasta: dict):
        sync_st  = pasta.get("sync_status", "pendente")
        bg_even  = COLORS["card"]
        bg_odd   = "#1A1C25"
        bg       = bg_even if idx % 2 == 0 else bg_odd

        _STATUS_CORES = {
            "ok":       (COLORS["success"],  "✓  Sincronizada"),
            "pendente": (COLORS["warning"],   "⏳  Pendente"),
            "erro":     (COLORS["danger"],    "✗  Erro"),
        }
        cor_st, label_st = _STATUS_CORES.get(sync_st, (COLORS["text_dim"], sync_st))

        row_f = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
        row_f.grid(row=idx, column=0, sticky="ew", padx=8, pady=1)
        row_f.grid_columnconfigure(0, weight=1)
        row_f.grid_columnconfigure(1, minsize=120)
        row_f.grid_columnconfigure(2, minsize=110)
        row_f.grid_columnconfigure(3, minsize=120)

        # Nome pasta
        ctk.CTkLabel(
            row_f, text=pasta["nome_pasta"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(16, 8), pady=10)

        # Mês / Ano
        mes_nome = MESES_PT[pasta["mes"] - 1]
        ctk.CTkLabel(
            row_f, text=f"{mes_nome} {pasta['ano']}",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8)

        # Documentos (n / total)
        try:
            docs = local_db.listar_documentos(pasta["id"])
            from config import DOCS_CONFIG
            n_docs  = len(docs)
            n_total = len(DOCS_CONFIG)
            cor_doc = COLORS["success"] if pasta["status"] == "completa" else COLORS["text_muted"]
            txt_doc = f"{n_docs} / {n_total}"
        except Exception:
            txt_doc = "—"
            cor_doc = COLORS["text_dim"]

        ctk.CTkLabel(
            row_f, text=txt_doc,
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=cor_doc, anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=8)

        # Status Drive + botão retentar
        st_frame = ctk.CTkFrame(row_f, fg_color="transparent")
        st_frame.grid(row=0, column=3, sticky="w", padx=8)

        ctk.CTkLabel(
            st_frame, text=label_st,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=cor_st,
        ).pack(side="left")

        if sync_st == "erro":
            ctk.CTkButton(
                st_frame, text="↺", width=28, height=24, corner_radius=6,
                fg_color=COLORS["stroke"], hover_color=COLORS["accent"],
                text_color=COLORS["text_muted"], font=ctk.CTkFont("Segoe UI", 13),
                command=lambda pid=pasta["id"]: self._retentar(pid),
            ).pack(side="left", padx=(6, 0))

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _retentar(self, pasta_id: int):
        local_db.adicionar_sync_manual(pasta_id)
        self._carregar()

    def _conectar_drive(self):
        if not _drive_credenciais_ok():
            from tkinter import messagebox
            messagebox.showinfo(
                "Credenciais não encontradas",
                "O arquivo 'assets/credentials.json' não foi encontrado.\n\n"
                "Para configurar o Google Drive:\n"
                "1. Acesse console.cloud.google.com\n"
                "2. Crie um projeto e ative a Drive API\n"
                "3. Baixe o credentials.json e coloque em assets/",
                parent=self,
            )
            return

        self._btn_conectar.configure(
            text="⏳  Autenticando…", state="disabled",
            fg_color=COLORS["stroke"], text_color=COLORS["text_muted"],
        )

        def _worker():
            erro = None
            try:
                from services.drive_service import autenticar_drive
                autenticar_drive()
            except ImportError:
                erro = (
                    "Dependências do Google Drive não instaladas.\n"
                    "Execute: pip install google-auth-oauthlib google-api-python-client"
                )
            except Exception as e:
                erro = str(e)
            finally:
                self.after(0, lambda: self._apos_autenticar(erro))

        threading.Thread(target=_worker, daemon=True).start()

    def _apos_autenticar(self, erro: str | None):
        if erro:
            from tkinter import messagebox
            messagebox.showerror("Erro ao conectar Drive", erro, parent=self)
        self._atualizar_status_drive()

    def _desconectar_drive(self):
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Desconectar Drive",
            "Deseja desconectar o Google Drive?\n"
            "Os arquivos já sincronizados não serão removidos.",
            parent=self,
        ):
            return
        try:
            os.remove(DRIVE_TOKEN)
        except Exception:
            pass
        self._atualizar_status_drive()

    def _verificar_atualizacao_manual(self):
        self._btn_update.configure(text="⏳  Verificando…", state="disabled")

        def _worker():
            try:
                from services.updater import verificar_atualizacao
                release = verificar_atualizacao()
            except Exception:
                release = None
            self.after(0, lambda: self._apos_verificar_update(release))

        threading.Thread(target=_worker, daemon=True).start()

    def _apos_verificar_update(self, release):
        self._btn_update.configure(text="🔔  Verificar Atualização", state="normal")
        if release:
            from ui.components.update_dialog import UpdateDialog
            UpdateDialog(self.winfo_toplevel(), release=release)
        else:
            from tkinter import messagebox
            messagebox.showinfo(
                "Atualização",
                "Você já está na versão mais recente.",
                parent=self,
            )

    def _sincronizar(self):
        if self._sincronizando:
            return
        self._sincronizando = True
        self._btn_sync.configure(text="⏳  Sincronizando…", state="disabled")

        def _worker():
            erro_drive = None
            try:
                from services.sync_manager import sync_manager
                res_drive, res_supa = sync_manager.sincronizar_tudo_agora()
            except Exception as e:
                res_drive = {"ok": 0, "erros": 0, "ignorados": 0}
                res_supa  = {"ok": 0, "erros": 0}
                erro_drive = str(e)

            self._sincronizando = False
            self.after(0, lambda: self._apos_sync(res_drive, res_supa, erro_drive))

        threading.Thread(target=_worker, daemon=True).start()

    def _apos_sync(self, res_drive: dict, res_supa: dict, erro_drive: str | None):
        self._btn_sync.configure(text="▶  Sincronizar Agora", state="normal")
        self._atualizar_status_supabase()

        if erro_drive:
            from tkinter import messagebox
            messagebox.showerror("Erro no Drive", erro_drive, parent=self)
        elif res_drive.get("erros", 0) > 0 or res_supa.get("erros", 0) > 0:
            from tkinter import messagebox
            linhas = []
            if _drive_conectado():
                linhas.append(
                    f"Drive: ✓ {res_drive['ok']} OK   ✗ {res_drive['erros']} erros"
                )
            if res_supa.get("erros", 0) > 0:
                linhas.append(
                    f"Supabase: ✓ {res_supa['ok']} OK   ✗ {res_supa['erros']} erros"
                )
                detalhes = res_supa.get("detalhes_erro", [])
                if detalhes:
                    linhas.append(f"\nDetalhe: {detalhes[0]}")
            messagebox.showwarning(
                "Sincronização parcial", "\n".join(linhas), parent=self
            )
        self._carregar()
