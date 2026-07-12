# Temp

Temporary files created during development, testing, or runtime.

## What Belongs Here

- Render cache files
- Intermediate processing outputs
- Downloaded models during setup
- Screenshot captures during tests
- Any ephemeral file that can be safely deleted

## Notes

- Contents of this directory should be treated as **disposable**.
- Add `temp/` to `.gitignore` — never commit temporary files.
- Clean this directory periodically or on each application restart.
