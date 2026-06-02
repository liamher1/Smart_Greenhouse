# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Strawberry Greenhouse IoT backend — ESP32 field sensors communicate over MQTT, a FastAPI async backend processes telemetry and issues actuation commands, and data flows through a domain-event-driven message bus into PostgreSQL. The system targets data-driven irrigation control (Brix optimization).

## Commands

All commands run from the repo root unless noted. The working directory for Python is `Backend/` with `src/` on the `PYTHONPATH`.

**Run the app:**
```bash
python Backend/main.py
```

**Start infrastructure (PostgreSQL + Mosquitto):**
```bash
docker-compose -f Backend/docker-compose.yml up -d
docker-compose -f Backend/docker-compose.yml down
```

**Run tests:**
```bash
# Unit tests only (no external dependencies)
pytest Backend/tests/unit/ -v

# Integration tests (require running Postgres — use docker-compose)
pytest Backend/tests/integration/ -v -m integration

# E2E tests (require Postgres + MQTT)
pytest Backend/tests/e2e/ -v -m e2e

# Single test file
pytest Backend/tests/unit/test_message_bus.py -v

# CI-style (unittest discover)
python -m unittest discover -s Backend/tests -p "test_*.py" -v
```

**Install dependencies:**
```bash
pip install -r Backend/requirements.txt
```

## Architecture

The backend is a **modular monolith** following Clean Architecture And Vertical Slices Architecture . Each feature lives in `Backend/src/features/<feature>/` and owns its own models, repository, event handlers, and entrypoints. Features communicate only through the shared `MessageBus` — never by importing each other's internals.

### Startup flow (`Backend/main.py`)

1. `Database.init()` — creates tables via SQLModel metadata
2. `MessageBus()` constructed and handlers registered (e.g., `TelemetryEventHandler`)
3. `MqttDriver` connects to broker; `entrypoints` register topic callbacks
4. `mqtt_driver.listen()` blocks in the async event loop

### Message flow (inbound MQTT → DB)

```
MQTT message
  → MqttDriver routes by topic pattern
    → Entrypoint translates JSON → domain Event (e.g., TelemetryRecorded)
      → MessageBus.handle(event)
        → TelemetryEventHandler persists via Repository
          → fresh async Session per message (transaction scope = one message)
```

### Message flow (HTTP → MQTT actuation)

```
POST /actuation
  → FastAPI router
    → ActuationService publishes MQTT command + registers a Future keyed by command_id
      → ActuationListener resolves the Future when ACK arrives on MQTT
        → HTTP response returned
```

### Key infrastructure in `Backend/src/base/infrastructure/`

| Module | Role |
|---|---|
| `message_bus.py` | Async dispatcher — Commands routed 1:1, Events routed 1:N to all registered handlers |
| `mqtt_driver.py` | Wraps `aiomqtt`; routes messages to callbacks by topic wildcard pattern |
| `database.py` | Async SQLAlchemy engine + `async_session` factory |

### Domain primitives in `Backend/src/base/domain/`

- **Command** — frozen dataclass, represents intent to change state, dispatched to exactly one handler
- **Event** — frozen Pydantic `BaseModel`, represents something that happened, dispatched to all registered handlers

### Feature slice conventions

Each feature under `Backend/src/features/<name>/` follows this layout:

- `models.py` — SQLModel table + any DTOs
- `repository.py` — async data-access, accepts `AsyncSession`
- `events.py` — domain events produced by this feature
- `handlers.py` — event/command handlers registered with the MessageBus
- `entrypoints.py` — translate external messages (MQTT JSON) → domain events
- `router.py` — FastAPI `APIRouter` (present only for features with HTTP endpoints)
- `service.py` — application logic (present for actuation)

### Configuration

`Backend/src/config.py` uses Pydantic `BaseSettings`. All values are loaded from `Backend/.env`:

```
DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT
MQTT_BROKER_IP, MQTT_PORT, MQTT_TOPIC_PREFIX
```

### Test structure

- **Unit** — fake/mock dependencies, no I/O; test MessageBus routing, entrypoint parsing, service logic
- **Integration** — real Postgres via `testcontainers`; test repository and handler persistence
- **E2E** — real Postgres + real MQTT; test full inbound message → DB flow

`pytest.ini` sets `asyncio_mode = auto` and adds `src/` to `pythonpath`, so all imports use the `src/`-rooted style (e.g., `from features.telemetry.models import TelemetryReading`).

### Windows note

`main.py` sets `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` — required for `aiomqtt` on Windows.
