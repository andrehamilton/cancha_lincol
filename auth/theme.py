"""Paletas y estilos visuales elegibles para la aplicación Cancha."""

from PySide6 import QtCore


THEMES = {
    "cancha": {
        "name": "Cancha", "background": "#f2eff8", "surface": "#ffffff",
        "primary": "#6735a8", "secondary": "#ff8b24", "outline": "#cfc2e3",
        "text": "#29213a", "muted": "#71677f", "highlight": "#e8ddf8",
    },
    "bosque": {
        "name": "Bosque", "background": "#e4f1e8", "surface": "#f8fff9",
        "primary": "#17633c", "secondary": "#c17a22", "outline": "#9fc5aa",
        "text": "#173726", "muted": "#52715c", "highlight": "#cfe7d5",
    },
    "oceano": {
        "name": "Océano", "background": "#dceef5", "surface": "#f5fcff",
        "primary": "#075985", "secondary": "#00a6a6", "outline": "#88bdcd",
        "text": "#123747", "muted": "#4c7180", "highlight": "#c3e5ee",
    },
    "cielo": {
        "name": "Atardecer", "background": "#fff0df", "surface": "#fffaf3",
        "primary": "#c2413b", "secondary": "#f08c28", "outline": "#e8b99e",
        "text": "#512c2b", "muted": "#8c6257", "highlight": "#ffe0bd",
    },
    "lavanda": {
        "name": "Lavanda", "background": "#f1e8ff", "surface": "#fdfaff",
        "primary": "#7136b5", "secondary": "#d946a8", "outline": "#c9a9ea",
        "text": "#342044", "muted": "#765c8d", "highlight": "#e5d3ff",
    },
    "coral": {
        "name": "Coral", "background": "#ffe8e4", "surface": "#fff9f7",
        "primary": "#c6384b", "secondary": "#ff7043", "outline": "#e7a7a5",
        "text": "#4b252b", "muted": "#8a5a5e", "highlight": "#ffd0c9",
    },
    "menta": {
        "name": "Menta", "background": "#ddf7ee", "surface": "#f5fffb",
        "primary": "#087f68", "secondary": "#72a900", "outline": "#91d4bc",
        "text": "#163d34", "muted": "#4c7869", "highlight": "#c2efdf",
    },
    "arena": {
        "name": "Arena", "background": "#f5e7c9", "surface": "#fff9ed",
        "primary": "#77511d", "secondary": "#b95c18", "outline": "#d4b77f",
        "text": "#403018", "muted": "#796342", "highlight": "#ead6ad",
    },
    "grafito": {
        "name": "Noche", "background": "#111827", "surface": "#1f2937",
        "primary": "#a78bfa", "secondary": "#fb923c", "outline": "#475569",
        "text": "#f1f5f9", "muted": "#bdc8d8", "highlight": "#303b50",
    },
    "malva": {
        "name": "Neón", "background": "#100d1a", "surface": "#1c1630",
        "primary": "#ff43d0", "secondary": "#44f0ff", "outline": "#65418a",
        "text": "#fff1ff", "muted": "#d1b9e6", "highlight": "#302044",
    },
}

DEFAULT_THEME = "cancha"
DIALOG_WIDTH = 1100
DIALOG_HEIGHT = 720
DIALOG_MIN_WIDTH = 900
DIALOG_MIN_HEIGHT = 620
SETTINGS_ORGANIZATION = "Cancha"
SETTINGS_APPLICATION = "CanchaReservas"


def current_theme_id():
    settings = QtCore.QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
    theme_id = settings.value("appearance/theme", DEFAULT_THEME, type=str)
    return theme_id if theme_id in THEMES else DEFAULT_THEME


def theme_palette(theme_id=None):
    return THEMES.get(theme_id or current_theme_id(), THEMES[DEFAULT_THEME])


def theme_stylesheet(theme_id=None):
    palette = theme_palette(theme_id)
    dark_accent = palette["name"] in ("Noche", "Neón")
    button_text = "#21182b" if dark_accent else "#ffffff"
    accent_text = "#17202b" if dark_accent else palette["text"]
    return f"""
QWidget {{ color: {palette['text']}; font-family: 'Segoe UI', sans-serif; }}
QMainWindow, QDialog {{ background: {palette['background']}; }}
QLabel {{ color: {palette['text']}; }}
QLineEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {palette['surface']}; color: {palette['text']};
    border: 1px solid {palette['outline']}; border-radius: 8px; padding: 8px 10px;
    selection-background-color: {palette['primary']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 2px solid {palette['primary']}; }}
QLineEdit:read-only {{ background: {palette['highlight']}; color: {palette['muted']}; }}
QPushButton {{ background: {palette['primary']}; color: {button_text}; border: none;
    border-radius: 8px; padding: 9px 14px; font-weight: 600; }}
QPushButton:hover {{ background: {palette['text']}; }}
QPushButton:pressed {{ background: {palette['primary']}; }}
QPushButton:disabled {{ background: {palette['outline']}; color: {palette['muted']}; }}
QPushButton#accentButton {{ background: {palette['secondary']}; color: {accent_text}; }}
QPushButton#accentButton:hover {{ background: {palette['primary']}; color: {button_text}; }}
QPushButton#secondaryButton {{ background: {palette['highlight']}; color: {palette['text']}; }}
QPushButton#secondaryButton:hover {{ background: {palette['outline']}; }}
QGroupBox {{ background: {palette['surface']}; border: 1px solid {palette['outline']};
    border-radius: 10px; margin-top: 13px; padding: 14px 12px 12px;
    font-weight: 700; color: {palette['primary']}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 13px; padding: 0 5px; }}
QTableWidget {{ background: {palette['surface']}; alternate-background-color: {palette['highlight']};
    border: 1px solid {palette['outline']}; border-radius: 8px; gridline-color: {palette['outline']}; }}
QHeaderView::section {{ background: {palette['highlight']}; color: {palette['text']};
    padding: 8px; border: 0; font-weight: 700; }}
QTableWidget::item:selected {{ background: {palette['primary']}; color: white; }}
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {palette['outline']};
    border-radius: 4px; background: {palette['surface']}; }}
QCheckBox::indicator:checked {{ background: {palette['primary']}; border-color: {palette['primary']}; }}
"""


APP_STYLESHEET = theme_stylesheet(DEFAULT_THEME)
