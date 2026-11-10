# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Before 1.0, minor versions may change the command set.

## [Unreleased]

## [0.1.0a1] - 2026-11-09

First public pre-release.

### Added
- Python client (`crusader.Game`) with typed results, standard library only.
- Bridge server (`crusader-bridge`) exposing every command over REST and MCP, bound to 127.0.0.1 by default, with an
  optional bearer token, Host/Origin checks and request size limits.
- Game driver for Stronghold Crusader HD 1.41 under Wine, with all memory access through a checked boundary
  (exe hash, mapped regions, write allowlist).
- UCP3 module `crusader-bridge` and a Docker setup that uses your own game files.
- Command reference, concepts and protocol docs, plus `llms.txt` and `llms-full.txt`.

### Known limitations
- Tested offline only; the first live run against the game is pending.

[Unreleased]: https://github.com/smwitkowski/crusader-sdk/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/smwitkowski/crusader-sdk/releases/tag/v0.1.0a1
