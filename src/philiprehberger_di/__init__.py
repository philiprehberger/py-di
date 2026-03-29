"""Lightweight dependency injection container for Python."""

from __future__ import annotations

import enum
import functools
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, get_type_hints

__all__ = [
    "CircularDependencyError",
    "Container",
    "Lifetime",
    "Scope",
    "inject",
]

T = TypeVar("T")


class Lifetime(enum.Enum):
    """Controls how instances are created and cached."""

    TRANSIENT = "transient"
    SINGLETON = "singleton"
    SCOPED = "scoped"


class CircularDependencyError(Exception):
    """Raised when a circular dependency chain is detected during resolution."""

    def __init__(self, chain: list[type]) -> None:
        self.chain = chain
        names = " -> ".join(t.__qualname__ for t in chain)
        super().__init__(f"Circular dependency detected: {names}")


@dataclass
class _Registration:
    """Internal record for a registered service."""

    factory: Callable[..., Any]
    lifetime: Lifetime
    on_create: Callable[..., None] | None = field(default=None)
    on_destroy: Callable[..., None] | None = field(default=None)


class Scope:
    """A child scope where scoped services are singletons within that scope.

    Created via :meth:`Container.create_scope`. When used as a context manager,
    on_destroy hooks are called for scoped singletons on exit.
    """

    def __init__(self, container: Container) -> None:
        self._container = container
        self._instances: dict[type, Any] = {}

    def resolve(self, cls: type[T]) -> T:
        """Resolve *cls* within this scope.

        Scoped registrations are cached per-scope. Singletons delegate to the
        parent container. Transients are always freshly created.
        """
        return self._container._resolve(cls, scope=self)

    def __enter__(self) -> Scope:
        return self

    def __exit__(self, *exc: object) -> None:
        for cls, instance in self._instances.items():
            registration = self._container._registry.get(cls)
            if registration is not None and registration.on_destroy is not None:
                registration.on_destroy(instance)
        self._instances.clear()


class Container:
    """Dependency injection container with support for singletons, transients, and scoped lifetimes."""

    def __init__(self) -> None:
        self._registry: dict[type, _Registration] = {}
        self._singletons: dict[type, Any] = {}

    def register(
        self,
        cls: type[T],
        factory: Callable[..., T] | None = None,
        *,
        singleton: bool = False,
        lifetime: Lifetime | None = None,
        on_create: Callable[[T], None] | None = None,
        on_destroy: Callable[[T], None] | None = None,
    ) -> None:
        """Register a class with an optional factory and lifetime.

        If *factory* is ``None``, *cls* itself is used as the factory.

        The *singleton* parameter is a convenience shorthand: passing
        ``singleton=True`` is equivalent to ``lifetime=Lifetime.SINGLETON``.
        If both are provided, *lifetime* takes precedence.

        Args:
            cls: The type to register.
            factory: Optional callable used to create instances.
            singleton: If True, only one instance is created and cached.
            lifetime: Explicit lifetime control (TRANSIENT, SINGLETON, or SCOPED).
            on_create: Optional callback invoked after each instance is created.
            on_destroy: Optional callback invoked when a singleton is cleared via reset,
                        or when a scope exits (for scoped registrations).
        """
        if lifetime is None:
            lifetime = Lifetime.SINGLETON if singleton else Lifetime.TRANSIENT

        self._registry[cls] = _Registration(
            factory=factory if factory is not None else cls,
            lifetime=lifetime,
            on_create=on_create,
            on_destroy=on_destroy,
        )

    def resolve(self, cls: type[T]) -> T:
        """Resolve *cls* from the container, creating it if necessary.

        For singletons the instance is cached and reused on subsequent calls.
        Factory parameters that carry type-hint annotations are resolved
        recursively from the container.

        Raises:
            KeyError: If *cls* is not registered.
            CircularDependencyError: If a circular dependency chain is detected.
        """
        return self._resolve(cls, scope=None)

    def create_scope(self) -> Scope:
        """Create a child scope.

        Within the returned scope, services registered with
        ``lifetime=Lifetime.SCOPED`` behave as singletons (one instance per
        scope). Use as a context manager to ensure cleanup::

            with container.create_scope() as scope:
                svc = scope.resolve(MyService)
        """
        return Scope(self)

    def reset(self) -> None:
        """Clear the singletons cache, keeping registrations intact.

        Before clearing, calls ``on_destroy(instance)`` for each singleton
        whose registration includes an *on_destroy* callback.
        """
        for cls, instance in self._singletons.items():
            registration = self._registry.get(cls)
            if registration is not None and registration.on_destroy is not None:
                registration.on_destroy(instance)
        self._singletons.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(
        self,
        cls: type[T],
        *,
        scope: Scope | None,
        _chain: list[type] | None = None,
    ) -> T:
        """Core resolution logic shared by Container and Scope."""
        registration = self._registry.get(cls)
        if registration is None:
            raise KeyError(f"{cls!r} is not registered in the container")

        # Circular dependency detection
        if _chain is None:
            _chain = []
        if cls in _chain:
            raise CircularDependencyError([*_chain, cls])
        _chain = [*_chain, cls]

        # Singleton: always from the container-level cache
        if registration.lifetime is Lifetime.SINGLETON:
            if cls in self._singletons:
                return self._singletons[cls]  # type: ignore[return-value]
            kwargs = self._resolve_params(registration.factory, scope=scope, chain=_chain)
            instance = registration.factory(**kwargs)
            if registration.on_create is not None:
                registration.on_create(instance)
            self._singletons[cls] = instance
            return instance  # type: ignore[return-value]

        # Scoped: cached per scope (falls back to transient if no scope)
        if registration.lifetime is Lifetime.SCOPED and scope is not None:
            if cls in scope._instances:
                return scope._instances[cls]  # type: ignore[return-value]
            kwargs = self._resolve_params(registration.factory, scope=scope, chain=_chain)
            instance = registration.factory(**kwargs)
            if registration.on_create is not None:
                registration.on_create(instance)
            scope._instances[cls] = instance
            return instance  # type: ignore[return-value]

        # Transient (or scoped without a scope)
        kwargs = self._resolve_params(registration.factory, scope=scope, chain=_chain)
        instance = registration.factory(**kwargs)
        if registration.on_create is not None:
            registration.on_create(instance)
        return instance  # type: ignore[return-value]

    def _resolve_params(
        self,
        factory: Callable[..., Any],
        *,
        scope: Scope | None,
        chain: list[type],
    ) -> dict[str, Any]:
        """Inspect *factory* and resolve parameters that are registered types."""
        target = factory.__init__ if isinstance(factory, type) else factory  # type: ignore[misc]
        try:
            hints = get_type_hints(target)
        except Exception:
            hints = {}

        sig = inspect.signature(factory)
        kwargs: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue
            hint = hints.get(name)
            if hint is not None and hint in self._registry:
                kwargs[name] = self._resolve(hint, scope=scope, _chain=chain)

        return kwargs


def inject(container: Container) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that resolves a function's type-hinted parameters from *container*.

    Parameters whose type is registered in the container are resolved and
    passed as keyword arguments.  Unregistered parameters are left for the
    caller to supply.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            hints = get_type_hints(fn)
            sig = inspect.signature(fn)

            for name, param in sig.parameters.items():
                if name in kwargs:
                    continue
                hint = hints.get(name)
                if hint is not None and hint in container._registry:
                    kwargs[name] = container.resolve(hint)

            return fn(*args, **kwargs)

        return wrapper

    return decorator
