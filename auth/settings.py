"""Selector de los diez temas de color de Cancha."""

from PySide6 import QtCore, QtWidgets

from .theme import (
    SETTINGS_APPLICATION,
    SETTINGS_ORGANIZATION,
    THEMES,
    DIALOG_HEIGHT,
    DIALOG_WIDTH,
    current_theme_id,
    theme_stylesheet,
)


class SettingsDialog(QtWidgets.QDialog):
    theme_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Temas | Cancha")
        self.setMinimumSize(940, 620)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setStyleSheet(theme_stylesheet())

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Personaliza los colores")
        title.setStyleSheet("font-size:24px; font-weight:700;")
        layout.addWidget(title)
        subtitle = QtWidgets.QLabel("Elige un tema para cambiar el fondo, los contornos y los colores de la aplicación.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)
        selected_theme = current_theme_id()
        for index, (theme_id, palette) in enumerate(THEMES.items()):
            button = self._make_theme_button(theme_id, palette)
            self.group.addButton(button)
            grid.addWidget(button, index // 5, index % 5)
            button.setChecked(theme_id == selected_theme)
            button.toggled.connect(
                lambda checked, selected=theme_id: self._select_theme(selected) if checked else None
            )
        layout.addLayout(grid)
        layout.addStretch(1)

        close = QtWidgets.QPushButton("Cerrar")
        close.setObjectName("secondaryButton")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _make_theme_button(theme_id, palette):
        button = QtWidgets.QPushButton()
        button.setCheckable(True)
        button.setFixedSize(168, 135)
        button.setStyleSheet(f"""
            QPushButton {{ background:{palette['surface']}; color:{palette['text']};
                border:2px solid {palette['outline']}; border-radius:12px; padding:7px; }}
            QPushButton:checked {{ border:3px solid {palette['primary']}; }}
            QPushButton:hover {{ border-color:{palette['primary']}; }}
        """)
        card = QtWidgets.QVBoxLayout(button)
        card.setContentsMargins(3, 3, 3, 3)
        preview = QtWidgets.QFrame()
        preview.setFixedHeight(74)
        preview.setStyleSheet(
            f"background:{palette['background']}; border:1px solid {palette['outline']}; border-radius:7px;"
        )
        preview_layout = QtWidgets.QVBoxLayout(preview)
        preview_layout.setContentsMargins(8, 7, 8, 7)
        sample = QtWidgets.QLabel("CANCHA")
        sample.setStyleSheet(
            f"background:{palette['surface']}; color:{palette['primary']}; "
            f"border:1px solid {palette['outline']}; border-radius:5px; padding:5px; font-weight:700;"
        )
        preview_layout.addWidget(sample)
        swatches = QtWidgets.QHBoxLayout()
        for color in (palette["primary"], palette["secondary"], palette["outline"], palette["highlight"]):
            chip = QtWidgets.QLabel()
            chip.setFixedSize(22, 10)
            chip.setStyleSheet(f"background:{color}; border:1px solid {palette['outline']}; border-radius:4px;")
            swatches.addWidget(chip)
        swatches.addStretch(1)
        preview_layout.addLayout(swatches)
        card.addWidget(preview)
        name = QtWidgets.QLabel(palette["name"])
        name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("border:0; background:transparent; font-weight:600;")
        card.addWidget(name)
        button.setAccessibleName(palette["name"])
        button.setProperty("theme_id", theme_id)
        return button

    def _select_theme(self, theme_id):
        settings = QtCore.QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        settings.setValue("appearance/theme", theme_id)
        settings.sync()
        stylesheet = theme_stylesheet(theme_id)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet)
        self.setStyleSheet(stylesheet)
        self.theme_selected.emit(theme_id)
