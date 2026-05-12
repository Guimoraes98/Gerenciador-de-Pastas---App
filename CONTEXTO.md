# CONTEXTO DO PROJETO — Efitecsolar Gerenciador de Pastas

## Visão Geral
App desktop em Python para a empresa **Efitecsolar**. Funciona como um gerenciador de pastas e documentos de clientes que viraram vendas. Os vendedores criam pastas padronizadas, adicionam documentos obrigatórios, e o app sincroniza tudo com o Google Drive.

---

## Stack Técnica
- **UI:** CustomTkinter (tema dark, visual moderno)
- **Banco local (offline):** SQLite via `database/local_db.py`
- **Banco online:** Supabase (ainda não implementado — credenciais em `config.py`)
- **Google Drive:** google-api-python-client com OAuth (ainda não implementado)
- **Distribuição:** PyInstaller `.exe` + instalador para Windows

---

## Estrutura de Pastas do Projeto

```
efitec_app/
├── main.py                        # Entry point
├── config.py                      # Constantes, cores, caminhos, docs obrigatórios
├── requirements.txt
│
├── database/
│   ├── __init__.py
│   └── local_db.py                # SQLite: usuários, pastas, documentos, metas, sync_queue
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py            # Sessão do usuário logado (salvar/carregar/limpar)
│   ├── folder_service.py          # Criar pasta local, gerar nome padronizado
│   └── document_service.py        # Nomear, sugerir tipo, copiar docs para pasta
│
├── ui/
│   ├── __init__.py
│   ├── app.py                     # Janela principal + roteamento de telas
│   ├── components/
│   │   ├── sidebar.py             # Sidebar com avatar, nome, botões de navegação
│   │   └── folder_card.py         # (A CRIAR) Card individual de pasta
│   └── screens/
│       ├── login_screen.py        # Tela de login ✅
│       ├── home_screen.py         # (A CRIAR) Corrida de vendas / ranking
│       ├── folders_screen.py      # (A CRIAR) Grid de cards de pastas
│       ├── status_screen.py       # (A CRIAR) Verificar status das pastas
│       ├── sync_screen.py         # (A CRIAR) Sincronizar com Drive
│       ├── drive_screen.py        # (A CRIAR) Abre o Drive no navegador
│       └── admin/
│           └── users_screen.py    # (A CRIAR) Gerenciar usuários (só ADM)
│
└── assets/
    └── avatars/                   # Fotos de perfil dos vendedores
```

---

## Tipos de Usuário
- **Vendedor** — vê e gerencia apenas suas próprias pastas
- **ADM** — vê pastas de todos os vendedores + gerencia usuários + define metas mensais

Usuário ADM padrão criado automaticamente no primeiro run:
- Email: `adm@efitecsolar.com.br`
- Senha: `adm123`

---

## Layout da Janela (1300x800)
- **Sidebar** (260px, fixo à esquerda): avatar circular + nome + tipo do usuário + botões de navegação + versão + botão logout
- **Área de conteúdo** (resto da janela): troca conforme o botão clicado na sidebar, sem abrir novas janelas

---

## Telas e Botões da Sidebar

| Tela (chave) | Label na Sidebar | Quem vê |
|---|---|---|
| `home` | 🏠 Início | Todos |
| `pastas` | 📁 Minhas Pastas | Todos |
| `status` | 📋 Verificar Status | Todos |
| `sync` | 🔄 Sincronizar Pastas | Todos |
| `drive` | ☁️ Acessar Drive | Todos |
| `usuarios` | 👥 Gerenciar Usuários | Só ADM |

---

## Estrutura de Pastas no Sistema de Arquivos

**Local (PC do vendedor):**
```
Desktop/Pastas_Clientes/2026/Maio/Joao Silva - Niteroi - 7,35kwp - Carlos
```

**Google Drive:**
```
EFITECSOLAR-DRIVE/2026/MAIO/CARLOS/Joao Silva - Niteroi - 7,35kwp - Carlos
```

---

## Campos para Criar Nova Pasta
| Campo | Tipo | Obrigatório |
|---|---|---|
| Nome do Cliente | Texto | ✅ |
| Cidade | Texto | ✅ |
| KWP | Número decimal | ✅ |
| Valor da Venda | Número (R$) | ✅ |
| SDR Responsável | Texto | ❌ |
| ID CRM | Número | ❌ |

**Nome da pasta gerado automaticamente:**
`Nome_Cliente - Cidade - 7,35kwp - Nome_Vendedor`

---

## Documentos Obrigatórios (11 tipos)
Definidos em `config.py` → `DOCS_CONFIG`

