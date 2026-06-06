"""Internationalization (i18n) support for the GUI."""

from foxhole_stockpiles.i18n.translator import (
    Translator,
    get_available_languages,
    get_translator,
    off_language_changed,
    on_language_changed,
    set_language,
    set_translations_resource,
    t,
)

__all__ = [
    "Translator",
    "get_available_languages",
    "get_translator",
    "off_language_changed",
    "on_language_changed",
    "set_language",
    "set_translations_resource",
    "t",
]
