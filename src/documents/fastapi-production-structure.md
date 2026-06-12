# FastAPI Production Structure Guide

> Reverse-engineered from `autox-2.0-toolbox` — a production FastAPI service.
> Use this as the reference blueprint when creating or refactoring any FastAPI service.

---

## Complete Directory Tree

```
my-service/
│
├── main.py                          ← entry point (uvicorn runner)
├── pyproject.toml                   ← project metadata, dependencies, scripts
├── uv.lock                          ← locked dependency tree (commit this)
├── alembic.ini                      ← alembic config pointing to migrations/
├── Dockerfile                       ← multi-stage production image
├── .env                             ← local secrets (gitignored)
├── .env.example                     ← committed template with no real values
├── .gitignore
├── readme.md
│
├── resources/                       ← static/bundled assets (committed)
│   └── __init__.py
│
├── migrations/                      ← alembic migration scripts
│   ├── env.py                       ← alembic runtime config + metadata wiring
│   ├── script.py.mako               ← template for generated migration files
│   ├── README
│   └── versions/                    ← auto-generated migration files (committed)
│       └── <rev>_<slug>.py
│
└── src/                             ← all application source code
    ├── __init__.py
    ├── app.py                       ← FastAPI app factory + middleware + lifespan
    │
    ├── config/                      ← environment config and infrastructure setup
    │   ├── __init__.py
    │   ├── setting.py               ← pydantic-settings: all env vars in one place
    │   ├── db_config.py             ← SQLAlchemy engine + session factory
    │   └── lib_config.py            ← third-party lib initialization (logging, etc.)
    │
    ├── model/                       ← SQLAlchemy ORM models
    │   ├── __init__.py              ← re-exports all models (needed by alembic)
    │   ├── base.py                  ← DeclarativeBase + Auditable mixin
    │   ├── enums.py                 ← DB-level enums used in models
    │   └── <entity>.py              ← one file per ORM model
    │
    ├── schema/                      ← Pydantic request/response schemas
    │   ├── __init__.py
    │   ├── app_base_model.py        ← shared AppBaseModel (camelCase, from_attributes)
    │   └── <entity>/                ← one sub-package per domain entity
    │       ├── __init__.py
    │       └── <entity>_<purpose>_sch.py
    │
    ├── repo/                        ← database access layer
    │   ├── __init__.py
    │   ├── base_repo.py             ← generic CRUD BaseRepo[T]
    │   └── <entity>_repo.py        ← one file per entity, extends BaseRepo
    │
    ├── service/                     ← service interfaces (ABCs)
    │   ├── __init__.py
    │   └── <entity>_service.py      ← abstract class, defines the contract
    │
    ├── service_impl/                ← service implementations
    │   ├── __init__.py
    │   └── <entity>_service_impl.py ← concrete class, implements the ABC
    │
    ├── router/                      ← FastAPI route definitions
    │   ├── __init__.py              ← add_router(app) — registers all routers
    │   └── <entity>_router.py       ← one APIRouter per domain
    │
    ├── dependency/                  ← FastAPI Depends() wiring
    │   ├── __init__.py
    │   ├── database.py              ← get_session() — yields AsyncSession
    │   ├── repo.py                  ← get_<entity>_repo() — instantiates repos
    │   ├── service.py               ← get_<entity>_service() — wires repo → service
    │   └── external_api.py         ← get_<client>() — external HTTP client deps
    │
    ├── exception/                   ← error handling
    │   ├── __init__.py
    │   ├── custom_exception.py      ← typed exception classes
    │   └── handler.py               ← registers all exception handlers on the app
    │
    ├── security/                    ← auth/authz dependencies
    │   ├── __init__.py
    │   └── api_key_security.py      ← Security() dependency for API key validation
    │
    ├── shared/                      ← truly cross-cutting constants and utilities
    │   ├── __init__.py
    │   ├── response.py              ← Response[T] and PaginationResponse[T]
    │   ├── schema.py                ← shared Pydantic base schemas
    │   ├── app_const.py             ← string constants, header dicts, msg codes
    │   ├── enum.py                  ← application-level enums (not DB-level)
    │   └── api_msg/                 ← typed API message registry
    │       ├── __init__.py
    │       ├── api_msg.py           ← Message dataclass (code + text)
    │       ├── shared_api_msg.py    ← common messages (not_found, server_error, etc.)
    │       └── <entity>_api_msg.py  ← domain-specific messages
    │
    └── utils/                       ← stateless helper functions
        └── __init__.py
```

