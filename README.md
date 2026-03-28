# philiprehberger-di

[![Tests](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-di.svg)](https://pypi.org/project/philiprehberger-di/)
[![GitHub release](https://img.shields.io/github/v/release/philiprehberger/py-di)](https://github.com/philiprehberger/py-di/releases)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-di)](https://github.com/philiprehberger/py-di/commits/main)
[![License](https://img.shields.io/github/license/philiprehberger/py-di)](LICENSE)
[![Bug Reports](https://img.shields.io/github/issues/philiprehberger/py-di/bug)](https://github.com/philiprehberger/py-di/issues?q=is%3Aissue+is%3Aopen+label%3Abug)
[![Feature Requests](https://img.shields.io/github/issues/philiprehberger/py-di/enhancement)](https://github.com/philiprehberger/py-di/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-ec6cb9)](https://github.com/sponsors/philiprehberger)

Lightweight dependency injection container for Python.

## Installation

```bash
pip install philiprehberger-di
```

## Usage

```python
from philiprehberger_di import Container

container = Container()
container.register(Logger)
logger = container.resolve(Logger)
```

### Singletons

```python
container.register(Database, singleton=True)

a = container.resolve(Database)
b = container.resolve(Database)
assert a is b
```

### Custom Factories

```python
container.register(Cache, factory=lambda: Cache(max_size=256))
cache = container.resolve(Cache)
```

### Recursive Resolution

```python
class Service:
    def __init__(self, db: Database, logger: Logger) -> None:
        self.db = db
        self.logger = logger

container.register(Database)
container.register(Logger)
container.register(Service)
service = container.resolve(Service)  # db and logger are injected automatically
```

### Inject Decorator

```python
from philiprehberger_di import Container, inject

container = Container()
container.register(Logger, singleton=True)

@inject(container)
def handle_request(logger: Logger) -> str:
    logger.log("request handled")
    return "ok"

handle_request()  # logger is resolved and injected automatically
```

### Lifecycle Hooks

```python
container.register(
    Database,
    singleton=True,
    on_create=lambda db: db.connect(),
    on_destroy=lambda db: db.disconnect(),
)

db = container.resolve(Database)  # on_create called after creation
container.reset()                 # on_destroy called before clearing singletons
```

## API

| Function / Class | Description |
|------------------|-------------|
| `Container()` | Create a new dependency injection container |
| `container.register(cls, factory?, singleton?, on_create?, on_destroy?)` | Register a class with optional factory, singleton flag, and lifecycle hooks |
| `container.resolve(cls)` | Resolve an instance, recursively injecting dependencies |
| `container.reset()` | Call `on_destroy` for singletons with hooks, then clear the cache |
| `inject(container)` | Decorator that resolves type-hinted params from the container |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this package useful, consider starring the repository.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Philip%20Rehberger-blue?logo=linkedin)](https://www.linkedin.com/in/philiprehberger/)
[![More packages](https://img.shields.io/badge/More%20packages-philiprehberger-orange)](https://github.com/philiprehberger?tab=repositories)

## License

[MIT](LICENSE)
