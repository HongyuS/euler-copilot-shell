"""国际化支持模块"""

from i18n.manager import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    _,
    _n,
    get_locale,
    get_supported_locales,
    init_i18n,
    set_locale,
)

__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "_",
    "_n",
    "get_locale",
    "get_supported_locales",
    "init_i18n",
    "set_locale",
]