---

## File-by-File Reference

### Root Level

---

#### `main.py`
**Purpose:** The runnable entry point. Calls `uvicorn.run()` pointing at `src.app:app`.

**Why separate from `app.py`:** `app.py` is the FastAPI factory — it must be importable without side effects (for tests, for Alembic, for type checkers). `main.py` owns the decision to start a uvicorn server. Never put `uvicorn.run()` inside `app.py`.

```python
import uvicorn

def run():
    uvicorn.run("src.app:app", host="127.0.0.1", port=8090, reload=True)

if __name__ == "__main__":
    run()
```

**In Docker:** The CMD overrides this and calls `uvicorn src.app:app --host 0.0.0.0 --port 8000` directly for production settings (no `--reload`).

---

#### `pyproject.toml`
**Purpose:** Single source of truth for the project — name, version, Python requirement, dependencies, build system, and CLI scripts.

**Why `uv` instead of `pip`/`poetry`:** uv resolves and installs significantly faster. `uv sync` is the equivalent of `pip install -r requirements.txt` but uses the lockfile.

```toml
[project]
name = "my-service"
version = "0.1.0"
description = "..."
requires-python = ">=3.14"
dependencies = [
    "fastapi>=0.136.3",
    "sqlalchemy>=2.0.50",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
    "uvicorn>=0.49.0",
    "structlog>=26.1.0",
]

[project.scripts]
start = "main:run"   # run with: uv run start
```

---

#### `uv.lock`
**Purpose:** Exact, reproducible dependency versions. Commit this file. It is the equivalent of `package-lock.json` for Python.

Never manually edit. Regenerate with `uv lock` after changing `pyproject.toml`.

---

#### `alembic.ini`
**Purpose:** Alembic's config file. Points to the `migrations/` directory and sets the `sqlalchemy.url`.

**Key setting:** `script_location = migrations`. Override `sqlalchemy.url` at runtime via env var or in `migrations/env.py` to avoid hardcoding credentials here.

---

#### `.env` / `.env.example`
**`.env`** — local secrets. Always gitignored.
**`.env.example`** — committed, no real values, documents every required env var.

```bash
# .env.example
PROFILE=DEV
LOG_LEVEL=INFO
CORS_ORIGIN=["http://localhost:5173"]
DOCS_URL=/docs
REDOC_URL=/redoc
DATABASE=mydb
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=secret
```

---

#### `Dockerfile`
**Purpose:** Multi-stage production image.

**Why multi-stage:**
- `builder` stage installs all deps and compiles `.py` → `.pyc`
- `production` stage copies only the virtualenv and compiled bytecode — no source files, no build tools, smaller attack surface

**Security:**
- Non-root user (`appuser`) created and used at runtime
- `PYTHONDONTWRITEBYTECODE=1` — no `.pyc` leftover in writable dirs
- `PYTHONUNBUFFERED=1` — stdout/stderr not buffered (logs reach Docker immediately)

**Key lines:**
```dockerfile
# Compiles source to bytecode, then deletes .py files
RUN python -m compileall -b src/ && \
    find src/ -name "*.py" -type f -delete

# Non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser ...
USER appuser
```

---

#### `resources/`
**Purpose:** Static files bundled with the application — JSON configs, prompt templates, lookup tables, seed data, ML assets, etc. These are committed to the repo and shipped inside the Docker image.

Included in the `pyproject.toml` wheel build:
```toml
[tool.hatch.build.targets.wheel]
include = ["resources/**"]
```

Keep binary files small. Large model weights don't belong here.

---

