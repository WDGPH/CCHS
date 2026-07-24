# Contributing to the CCHS Bootstrap Analysis Tool

Thank you for your interest in contributing! This project is open source under the
MIT license, and contributions of all kinds are welcome — bug reports, feature
requests, documentation improvements, and code.

## Reporting Issues

- Please use [GitHub Issues](../../issues) to report bugs or request enhancements.
- When reporting a bug, include steps to reproduce, what you expected, what happened,
  and your environment (OS, Python version).
- For security-sensitive issues, do **not** open a public issue — follow the process
  in [SECURITY.md](SECURITY.md) instead.

## Development Setup

This project uses [uv](https://astral.sh/uv) for dependency management.

```bash
uv sync                       # create the .venv and install dependencies
uv run streamlit run app.py   # run the app locally
```

Authoritative dependencies live in `pyproject.toml` (and `uv.lock`). Add a package
with `uv add package_name` and commit the updated manifest and lock file.

## Submitting Changes

1. **Fork** the repository and clone your fork.
2. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**, following the existing project structure. Application code
   lives under `app.py`, `config/`, and `src/`; supporting scripts live under `scripts/`.
4. **Test locally** to ensure existing functionality still works.
5. **Commit** with clear, descriptive messages:
   ```bash
   git commit -m "Add feature: short description"
   ```
6. **Push** your branch to your fork and **open a pull request** against the main
   repository. Include a summary of your changes and any relevant context.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use clear, descriptive variable and function names.
- Add docstrings and comments only where the intent is non-obvious.
- Keep code modular and avoid duplicating logic.

> Note: this project does not currently pin an autoformatter or linter in
> `pyproject.toml`. If you use one locally (e.g. `ruff` or `black`), keep changes
> scoped to the lines you are editing so diffs stay reviewable.

## Contact

For questions that are not suited to a public issue, you can reach the maintainer at
dna.automation@wdgpublichealth.ca.
