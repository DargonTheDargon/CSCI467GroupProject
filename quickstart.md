# Project Setup Steps

Once you downloaded python, run the command:

```
pip install django
```

Install UV, used for running a small virtual environment in the project, and lets us install multiple versions of python and sync our python dependencies together

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then go to a project directory:

```
django-admin startproject mysite djangotutorial
```

create `pyproject.toml` with:

```
[project]
name = "djangotutorial"
version = "0.1.0"
requires-python = ">=3.14"
```

run:

```
uv add django
```

activate the virtual environment:
```
.venv/Scripts/Activate
```

run:

```
python manage.py startapp polls
python manage.py migrate
python manage.py runserver
```

run:

```
git init
```

Create `.gitignore` file

Commit:

```
git add *
git commit -m "Initial commit"
```

# NOTE: OVERRIDE THE USER MODEL