### `migrations/`

---

#### `migrations/env.py`
**Purpose:** Alembic's runtime environment. It:
1. Imports your `Base.metadata` so Alembic knows about all models
2. Configures the DB connection for running migrations
3. Handles offline (SQL script) and online (live DB) migration modes

**Critical:** You must import all models here (or import `Base` from a module that already imports them), otherwise `--autogenerate` won't see the tables.

```python
from src.model.base import Base
# if models are spread across files, import them so metadata is populated:
import src.model  # this triggers src/model/__init__.py which imports all models

target_metadata = Base.metadata
```

#### `migrations/script.py.mako`
**Purpose:** Jinja-like template for every generated migration file. Contains the `upgrade()` and `downgrade()` function stubs. Rarely modified — only if you want to add boilerplate to every migration (e.g., a comment header).

#### `migrations/versions/`
**Purpose:** Auto-generated migration files. Commit these. Each file is one schema change with `upgrade()` (apply) and `downgrade()` (rollback).

**Migration workflow:**
```bash
# After adding/changing a model:
python -m alembic revision --autogenerate -m "add status to tools"

# Review the generated file in migrations/versions/, then:
python -m alembic upgrade head

# To rollback one step:
python -m alembic downgrade -1
```

---

### `src/`

---

#### `src/app.py`
**Purpose:** The FastAPI application factory. This is the file uvicorn points at.

Responsibilities:
- Create the `FastAPI()` instance with metadata
- Register middleware (CORS, security headers, request logging)
- Register exception handlers via `exception_handlers(app)`
- Register all routers via `add_router(app)`
- Define the `lifespan` context manager for startup/shutdown logic (DB init, connection pool warmup)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()   # runs create_all on startup (dev only; use migrations in prod)
    yield
    # teardown here if needed

app = FastAPI(lifespan=lifespan, root_path="/api", ...)
```

**`root_path="/api"`:** Sets the path prefix for all OpenAPI docs and schema generation. If your gateway strips `/api` before forwarding, set this to match.

---

### `src/config/`

**Purpose:** Everything that configures the application from the outside world (env vars, connection pools, third-party clients). Nothing else imports from here except to READ config — config never imports from business logic layers.

---

#### `src/config/setting.py`
**Purpose:** Single, validated, typed access point for all environment variables.

Uses `pydantic-settings` `BaseSettings`. On import, it reads from `.env` and the actual environment. Fails fast at startup if a required variable is missing.

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROFILE: str
    DATABASE_HOST: str
    DATABASE_PORT: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE: str
    CORS_ORIGIN: list[str]
    DOCS_URL: str | None = None
    APPLY_SECURITY_HEADER: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignores unknown env vars instead of erroring

@lru_cache
def get_setting() -> Settings:
    return Settings()
```

**`@lru_cache`:** Settings is parsed once and cached. Calling `get_setting()` everywhere is free after the first call. In tests, you can clear the cache to swap values.

**Rule:** All other files call `get_setting()` — they never read `os.environ` directly.

---

#### `src/config/db_config.py`
**Purpose:** Creates the SQLAlchemy async engine and session factory. Also provides `init_models()` for dev startup.

```python
engine = create_async_engine(
    f"postgresql+asyncpg://{s.DATABASE_USERNAME}:{s.DATABASE_PASSWORD}@...",
    poolclass=AsyncAdaptedQueuePool,
    pool_size=100,       # max persistent connections
    max_overflow=20,     # extra connections above pool_size under load
    pool_timeout=30,     # seconds to wait for a connection before error
    pool_recycle=1800,   # recycle connections after 30 min (avoids stale conn errors)
    echo=False,          # set True in dev to log all SQL
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # prevents lazy-load errors after commit
)
```

**`expire_on_commit=False`:** Without this, SQLAlchemy expires all attributes after a commit, which causes "MissingGreenlet" errors when you try to access them outside a session in async code.

**`init_models()`:** Calls `Base.metadata.create_all` — creates tables if they don't exist. Use in development. In production, use Alembic migrations instead.

