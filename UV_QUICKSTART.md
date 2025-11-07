# UV Quick Reference

## Installation
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup
```bash
cd backend
uv venv              # Creates .venv/
source .venv/bin/activate
uv sync              # Installs from pyproject.toml
```

## Common Commands
```bash
uv sync              # Install/update dependencies
uv add package       # Add new package
uv remove package    # Remove package
uv run python manage.py runserver  # Run command in venv
```

## Virtual Environment
- Created in `.venv/` directory (not `venv/`)
- Activated with: `source .venv/bin/activate`
- Or use: `uv run <command>` without activation

