```pwsh
# Download project
git clone <repo>

# Install UV
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install python, create virtual environment, download dependency packages
uv sync

# Activate virtual environment
.venv/Scripts/activate

# Migrate database
python manage.py migrate

# Start development web server
python manage.py runserver
```
