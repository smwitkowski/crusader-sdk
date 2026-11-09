# Contributing

Issues are welcome for bug reports, questions, and suggestions. Please include steps to reproduce bugs and relevant environment details. Do not post security vulnerabilities publicly; follow [SECURITY.md](SECURITY.md).

Pull requests are by invitation. Please open an issue and discuss your proposed change before starting a pull request; wait for a maintainer to invite one.

## Local checks

From the repository root, install Python 3.10 or later and [uv](https://docs.astral.sh/uv/). Run these checks before submitting an invited pull request:

```sh
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest -q
sh scripts/leakcheck.sh
uv run python tools/gen_docs.py --check
```

Maintainers updating GitHub Actions pins should inspect each pinned revision’s `action.yml` and validate its inputs. With the GitHub CLI (`gh`) installed and authenticated, run `scripts/check-action-pins.sh` to verify that every remote workflow action pin resolves to a commit. This requires GitHub API access and does not verify release tags or attestations.

If `actionlint` is installed, also run `actionlint`. Optionally, run `uv run pre-commit run --all-files` for the configured hooks.

Do not include game files, credentials, or other material you cannot redistribute.
