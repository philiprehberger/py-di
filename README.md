# philiprehberger-di

[![Tests](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-di/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-di.svg)](https://pypi.org/project/philiprehberger-di/)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-di)](https://github.com/philiprehberger/py-di/commits/main)

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

### Circular Dependency Detection

The container detects circular dependencies during resolution and raises a
`CircularDependencyError` with the full dependency chain:

```python
from philiprehberger_di import CircularDependencyError

class A:
    def __init__(self, b: B) -> None: ...

class B:
    def __init__(self, a: A) -> None: ...

container.register(A)
container.register(B)

try:
    container.resolve(A)
except CircularDependencyError as e:
    print(e)  # Circular dependency detected: A -> B -> A
    print(e.chain)  # [A, B, A]
```

### Scoped Lifetime

Services registered with `Lifetime.SCOPED` are singletons within a scope but
differ across scopes:

```python
from philiprehberger_di import Container, Lifetime

container = Container()
container.register(RequestContext, lifetime=Lifetime.SCOPED)
container.register(Logger, lifetime=Lifetime.SINGLETON)

with container.create_scope() as scope:
    ctx1 = scope.resolve(RequestContext)
    ctx2 = scope.resolve(RequestContext)
    assert ctx1 is ctx2  # same within the scope

# on_destroy hooks are called when the scope exits
```

## API

| Function / Class | Description |
|------------------|-------------|
| `Container()` | Create a new dependency injection container |
| `container.register(cls, factory?, singleton?, lifetime?, on_create?, on_destroy?)` | Register a class with optional factory, lifetime, and lifecycle hooks |
| `container.resolve(cls)` | Resolve an instance, recursively injecting dependencies |
| `container.create_scope()` | Create a child scope for scoped lifetime management |
| `container.reset()` | Call `on_destroy` for singletons with hooks, then clear the cache |
| `inject(container)` | Decorator that resolves type-hinted params from the container |
| `Lifetime.TRANSIENT` | New instance on every resolve (default) |
| `Lifetime.SINGLETON` | Single shared instance across the container |
| `Lifetime.SCOPED` | Single instance per scope, transient without a scope |
| `CircularDependencyError` | Raised when a circular dependency chain is detected |
| `Scope` | Child scope returned by `create_scope()`, used as a context manager |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this project useful:

⭐ [Star the repo](https://github.com/philiprehberger/py-di)

🐛 [Report issues](https://github.com/philiprehberger/py-di/issues?q=is%3Aissue+is%3Aopen+label%3Abug)

💡 [Suggest features](https://github.com/philiprehberger/py-di/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

❤️ [Sponsor development](https://github.com/sponsors/philiprehberger)

🌐 [All Open Source Projects](https://philiprehberger.com/open-source-packages)

💻 [GitHub Profile](https://github.com/philiprehberger)

🔗 [LinkedIn Profile](https://www.linkedin.com/in/philiprehberger)

## License

[MIT](LICENSE)