---

#### `src/config/lib_config.py`
**Purpose:** Placeholder/home for initializing third-party libraries that need global setup (logging frameworks, tracing clients, feature flag SDKs, etc.).

Currently sparse. Grows as you add observability, APM, or external SDK setup that should run once at import time.

---

### `src/model/`

**Purpose:** SQLAlchemy ORM model definitions. Each file is one table. Models define the DB schema — they are the source of truth for Alembic autogenerate.

---

#### `src/model/base.py`
**Purpose:** Two things: the declarative base class that all models inherit, and the `Auditable` mixin.

```python
class Base(AsyncAttrs, DeclarativeBase):
    pass

class Auditable:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(SAUUID)
    updated_by: Mapped[UUID] = mapped_column(SAUUID)
```

**`AsyncAttrs`:** Enables async lazy loading on relationships. Without this, accessing a relationship outside an async context raises an error.

**`Auditable` mixin:** Mixin (not a Base subclass) so you can selectively apply it. Any model that needs audit columns does `class MyModel(Base, Auditable)`.

**Why `server_default=func.now()`:** The DB sets the timestamp, not Python. This ensures correctness even if the app clock is wrong or a migration script inserts rows directly.

---

#### `src/model/enums.py`
**Purpose:** Python `Enum` classes that map to database enum columns.

```python
class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    INVITED = "INVITED"
```

**`str, Enum`:** Inheriting from `str` makes the enum serializable to JSON directly and comparable with plain strings. SQLAlchemy's `Enum(UserStatus, native_enum=False)` stores it as a `VARCHAR`, not a PostgreSQL native ENUM type — this avoids migration headaches when adding new values.

---

#### `src/model/<entity>.py`
**Purpose:** One model per file. Keep models focused — only column definitions and relationships.

```python
class Tool(Base, Auditable):
    __tablename__ = 'tools'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    tool_type_id: Mapped[int] = mapped_column(ForeignKey("tool_types.id"))
    tool_type: Mapped["ToolType"] = relationship(back_populates="tools")
```

**TYPE_CHECKING guard on relationship imports:** Prevents circular import errors between models that reference each other:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.model.tool_type import ToolType
```

---

#### `src/model/__init__.py`
**Purpose:** Re-exports all models with wildcard imports. Critical for two things:
1. Alembic's `env.py` imports `Base` from here — the import side-effect registers all models with `Base.metadata`
2. Lets you write `from src.model import ToolType` instead of the full path

```python
from .tool_category import *
from .tool_type import *
from .tool import *
```

**If a model is missing from this file, Alembic will not see its table.**

---

### `src/schema/`

**Purpose:** All Pydantic models for request bodies, response payloads, and internal data transfer. Schemas are NOT ORM models — they define what goes in/out of the API.

---

#### `src/schema/app_base_model.py`
**Purpose:** The project-wide Pydantic base class. All schemas inherit this instead of `BaseModel` directly.

```python
class AppBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,       # snake_case Python ↔ camelCase JSON
        populate_by_name=True,          # accept both snake_case and camelCase in input
        from_attributes=True,           # allow .model_validate(orm_object)
    )
```

**`alias_generator=to_camel`:** The API speaks camelCase JSON (what frontends expect), the Python code uses snake_case. This one config handles the translation automatically.

**`from_attributes=True`:** Enables `ToolTypeDropdownSch.model_validate(tool_type_orm_object)`. Without this, you can't build a schema directly from an ORM model instance.

**`populate_by_name=True`:** Accepts both `toolName` and `tool_name` as input field names. Important so internal code can still use Python field names.

---

#### `src/schema/<entity>/`
**Purpose:** One sub-package per domain entity. Keeps schemas organized by domain, not by HTTP verb.

Name schemas by their purpose, not by CRUD operation:

```
src/schema/tool_type/
    __init__.py
    tool_type_dropdown_sch.py    ← for dropdown endpoint
    tool_type_list_sch.py        ← for list/table endpoint  
    tool_type_detail_sch.py      ← for get-by-id endpoint
    tool_type_create_sch.py      ← request body for create
    tool_type_update_sch.py      ← request body for update
