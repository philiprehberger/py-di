"""Tests for philiprehberger_di."""

from __future__ import annotations

from philiprehberger_di import Container, inject


class _Logger:
    """Stub service for testing."""

    def __init__(self) -> None:
        self.logs: list[str] = []

    def log(self, msg: str) -> None:
        self.logs.append(msg)


class _Database:
    """Stub service that depends on _Logger."""

    def __init__(self, logger: _Logger) -> None:
        self.logger = logger


def test_register_and_resolve() -> None:
    container = Container()
    container.register(_Logger)
    instance = container.resolve(_Logger)
    assert isinstance(instance, _Logger)


def test_singleton_returns_same_instance() -> None:
    container = Container()
    container.register(_Logger, singleton=True)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is b


def test_transient_returns_different_instances() -> None:
    container = Container()
    container.register(_Logger)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is not b


def test_inject_decorator() -> None:
    container = Container()
    container.register(_Logger, singleton=True)

    @inject(container)
    def handler(logger: _Logger) -> str:
        logger.log("handled")
        return "ok"

    result = handler()
    assert result == "ok"

    resolved = container.resolve(_Logger)
    assert resolved.logs == ["handled"]


def test_reset_clears_singletons() -> None:
    container = Container()
    container.register(_Logger, singleton=True)
    a = container.resolve(_Logger)
    container.reset()
    b = container.resolve(_Logger)
    assert a is not b


def test_recursive_resolution() -> None:
    container = Container()
    container.register(_Logger, singleton=True)
    container.register(_Database)
    db = container.resolve(_Database)
    assert isinstance(db, _Database)
    assert isinstance(db.logger, _Logger)
    assert db.logger is container.resolve(_Logger)
