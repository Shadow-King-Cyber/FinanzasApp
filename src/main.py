import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ui.login import LoginDialog
from src.ui.dashboard import Dashboard


def main():
    login = LoginDialog()
    login.mainloop()

    cifrador = login.obtener_cifrador()
    if cifrador is None:
        return

    app = Dashboard(cifrador)
    app.mainloop()


if __name__ == "__main__":
    main()
