# Contributing

Thank you for your interest in VisionMoCap. Please follow the
guidelines below to keep the project consistent and maintainable.

---

## Code Style

- **PEP 8** — Follow standard Python style conventions.
- **Type hints** — All function signatures must include type annotations.
- **Docstrings** — Use Google-style docstrings for all public modules,
  classes, and functions.
- **Clean Architecture** — Respect dependency rules:
  - `src/core/` has zero dependencies on other project packages.
  - Outer layers depend on inner layers, never the reverse.

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]
```

### Types

| Type       | Usage                                  |
|------------|----------------------------------------|
| `feat`     | A new feature                          |
| `fix`      | A bug fix                              |
| `refactor` | Code change that neither fixes nor adds |
| `test`     | Adding or updating tests               |
| `docs`     | Documentation changes                  |
| `style`    | Formatting, missing semicolons, etc.   |
| `chore`    | Build, CI, or tooling changes          |
| `perf`     | Performance improvements               |

### Examples

```
feat(recording): add pause/resume to recording session
fix(pose): handle missing landmark confidence gracefully
docs(readme): update installation instructions
```

## Branch Workflow

1. Create a feature branch from `main`:
   ```
   git checkout -b feat/<short-description>
   ```
2. Commit changes following the commit format above.
3. Run tests before pushing:
   ```
   pytest tests/
   ```
4. Open a pull request against `main`.
5. Ensure CI passes and request a review.

## Pull Request Guidelines

- Keep PRs focused on a single concern.
- Include a clear description of the change and motivation.
- Reference related issues with `Closes #<issue>`.
- Add or update tests to cover the change.

## Testing

- All new code must include tests.
- Run the full suite before submitting:
  ```bash
  pytest tests/
  ```
- Aim for high coverage on business logic in `src/core/` and `src/motion/`.
