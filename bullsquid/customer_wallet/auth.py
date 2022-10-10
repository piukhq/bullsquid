"""
Provides merchant data API authentication helpers.
"""
from typing import Callable

from bullsquid.api.auth import AccessLevel, JWTCredentials
from bullsquid.api.auth import require_access_level as base_require_access_level
from bullsquid.customer_wallet.piccolo_app import APP_CONFIG


def require_access_level(level: AccessLevel) -> Callable[[], JWTCredentials]:
    """
    Call bullsquid.api.auth.require_access_level with the correct app name.
    """
    return base_require_access_level(level, app_name=APP_CONFIG.app_name)
