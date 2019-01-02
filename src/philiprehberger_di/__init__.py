"""Lightweight dependency injection container for Python."""

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, get_type_hints

__all__ = ["Container", "inject"]

T = TypeVar("T")


@dataclass
class _Registration:
    """Internal record for a registered service."""

    factory: Callable[..., Any]
    singleton: bool


class Container:
    """Dependency injection container with support for singletons and transients."""

    def __init__(self) -> None:
        self._registry: dict[type, _Registration] = {}
        self._singletons: dict[type, Any] = {}

    def register(
        self,
        cls: type[T],
        factory: Callable[..., T] | None = None,
        *,
        singleton: bool = False,
    ) -> None:
        """Register a class with an optional factory and singleton flag.

        If *factory* is ``None``, *cls* itself is used as the factory.
        """
        self._registry[cls] = _Registration(
            factory=factory if factory is not None else cls,
            singleton=singleton,
        )

    def resolve(self, cls: type[T]) -> T:
        """Resolve *cls* from the container, creating it if necessary.

        For singletons the instance is cached and reused on subsequent calls.
        Factory parameters that carry type-hint annotations are resolved
        recursively from the container.
        """
        registration = self._registry.get(cls)
        if registration is None:
            raise KeyError(f"{cls!r} is not registered in the container")

        if registration.singleton and cls in self._singletons:
            return self._singletons[cls]  # type: ignore[return-value]

        kwargs = self._resolve_params(registration.factory)
        instance = registration.factory(**kwargs)

        if registration.singleton:
            self._singletons[cls] = instance

        return instance  # type: ignore[return-value]

    def reset(self) -> None:
        """Clear the singletons cache, keeping registrations intact."""
        self._singletons.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_params(self, factory: Callable[..., Any]) -> dict[str, Any]:
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
                kwargs[name] = self.resolve(hint)

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
