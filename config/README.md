# Config

Application configuration files and environment-specific settings.

## What Belongs Here

- `config.json` — Main application configuration
- `logging.conf` — Logging level and output configuration
- `.env` — Environment variables (secrets managed separately)
- `defaults.json` — User-configurable default values

## Notes

- Do **not** commit secrets or API keys to version control.
- Use `.env.example` to document required environment variables.
- Configuration schemas should be validated at startup.
