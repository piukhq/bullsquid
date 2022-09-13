from ward import raises, test

from bullsquid.api.auth import AccessLevel, role_to_access_level


def t(role: str) -> str:
    return role_to_access_level(role, app_name="test")


@test("can convert role strings to access levels")
def _() -> None:
    assert t("test:ro") == AccessLevel.READ_ONLY
    assert t("test:rw") == AccessLevel.READ_WRITE
    assert t("test:rwd") == AccessLevel.READ_WRITE_DELETE


@test("invalid role string raises an error")
def _() -> None:
    with raises(ValueError):
        t("test:badrole")


@test("incorrect app name prefix raises an error")
def _() -> None:
    with raises(ValueError):
        t("badprefix:ro")


@test("incorrect role string and app name prefix raises an error")
def _() -> None:
    with raises(ValueError):
        t("badprefix:badrole")


@test("prefixed role string without the prefix raises an error")
def _() -> None:
    with raises(ValueError):
        t("ro")
