"""Punto de entrada de la aplicacion Cancha."""

import sys

from PySide6 import QtWidgets

from auth.login import LoginWindow
from auth.theme import theme_stylesheet


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(theme_stylesheet())
    login = LoginWindow()
    login.window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
