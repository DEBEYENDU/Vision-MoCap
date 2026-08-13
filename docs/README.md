# Documentation

Project documentation, references, and technical resources.

## Directory Structure

| Directory      | Purpose                                              |
|----------------|------------------------------------------------------|
| `architecture/`| Clean Architecture diagrams, layer descriptions      |
| `diagrams/`    | UML, flowchart, and data-flow diagrams              |
| `api/`         | API reference for internal and external interfaces   |
| `setup/`       | Installation guides, environment setup, dependencies |
| `research/`    | Papers, notes, and references on pose estimation     |
| `testing/`     | Test-suite and benchmark instructions                |
| `images/`      | Embedded images for documentation pages              |

## Key Documents

- [Architecture](architecture/ARCHITECTURE.md) — module map, data flow,
  threading model, design decisions.
- [Error Handling](architecture/ERROR_HANDLING.md) — exception
  hierarchy, failure paths, exit codes, resilience features.
- [Testing](testing/TESTING.md) — unit suite, GUI smoke test,
  benchmark script usage.

## Naming Conventions

- Markdown for text documents, PNG/SVG for images and diagrams.
- Keep documents focused: one concept per file.
