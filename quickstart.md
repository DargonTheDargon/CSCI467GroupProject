# Project Setup Steps

Once you downloaded python, run the command:

```
pip install django
```

Install UV that makes it super easy to sync project dependencies across our repos

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

run:

```
python manage.py startapp polls
python manage.py runserver
python manage.py migrate
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