| Tipo | Subtipos | Nome do arquivo gerado |
|---|---|---|
| CNH | Principal / Rateio | `CNH – Principal.pdf` |
| Conta de Luz | Principal / Rateio | `Conta de Luz – Rateio.pdf` |
| Contrato | — | `Contrato.pdf` |
| Proposta Comercial | — | `Proposta Comercial.pdf` |
| Procuração | — | `Procuração.pdf` |
| Projeto 2D | — | `Projeto 2D.pdf` |
| Nota Fiscal | — | `Nota Fiscal.pdf` |
| Lista de Equipamento | — | `Lista de Equipamento.pdf` |
| Checklist | — | `Checklist.pdf` |
| Pagamento Serviço | Entrada / 50% / Quitação | `Pagamento Serviço – Entrada.pdf` |
| Pagamento Equipamento | Entrada / 50% / Quitação | `Pagamento Equipamento – Quitação.pdf` |

Pasta com **status COMPLETA** = todos os 11 tipos presentes.
Pasta **INCOMPLETA** = falta ao menos 1 tipo.
Só pastas COMPLETAS contam como venda no ranking.

---

## Cards de Pasta (tela Minhas Pastas)
Grid 3 colunas. Cada card mostra:
- Nome do cliente
- Cidade + KWP
- Vendedor + SDR
- Data de criação
- Status (verde = completa / vermelho = incompleta)
- Botão 🗑️ Excluir
- Botão 🌐 CRM → abre `https://efitecsolar.groner.app/negocio/{id_crm}/contato`
- Botão 📂 Abrir pasta local

Na tela também deve haver botão **"+ Nova Pasta"** e opção de selecionar pasta existente para add/substituir documentos.

---

## Tela Home — Corrida de Vendas
- Ranking visual estilo maratona com avatares dos vendedores
- Posição na pista proporcional ao nº de vendas do mês
- Tabela abaixo com: posição, avatar, nome, nº de vendas, valor total vendido
- Meta mensal configurável pelo ADM (nº de vendas + valor total em R$)
- Filtro de mês/ano

---

## Tela Verificar Status
- Lista de pastas com filtro por mês e ano
- Para cada pasta: nome, documentos presentes, documentos faltando, status (verde/vermelho)

---

## Tela Sincronizar Pastas
- Permite ao usuário forçar envio de pastas para o Drive
- Filtro: por mês inteiro ou selecionar pastas específicas
- Mostra progresso do upload

---

## Paleta de Cores (config.py → COLORS)
```python
"bg":           "#0F1117"   # fundo principal
"sidebar":      "#16181F"   # fundo sidebar
"card":         "#1E2029"   # fundo cards
"card_hover":   "#252836"
"stroke":       "#2A2D3A"   # bordas
"accent":       "#F97316"   # laranja (botões principais)
"accent_hover": "#EA6A0A"
"accent2":      "#3B82F6"   # azul (botões secundários)
"success":      "#22C55E"   # verde (completa)
"danger":       "#EF4444"   # vermelho (incompleta)
"text":         "#F1F5F9"
"text_muted":   "#94A3B8"
"text_dim":     "#475569"
```

---

## Status de Implementação

| Arquivo | Status |
|---|---|
| `main.py` | ✅ Pronto |
| `config.py` | ✅ Pronto |
| `database/local_db.py` | ✅ Pronto |
| `services/auth_service.py` | ✅ Pronto |
| `services/folder_service.py` | ✅ Pronto |
| `services/document_service.py` | ✅ Pronto |
| `ui/app.py` | ✅ Pronto |
| `ui/components/sidebar.py` | ✅ Pronto |
| `ui/screens/login_screen.py` | ✅ Pronto |
| `ui/components/folder_card.py` | 🔲 A criar |
| `ui/screens/folders_screen.py` | 🔲 A criar |
| `ui/screens/home_screen.py` | 🔲 A criar |
| `ui/screens/status_screen.py` | 🔲 A criar |
| `ui/screens/sync_screen.py` | 🔲 A criar |
| `ui/screens/drive_screen.py` | 🔲 A criar |
| `ui/screens/admin/users_screen.py` | 🔲 A criar |
| `services/drive_service.py` | 🔲 A criar |
| `services/sync_service.py` | 🔲 A criar |
| `database/supabase_client.py` | 🔲 A criar |

---

## Próximos Passos Sugeridos (em ordem)
1. `ui/components/folder_card.py` + `ui/screens/folders_screen.py` — tela principal de uso diário
2. Modal de criar nova pasta (dentro de `folders_screen.py`)
3. Modal de adicionar documentos com drag & drop
4. `ui/screens/home_screen.py` — corrida de vendas
5. `ui/screens/status_screen.py`
6. `services/drive_service.py` + `ui/screens/sync_screen.py`
7. `ui/screens/admin/users_screen.py`
8. `database/supabase_client.py` — sync online

---

## Observações Importantes
- O app deve funcionar **100% offline**. Sem internet, tudo salva local no SQLite e fica na fila de sync.
- Não usar variáveis globais para estado — usar `services/auth_service.py` para o usuário logado.
- Cada tela recebe `(master, usuario: dict, on_navigate)` no `__init__`.
- Todas as telas usam `.grid(row=0, column=0, sticky="nsew")` para preencher o content frame.
- Manter o padrão visual: fundo `#0F1117`, cards `#1E2029`, destaque laranja `#F97316`.
