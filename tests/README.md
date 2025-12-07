# PlatoniCam Test Suite

This folder contains all tests and testing utilities for PlatoniCam.

## Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── backend/                 # Backend (Python) tests
│   ├── test_optimization.py # Optimization service tests
│   ├── test_onvif.ps1       # ONVIF integration test script
│   ├── test_wave.ps1        # WAVE VMS integration test script
│   ├── test_tracker.py      # Test result tracking utility
│   ├── save_test_result.py  # Save test results to JSON
│   ├── convert_image.py     # Image to base64 converter for testing
│   └── ai_outputs/          # AI optimization test results
└── frontend/                # Frontend tests (planned)
```

## Running Tests

### Python Tests (pytest)

```bash
# From project root
cd C:\projects\cam_whisperer

# Activate virtual environment
backend\venv\Scripts\activate

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/backend/test_optimization.py

# Run specific test
pytest tests/backend/test_optimization.py::TestOptimizationService::test_heuristic_fallback_plates
```

### Integration Tests (PowerShell)

```powershell
# ONVIF camera tests (requires cameras on network)
.\tests\backend\test_onvif.ps1

# WAVE VMS tests (requires WAVE server)
.\tests\backend\test_wave.ps1
```

## Test Utilities

### test_tracker.py
Tracks and analyzes AI optimization test results over time.

```bash
python tests/backend/test_tracker.py
```

### save_test_result.py
Saves API responses to JSON files for analysis.

```bash
python tests/backend/save_test_result.py <result.json>
```

### convert_image.py
Converts images to base64 for API testing.

```bash
python tests/backend/convert_image.py <image.jpg>
```

## AI Test Outputs

The `backend/ai_outputs/` folder stores historical optimization results:
- JSON files with full API responses
- `test_log.json` - Consolidated test log
- `TEST_REPORT.md` - Generated test report

## Adding New Tests

1. Create test files with `test_` prefix
2. Use fixtures from `conftest.py`
3. Follow existing test patterns
4. Run `pytest` to verify

## Coverage

To generate coverage reports:

```bash
pip install pytest-cov
pytest tests/ --cov=backend --cov-report=html
```
