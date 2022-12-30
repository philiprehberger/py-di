# Changelog

## 0.3.0 (2026-03-28)

- Add circular dependency detection with clear error messages
- Add `@inject` decorator for automatic parameter resolution
- Add scoped lifetime support with `container.create_scope()`
- Bring package into full compliance with guides

## 0.2.0 (2026-03-27)

- Add `on_create` lifecycle hook to `Container.register()` — called after each instance is created
- Add `on_destroy` lifecycle hook to `Container.register()` — called for singletons during `reset()`
- Add 8 badges to README (tests, PyPI, release, last updated, license, bugs, features, sponsor)
- Add Support section to README
- Add `.github/` templates (bug report, feature request, PR template, dependabot)

## 0.1.1 (2026-03-22)

- Add Changelog URL to project URLs
- Add `#readme` anchor to Homepage URL
- Add pytest and mypy configuration

## 0.1.0 (2026-03-21)

- Initial release
- `Container` class with `register`, `resolve`, and `reset` methods
- Singleton and transient lifetime support
- Recursive dependency resolution via type hints
- `inject` decorator for automatic parameter injection
