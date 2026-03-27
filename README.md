# philiprehberger-di

[![Tests](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-di.svg)](https://pypi.org/project/philiprehberger-di/)
[![License](https://img.shields.io/github/license/philiprehberger/py-di)](LICENSE)
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

## API

| Function / Class | Description |
|------------------|-------------|
| `Container()` | Create a new dependency injection container |
| `container.register(cls, factory?, singleton?)` | Register a class with optional factory and singleton flag |
| `container.resolve(cls)` | Resolve an instance, recursively injecting dependencies |
| `container.reset()` | Clear the singleton cache, keeping registrations |
| `inject(container)` | Decorator that resolves type-hinted params from the container |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## License

MIT