```

**Why per-entity sub-packages instead of one flat schema/ directory:** As the service grows, a flat `schema/` with 30 files becomes unnavigable. Entity sub-packages group what changes together.

---

### `src/repo/`

**Purpose:** The only layer that touches the database. Repositories translate business intent ("get all active tools") into SQLAlchemy queries.

**Rule:** No business logic here. No conditional branching based on data values. Just query construction and execution.

---

#### `src/repo/base_repo.py`
**Purpose:** Generic, typed CRUD base that every repo inherits from.

```python
T = TypeVar("T", bound=Base)

class BaseRepo(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def get(self, id: int, db: AsyncSession | None = None) -> T | None: ...
    async def get_all(self, db: AsyncSession | None = None) -> list[T]: ...
    async def save(self, db_obj: T, db: AsyncSession) -> T: ...
    async def update(self, id: int, obj_data: dict, db: AsyncSession) -> T | None: ...
    async def delete(self, id: int, db: AsyncSession) -> bool: ...
```

**`db: AsyncSession | None = None`:** When `db` is `None`, the repo opens its own session via `AsyncSessionLocal`. When provided, it participates in the caller's transaction. This pattern supports both standalone calls and transactional coordination.

**`Generic[T]`:** Full type safety — `ToolTypeRepo.get(1)` returns `ToolType | None`, not `Any`.

---

#### `src/repo/<entity>_repo.py`
**Purpose:** Entity-specific repository. Extends `BaseRepo` and adds domain queries.

```python
class ToolTypeRepo(BaseRepo[ToolType]):
    def __init__(self):
        super().__init__(ToolType)

    # Custom query beyond CRUD:
    async def find_by_name(self, name: str, db: AsyncSession) -> ToolType | None:
        query = select(ToolType).where(ToolType.name == name)
        return await self._get(query, db)
```

Keep repos small. If a repo is getting very large, the domain might need splitting.

---

### `src/service/` and `src/service_impl/`

**Purpose:** Business logic. Split into interface (ABC) and implementation to enforce separation of concerns and enable testing with mock implementations.

---

#### `src/service/<entity>_service.py`
**Purpose:** Abstract base class (interface) declaring what the service can do. No implementation.

```python
from abc import ABC, abstractmethod

class ToolTypeService(ABC):
    @abstractmethod
    async def get_dropdown(self) -> list[ToolTypeDropdownSch]:
        pass

    @abstractmethod
    async def create(self, data: CreateToolTypeSchema, db: AsyncSession) -> ToolTypeDropdownSch:
        pass
```

**Why define an interface (ABC)?**
- The router depends on `ToolTypeService`, not `ToolTypeServiceImpl`. You can swap the implementation (e.g., for testing) without changing any router code.
- Makes the contract explicit — anyone reading the service file immediately knows what this service does.

---

#### `src/service_impl/<entity>_service_impl.py`
**Purpose:** The actual implementation. Receives its repo via constructor injection (not via `Depends` — that's the `dependency/` layer's job).

```python
class ToolTypeServiceImpl(ToolTypeService):
    def __init__(self, tool_type_repo: ToolTypeRepo) -> None:
        self.tool_type_repo = tool_type_repo

    async def get_dropdown(self) -> list[ToolTypeDropdownSch]:
        tool_types = await self.tool_type_repo.get_all()
        return [ToolTypeDropdownSch.model_validate(tt) for tt in tool_types]
```

**Business logic belongs here:** Validation rules, data transformation, cross-entity coordination, raising business exceptions.

**Never import from `router/` or `dependency/`** — those layers depend on this one, not the other way around.

---

### `src/router/`

**Purpose:** HTTP interface. Defines URLs, HTTP methods, request/response types, and delegates to services. Contains zero business logic.

---

#### `src/router/__init__.py`
**Purpose:** Single `add_router(app)` function that registers all `APIRouter` instances. The only file in the codebase that knows which routers exist.

```python
from fastapi import FastAPI
from src.router.tool_type_router import toolTypeRouter
from src.router.tool_router import toolRouter

def add_router(app: FastAPI):
    app.include_router(toolTypeRouter)
    app.include_router(toolRouter)
```

**Why not do this in `app.py`?** Keeps `app.py` clean. Adding a new router requires only touching `router/__init__.py`.

---

#### `src/router/<entity>_router.py`
**Purpose:** One `APIRouter` per domain entity.

```python
toolTypeRouter = APIRouter(prefix="/toolType", tags=["Tool Type"])

@toolTypeRouter.get("/dropdown", response_model=Response[list[ToolTypeDropdownSch]])
async def get_dropdown(service: Annotated[ToolTypeService, Depends(get_tool_type_service)]):
    resp = await service.get_dropdown()
    api_msg = ToolTypeAPIMsg.DROPDOWN_FETCHED
    return Response[list[ToolTypeDropdownSch]].build_success_resp(
        resp, api_msg.msg_code, api_msg.text()
    )
```

**`Annotated[ToolTypeService, Depends(...)]`:** Modern FastAPI style — the type annotation and the dependency are co-located. Cleaner than `service: ToolTypeService = Depends(get_tool_type_service)`.

**Router depends on `ToolTypeService` (abstract), not `ToolTypeServiceImpl`.**

---

### `src/dependency/`

**Purpose:** FastAPI's dependency injection wiring layer. This is where concrete classes are assembled and made available to routers via `Depends()`. It is the composition root of the application.

---

#### `src/dependency/database.py`
**Purpose:** Provides an `AsyncSession` to any route that needs direct DB access.

```python
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

The `async with` ensures the session is always closed (and the connection returned to the pool) even if the request handler raises.

Used in routers as: `db: AsyncSession = Depends(get_session)`

---

#### `src/dependency/repo.py`
**Purpose:** Factory functions for repository instances.

```python
def get_tool_type_repo() -> ToolTypeRepo:
    return ToolTypeRepo()
```

Simple now. In a future where repos require injected dependencies (e.g., a cache client), this is the correct place to wire them.

---

#### `src/dependency/service.py`
**Purpose:** Factory functions for service instances. Wires repos into services.

```python
def get_tool_type_service(
    tool_type_repo: ToolTypeRepo = Depends(get_tool_type_repo)
) -> ToolTypeService:
    return ToolTypeServiceImpl(tool_type_repo)
```

**Returns `ToolTypeService` (ABC), not `ToolTypeServiceImpl`.** The router receives the abstract type.

**The chain is:** `get_tool_type_service` → `get_tool_type_repo` → (no deps). FastAPI resolves this automatically.

---

#### `src/dependency/external_api.py`
**Purpose:** Factory functions for external HTTP clients. Follows the same pattern as `repo.py` but for outbound API clients.

```python
# Example when populated:
def get_payments_client() -> PaymentsApiClient:
    return PaymentsApiClient(base_url=get_setting().PAYMENTS_URL)
```

Kept separate from `service.py` because external clients have different lifecycle concerns (connection pooling, retry config, circuit breakers).

---

### `src/exception/`

**Purpose:** Centralized error handling. Two concerns: defining exception types and registering handlers that convert them to HTTP responses.

---

#### `src/exception/custom_exception.py`
**Purpose:** Typed business exception classes. These are raised in service layer code.

```python
class GenericException(Exception):
    def __init__(self, msg=None, msg_code=None, body=None, status_code=None):
        ...

class UnauthorizedException(Exception): ...
class ForbiddenException(Exception): ...
class ConflictException(Exception): ...
```

**Why typed exceptions instead of raising `HTTPException` in services?**
Services should not know about HTTP. Raising `HTTPException` in `service_impl/` couples business logic to the transport layer. Instead:
- Services raise `GenericException` / `ConflictException` / etc.
- The handler layer converts them to HTTP responses.

---

#### `src/exception/handler.py`
**Purpose:** Registers `@app.exception_handler()` callbacks for every exception type. Called once from `app.py`.

```python
def exception_handlers(app: FastAPI):

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        # Returns 422 with structured field-level error info
        ...

    @app.exception_handler(ConflictException)
    async def conflict_handler(_, exc):
        return JSONResponse(status_code=409, content=Response[Any](
            success=False, msg=exc.msg, msg_code=exc.msg_code
        ).model_dump())

    @app.exception_handler(Exception)
    async def catch_all(request, exc):
        # Last resort — logs and returns 500
        ...
```

**The `RequestValidationError` handler** returns structured field-level errors:
```json
{
  "success": false,
  "error_info": {
    "error_fields": ["email"],
    "details": [{"type": "value_error", "field": "email", "msg": "..."}]
  },
  "msg_code": "INVALID_PAYLOAD"
}
```

---

### `src/security/`

**Purpose:** Authentication and authorization dependencies used in routers.

---

#### `src/security/api_key_security.py`
**Purpose:** A reusable `Security()` dependency that validates an API key from a header.

```python
api_key_auth = APIKeyHeader(name='access_token', auto_error=False)

def is_authorized(api_key: str = Security(api_key_auth)):
    if api_key != get_setting().API_KEY:
        raise HTTPException(status_code=401, detail='forbidden')
```

Used in a router: `_: None = Depends(is_authorized)` or at the router level:
```python
router = APIRouter(dependencies=[Depends(is_authorized)])
```

Grow this module as auth complexity increases (JWT validation, Keycloak OIDC, OPA checks).

---

### `src/shared/`

**Purpose:** Cross-cutting code that multiple layers use. Nothing in `shared/` should import from `router/`, `service/`, or `repo/` — it forms the base of the dependency graph.

---

#### `src/shared/response.py`
**Purpose:** The standard API response envelope used by every endpoint.

```python
class Response(AppBaseModel, Generic[T]):
    success: bool = True
    msg: str | None = None
    msg_code: str | None = None
    body: T | None = None

    @staticmethod
    def build_success_resp(body: T, msg_code: str, msg: str) -> Response[T]:
        return Response(success=True, msg=msg, msg_code=msg_code, body=body)


class PaginationResponse(AppBaseModel, Generic[T]):
    success: bool = True
    msg: str | None = None
    msg_code: str | None = None
    total_pages: int = 0
    total_elements: int = 0
    page_elements: int = 0
    page_number: int = 0
    size: int = 0
    body: List[T]
```

**`Generic[T]`** gives full type safety on responses:
```python
response_model=Response[list[ToolTypeDropdownSch]]
```
FastAPI uses this for OpenAPI schema generation and response validation.

---

#### `src/shared/api_msg/`

**Purpose:** Typed, centralized API message registry. Prevents hardcoded strings scattered across the codebase.

**`api_msg.py` — the `Message` dataclass:**
```python
class Message:
    def __init__(self, code: str, msg: str | Callable[..., str]):
        self.msg_code = code
        self.msg = msg

    def text(self, *args, **kwargs) -> str:
        # Supports both static strings and format strings
        if callable(self.msg):
            return self.msg(*args, **kwargs)
        return str(self.msg).format(*args, **kwargs) if (args or kwargs) else str(self.msg)
```

**`shared_api_msg.py` — common messages:**
```python
class SharedAPIMsg(Enum):
    NOT_FOUND = Message("NOT_FOUND", "Resource not found.")
    INTERNAL_SERVER_ERROR = Message("INTERNAL_SERVER_ERROR", "Unexpected error occurred.")
    UNAUTHORIZED = Message("UNAUTHORIZED", "Unauthorized.")
```

**`<entity>_api_msg.py` — domain messages:**
```python
class ToolTypeAPIMsg(Enum):
    DROPDOWN_FETCHED = Message("TOOL_TYPE_DROPDOWN_FETCHED", "Tool type fetched successfully.")
    CREATED = Message("TOOL_TYPE_CREATED", "Tool type '{}' created successfully.")
    # .text("Wrench") → "Tool type 'Wrench' created successfully."
```

Used in routers: `api_msg = ToolTypeAPIMsg.DROPDOWN_FETCHED` then `api_msg.msg_code` and `api_msg.text()`.

---

#### `src/shared/app_const.py`
**Purpose:** Named string constants that don't fit in enums — error code strings, header dictionaries, magic values.

```python
class Headers:
    stream_headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
    }

class APIMsgCode:
    TOKEN_INV = "token_inv"
    SOME_ERR_OCCURRED = "some_err_occurred"
```

---

#### `src/shared/enum.py`
**Purpose:** Application-level enums that are NOT tied to a database column (those live in `model/enums.py`). Cross-service concept enums, request filter enums, role/permission string enums.

```python
class ChatRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
```

---

#### `src/utils/`
**Purpose:** Pure stateless helper functions. No DB access, no HTTP calls, no side effects. Date formatters, string utilities, hash helpers, pagination calculators.

Currently empty — grows as needed. Never import from business layers here.

---

## Dependency Flow (Read-Only Directions)

```
router/
  │  depends on
  ▼
dependency/              ← wires everything together
  │  instantiates
  ├──────────────► service_impl/
  │                    │  depends on
  │                    ▼
  │               service/   (ABC — what)
  │
  └──────────────► repo/
                       │  depends on
                       ▼
                   model/     (ORM — tables)
                       │
                       ▼
                   config/db_config  (engine)
                       │
                       ▼
                   config/setting   (env vars)

shared/   ← imported by all layers, imports from nothing
schema/   ← imported by router, service, repo — imports from shared/
exception/ ← imported by app.py and service layer
security/  ← imported by router
```

**Nothing flows upward.** A lower layer never imports from a higher one.

---

## Adding a New Domain Entity — Checklist

When adding `Widget` to the service:

```
[ ] src/model/widget.py              — SQLAlchemy model
[ ] src/model/__init__.py            — add `from .widget import *`
[ ] src/schema/widget/               — create sub-package
[ ]   __init__.py
[ ]   widget_list_sch.py
[ ]   widget_create_sch.py
[ ]   widget_detail_sch.py
[ ] src/repo/widget_repo.py          — extends BaseRepo[Widget]
[ ] src/service/widget_service.py    — ABC with method signatures
[ ] src/service_impl/widget_service_impl.py  — implementation
[ ] src/router/widget_router.py      — APIRouter with endpoints
[ ] src/router/__init__.py           — add_router: include widgetRouter
[ ] src/dependency/repo.py           — add get_widget_repo()
[ ] src/dependency/service.py        — add get_widget_service()
[ ] src/shared/api_msg/widget_api_msg.py  — WidgetAPIMsg enum
[ ] migrations: alembic revision --autogenerate -m "add widgets table"
```

---

## Key Design Decisions Explained

| Decision | Why |
|---|---|
| `service/` (ABC) + `service_impl/` (concrete) | Routers depend on the interface. Swap implementations for tests without touching routers. |
| `dependency/` as a separate layer | Keeps `Depends()` wiring out of business logic. Services are plain classes, testable without FastAPI. |
| `shared/response.py` generic `Response[T]` | Single envelope for all endpoints. Type-safe. OpenAPI schema generation works correctly. |
| `api_msg/` enums instead of hardcoded strings | All user-facing messages in one place. Machine codes enable frontend i18n lookups. |
| `model/enums.py` vs `shared/enum.py` | DB enums (stored in columns) → `model/`. App-level enums (used in logic/schemas) → `shared/`. |
| `expire_on_commit=False` on session | Prevents MissingGreenlet errors when reading ORM attributes after an async commit. |
| `server_default=func.now()` on timestamps | DB sets timestamps, not Python. Reliable under any timezone configuration. |
| `from_attributes=True` on all schemas | `Schema.model_validate(orm_obj)` works everywhere. No manual `.to_dict()` mapping needed. |
| `alias_generator=to_camel` on AppBaseModel | Python stays snake_case internally, JSON is camelCase externally. One config, zero manual field renaming. |
