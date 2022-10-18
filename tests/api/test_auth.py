import pytest

from bullsquid.api.auth import AccessLevel, role_to_access_level


def t(role: str) -> str:
    return role_to_access_level(role, app_name="test")


def test_convert_role_string_to_access_level() -> None:
    assert t("test:ro") == AccessLevel.READ_ONLY
    assert t("test:rw") == AccessLevel.READ_WRITE
    assert t("test:rwd") == AccessLevel.READ_WRITE_DELETE


def test_invalid_role_string() -> None:
    with pytest.raises(ValueError):
        t("test:badrole")


def test_incorrect_app_name() -> None:
    with pytest.raises(ValueError):
        t("badprefix:ro")


def test_incorrect_role_string_and_app_name() -> None:
    with pytest.raises(ValueError):
        t("badprefix:badrole")


def test_role_string_without_prefix() -> None:
    with pytest.raises(ValueError):
        t("ro")
