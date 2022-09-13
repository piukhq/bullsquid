"""
Provides merchant data API authentication helpers.
"""
from bullsquid.api.auth import AccessLevel
from bullsquid.api.auth import require_access_level as base_require_access_level
from bullsquid.merchant_data.piccolo_app import APP_CONFIG


def require_access_level(level: AccessLevel) -> None:
    """
    Call bullsquid.api.auth.require_access_level with the correct app name.
    """
    return base_require_access_level(level, app_name=APP_CONFIG.app_name)
