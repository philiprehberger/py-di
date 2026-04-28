"""Tests for philiprehberger_di."""

from __future__ import annotations

import pytest

from philiprehberger_di import (
    CircularDependencyError,
    Container,
    Lazy,
    Lifetime,
    Scope,
    inject,
)


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


# ------------------------------------------------------------------
# Basic registration & resolution
# ------------------------------------------------------------------


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


def test_unregistered_type_raises_key_error() -> None:
    container = Container()
    with pytest.raises(KeyError, match="not registered"):
        container.resolve(_Logger)


# ------------------------------------------------------------------
# Inject decorator
# ------------------------------------------------------------------


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


def test_inject_decorator_allows_manual_override() -> None:
    container = Container()
    container.register(_Logger, singleton=True)

    @inject(container)
    def handler(logger: _Logger) -> _Logger:
        return logger

    manual = _Logger()
    result = handler(logger=manual)
    assert result is manual


# ------------------------------------------------------------------
# Lifecycle hooks
# ------------------------------------------------------------------


def test_on_create_hook() -> None:
    created: list[_Logger] = []
    container = Container()
    container.register(_Logger, on_create=lambda inst: created.append(inst))
    instance = container.resolve(_Logger)
    assert created == [instance]


def test_on_destroy_hook_on_reset() -> None:
    destroyed: list[_Logger] = []
    container = Container()
    container.register(
        _Logger, singleton=True, on_destroy=lambda inst: destroyed.append(inst)
    )
    instance = container.resolve(_Logger)
    container.reset()
    assert destroyed == [instance]


# ------------------------------------------------------------------
# Circular dependency detection
# ------------------------------------------------------------------


class _A:
    def __init__(self, b: _B) -> None:
        self.b = b


class _B:
    def __init__(self, a: _A) -> None:
        self.a = a


class _SelfDep:
    def __init__(self, me: _SelfDep) -> None:
        self.me = me


class _X:
    def __init__(self, y: _Y) -> None:
        self.y = y


class _Y:
    def __init__(self, z: _Z) -> None:
        self.z = z


class _Z:
    def __init__(self, x: _X) -> None:
        self.x = x


def test_circular_dependency_two_types() -> None:
    container = Container()
    container.register(_A)
    container.register(_B)
    with pytest.raises(CircularDependencyError, match="_A.*_B.*_A"):
        container.resolve(_A)


def test_circular_dependency_self() -> None:
    container = Container()
    container.register(_SelfDep)
    with pytest.raises(CircularDependencyError, match="_SelfDep.*_SelfDep"):
        container.resolve(_SelfDep)


def test_circular_dependency_three_types() -> None:
    container = Container()
    container.register(_X)
    container.register(_Y)
    container.register(_Z)
    with pytest.raises(CircularDependencyError, match="_X.*_Y.*_Z.*_X"):
        container.resolve(_X)


def test_circular_dependency_error_has_chain() -> None:
    container = Container()
    container.register(_A)
    container.register(_B)
    with pytest.raises(CircularDependencyError) as exc_info:
        container.resolve(_A)
    assert exc_info.value.chain == [_A, _B, _A]


# ------------------------------------------------------------------
# Scoped lifetime
# ------------------------------------------------------------------


def test_scoped_is_singleton_within_scope() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.SCOPED)

    with container.create_scope() as scope:
        a = scope.resolve(_Logger)
        b = scope.resolve(_Logger)
        assert a is b


def test_scoped_differs_across_scopes() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.SCOPED)

    with container.create_scope() as scope1:
        inst1 = scope1.resolve(_Logger)
    with container.create_scope() as scope2:
        inst2 = scope2.resolve(_Logger)
    assert inst1 is not inst2


def test_scoped_on_destroy_called_on_exit() -> None:
    destroyed: list[_Logger] = []
    container = Container()
    container.register(
        _Logger,
        lifetime=Lifetime.SCOPED,
        on_destroy=lambda inst: destroyed.append(inst),
    )

    with container.create_scope() as scope:
        instance = scope.resolve(_Logger)
    assert destroyed == [instance]


def test_scoped_resolves_singleton_from_container() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.SINGLETON)
    container.register(_Database, lifetime=Lifetime.SCOPED)

    singleton_logger = container.resolve(_Logger)

    with container.create_scope() as scope:
        db = scope.resolve(_Database)
        assert db.logger is singleton_logger


def test_scoped_without_scope_behaves_as_transient() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.SCOPED)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is not b


def test_scoped_on_create_hook() -> None:
    created: list[_Logger] = []
    container = Container()
    container.register(
        _Logger,
        lifetime=Lifetime.SCOPED,
        on_create=lambda inst: created.append(inst),
    )

    with container.create_scope() as scope:
        instance = scope.resolve(_Logger)
        # Second resolve should not trigger on_create again
        scope.resolve(_Logger)
    assert created == [instance]


# ------------------------------------------------------------------
# Lifetime enum via register()
# ------------------------------------------------------------------


def test_lifetime_singleton_via_enum() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.SINGLETON)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is b


def test_lifetime_transient_via_enum() -> None:
    container = Container()
    container.register(_Logger, lifetime=Lifetime.TRANSIENT)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is not b


def test_lifetime_takes_precedence_over_singleton_flag() -> None:
    container = Container()
    container.register(_Logger, singleton=True, lifetime=Lifetime.TRANSIENT)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is not b


class TestLazy:
    def test_lazy_does_not_resolve_until_used(self) -> None:
        created: list[str] = []

        class Expensive:
            def __init__(self) -> None:
                created.append("init")

            def value(self) -> int:
                return 42

        container = Container()
        container.register(Expensive, lifetime=Lifetime.SINGLETON)

        proxy = container.lazy(Expensive)
        assert created == []  # not resolved yet

        # First access triggers resolution
        result = proxy.value()
        assert result == 42
        assert created == ["init"]

    def test_lazy_caches_after_first_access(self) -> None:
        container = Container()
        container.register(_Logger, lifetime=Lifetime.SINGLETON)

        proxy = container.lazy(_Logger)
        first = proxy.get()
        second = proxy.get()
        assert first is second

    def test_lazy_get_returns_underlying_instance(self) -> None:
        container = Container()
        container.register(_Logger, lifetime=Lifetime.SINGLETON)
        proxy = container.lazy(_Logger)
        assert isinstance(proxy.get(), _Logger)

    def test_lazy_proxies_attribute_access(self) -> None:
        container = Container()
        container.register(_Logger, lifetime=Lifetime.SINGLETON)
        proxy = container.lazy(_Logger)

        proxy.log("hello")
        # Reaching back through the resolved instance shows the side-effect
        assert proxy.get().logs == ["hello"]

    def test_lazy_within_scope_resolves_per_scope(self) -> None:
        class Service:
            counter = 0

            def __init__(self) -> None:
                Service.counter += 1

        container = Container()
        container.register(Service, lifetime=Lifetime.SCOPED)

        with container.create_scope() as scope_a:
            proxy_a = scope_a.lazy(Service)
            proxy_a.get()  # resolves once

        with container.create_scope() as scope_b:
            proxy_b = scope_b.lazy(Service)
            proxy_b.get()  # resolves a second time in new scope

        assert Service.counter == 2

    def test_lazy_repr_indicates_state(self) -> None:
        container = Container()
        container.register(_Logger, lifetime=Lifetime.SINGLETON)
        proxy = container.lazy(_Logger)
        assert "pending" in repr(proxy)
        proxy.get()
        assert "resolved" in repr(proxy)

    def test_lazy_class_is_exported(self) -> None:
        # Smoke test: the public class is importable
        assert Lazy is not None
