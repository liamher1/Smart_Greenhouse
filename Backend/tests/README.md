# Telemetry Test Suite

This folder contains telemetry-focused tests across three levels:

- `unit/`: Pure behavior tests for validation and dispatch logic.
- `integration/`: Session/transaction boundary tests around handler + repository seam.
- `e2e/`: In-process end-to-end flow from MQTT payload bytes to persisted model object.

Layer-specific docs:
- `Backend/tests/e2e/README.md`: Detailed explanation of telemetry e2e test flow and scope.

## Run all tests

```powershell
python -m unittest discover -s Backend/tests -p "test_*.py" -v
```

## Run by layer

```powershell
python -m unittest discover -s Backend/tests/unit -p "test_*.py" -v
python -m unittest discover -s Backend/tests/integration -p "test_*.py" -v
python -m unittest discover -s Backend/tests/e2e -p "test_*.py" -v
```

## CI

GitHub Actions runs the same suite using `.github/workflows/telemetry-tests.yml`.
It installs `Backend/requirements.txt` and executes:

```powershell
python -m unittest discover -s Backend/tests -p "test_*.py" -v
```


