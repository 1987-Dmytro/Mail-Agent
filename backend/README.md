# Mail Agent Backend

FastAPI + LangGraph backend service for intelligent email management.

## Setup Instructions

### Python Virtual Environment Setup

A virtual environment isolates your project's Python dependencies from your system Python installation. This prevents version conflicts and ensures consistent behavior across different machines.

#### Option 1: Using venv (Recommended for Beginners)

##### macOS/Linux

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3.13 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Your prompt should now show (venv) prefix
# Example: (venv) user@computer:~/mail-agent/backend$

# Install dependencies (available in Story 1.2)
pip install -r requirements.txt

# Deactivate when done (optional)
deactivate
```

##### Windows

```cmd
REM Navigate to backend directory
cd backend

REM Create virtual environment
python -m venv venv

REM Activate virtual environment
venv\Scripts\activate

REM Your prompt should now show (venv) prefix

REM Install dependencies (available in Story 1.2)
pip install -r requirements.txt

REM Deactivate when done (optional)
deactivate
```

#### Option 2: Using Poetry (Advanced)

Poetry is a modern Python package manager that handles dependency resolution and virtual environments automatically.

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Navigate to backend directory
cd backend

# Install dependencies (creates virtual environment automatically)
poetry install

# Activate virtual environment
poetry shell

# Run commands within poetry environment
poetry run uvicorn app.main:app --reload
```

### When to Activate Virtual Environment

**Always activate your virtual environment** when working on the backend:

- Before installing packages (`pip install`)
- Before running the development server (`uvicorn`)
- Before running tests (`pytest`)
- Before running database migrations (`alembic`)
- Before running any Python scripts in the project

**How to check if activated:**
- Your command prompt should show `(venv)` prefix
- Run `which python` (macOS/Linux) or `where python` (Windows) - it should point to the venv directory

### Troubleshooting

#### "python3.13: command not found"

**Solution**: Install Python 3.13+ from [python.org](https://www.python.org/downloads/) or use your system's package manager:

```bash
# macOS (using Homebrew)
brew install python@3.13

# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv

# Windows: Download installer from python.org
```

#### "Permission denied" when activating (macOS/Linux)

**Solution**: The activation script might not be executable:

```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

#### Virtual environment activation not persisting

**Issue**: You need to activate the virtual environment in every new terminal session.

**Solution**: This is normal behavior. Always run `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows) when opening a new terminal.

#### "pip: command not found" after activation

**Solution**: Ensure pip is installed in the virtual environment:

```bash
# Deactivate and recreate virtual environment
deactivate
rm -rf venv
python3.13 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Upgrade pip
pip install --upgrade pip
```

#### Dependencies not installing correctly

**Solution**: Upgrade pip and try again:

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### "SSL: CERTIFICATE_VERIFY_FAILED" errors

**Solution**: Update your system's SSL certificates:

```bash
# macOS
/Applications/Python\ 3.13/Install\ Certificates.command

# Ubuntu/Debian
sudo apt install ca-certificates

# Windows: Usually fixed by reinstalling Python with default settings
```

## Environment Configuration

See `backend/.env.example` for required environment variables.

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**⚠️ Important**: Never commit `.env` files to version control.

## Running the Development Server

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start FastAPI development server (available in Story 1.2)
uvicorn app.main:app --reload

# Server will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## Running Tests

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Run all tests (available in Story 1.10)
pytest

# Run with coverage
pytest --cov=app tests/
```

## Database Migrations

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Create new migration (available in Story 1.3)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Project Structure (Coming in Story 1.2)

The backend will be populated using the FastAPI + LangGraph production template:

```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Configuration and security
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── alembic/          # Database migrations
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variables template
└── README.md         # This file
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Python venv Documentation](https://docs.python.org/3/library/venv.html)
- [Poetry Documentation](https://python-poetry.org/docs/)

---

**Last Updated**: 2025-11-03
