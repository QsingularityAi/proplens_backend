# UV Configuration for Proplens AI Backend

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

## Quick Start

```bash
cd backend
uv venv              # Create virtual environment
source .venv/bin/activate
uv sync              # Install all dependencies
```

## Why UV?

- **10-100x faster** than pip for dependency resolution
- **Automatic virtual environment management**
- **Better dependency resolution**
- **Compatible with pip and requirements.txt**

## Installation

If uv is not installed, the setup script will install it automatically. Or install manually:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Usage

### Install dependencies
```bash
uv sync
```

### Add a new dependency
```bash
uv add package-name
```

### Remove a dependency
```bash
uv remove package-name
```

### Run commands in the virtual environment
```bash
uv run python manage.py runserver
uv run pytest
```

### Update dependencies
```bash
uv sync --upgrade
```

## Project Structure

- `pyproject.toml` - Main dependency configuration (used by uv)
- `requirements.txt` - Fallback for traditional pip users
- `.python-version` - Python version specification
- `.venv/` - Virtual environment (created by uv)

## Migration from pip

If you're already using pip, you can migrate to uv:

```bash
cd backend
uv venv
source .venv/bin/activate
uv sync  # Reads from pyproject.toml
```

The `requirements.txt` file is still maintained for compatibility, but `pyproject.toml` is the source of truth.

