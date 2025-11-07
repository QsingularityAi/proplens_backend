# UV Setup Complete ✅

## What Was Configured

### 1. Created `pyproject.toml`
- All dependencies from `requirements.txt` migrated to `pyproject.toml`
- Configured for Python 3.9+ (3.11 recommended)
- Includes pytest configuration
- Compatible with both uv and pip

### 2. Created `.python-version`
- Specifies Python 3.11 as the recommended version
- Used by uv and pyenv

### 3. Updated `setup.sh`
- Automatically installs uv if not present
- Uses `uv venv` to create virtual environment
- Uses `uv sync` to install dependencies
- Creates `.venv/` directory (uv's default)

### 4. Updated Documentation
- `README.md` - Added uv setup instructions
- `UV_SETUP.md` - Detailed uv documentation
- `UV_QUICKSTART.md` - Quick reference guide
- Updated deployment instructions

### 5. Created `.gitignore`
- Ignores `.venv/` directory
- Ignores other Python/Django artifacts

## Quick Start

```bash
cd backend
uv venv              # Creates .venv/
source .venv/bin/activate
uv sync              # Installs all dependencies from pyproject.toml
```

## Benefits of UV

- ⚡ **10-100x faster** than pip
- 🔒 **Better dependency resolution**
- 📦 **Automatic virtual environment management**
- 🔄 **Compatible with pip** (requirements.txt still maintained)

## Virtual Environment Location

- **UV**: `.venv/` (created by `uv venv`)
- **Traditional**: `venv/` (created by `python -m venv`)

Both work, but uv uses `.venv/` by default.

## Running Commands

### With activation:
```bash
source .venv/bin/activate
python manage.py runserver
```

### Without activation (uv run):
```bash
uv run python manage.py runserver
uv run pytest
```

## Migration Notes

- `requirements.txt` is still maintained for compatibility
- `pyproject.toml` is the source of truth
- Both can be used, but uv prefers `pyproject.toml`

## Verification

To verify uv setup:
```bash
cd backend
uv --version        # Should show uv version
uv venv            # Should create .venv/
uv sync            # Should install all packages
```

## Troubleshooting

If uv is not found:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

If you prefer pip:
```bash
pip install -r requirements.txt  # Still works!
```



