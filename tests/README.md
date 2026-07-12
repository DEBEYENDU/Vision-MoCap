# Tests

Automated test suite organized by scope and category.

## Directory Structure

| Directory       | Purpose                                                  |
|-----------------|----------------------------------------------------------|
| `unit/`         | Unit tests for individual classes / functions            |
| `integration/`  | Integration tests combining multiple modules             |
| `performance/`  | Performance benchmarks and regression tests              |
| `test_data/`    | Fixtures, mock recordings, and sample inputs for tests   |

## Running Tests

```bash
# All tests
pytest tests/

# By category
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

## Naming Conventions

- Test file: `test_<module_name>.py` (e.g. `test_pose_estimator.py`)
- Test function: `test_<scenario>_<expected_behavior>()`
- Fixtures in `conftest.py` at the appropriate level.
