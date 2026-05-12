# =============================================================
#  main.py — Ponto de entrada do App Efitecsolar
# =============================================================

import sys
import os

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.local_db import init_db
from ui.app import App


def main():
    # 1. Inicializa / migra o banco local
    init_db()

    # 2. Inicia a interface gráfica
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
