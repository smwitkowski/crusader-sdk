# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Before 1.0, minor versions may change the command set.

## [Unreleased]

### Changed
- Reference docs are complete: every building (footprint, cost, placement, purpose, staffing), unit, siege engine,
  good, event field and state field is documented, each command page lists its needs, costs, timing and refusals,
  and `docs/concepts.md` gains a game mechanics primer. Parameter constraints in the command catalog are filled in.
- Docs and README no longer say `advance` returns events; read them with `events`.

## [0.1.0] - 2026-11-10

### Fixed
- The memory boundary refused the UCP3 module's mailbox, which Wine maps as anonymous `rwxp` memory, so the bridge
  could not start against the real game. Anonymous executable private memory is now accepted; file-backed
  executable memory, the exe image and stacks are still refused.

### Changed
- `tools/smoke.py` advances the first month before building (a new skirmish pays out its starting gold and wood over
  about 640 ticks), builds its own mercenary post, and asks `find_sites` for more candidates.
- Docker docs: the container runs with `--cap-drop ALL` and no added capabilities (verified live).

### Verified
- First live run: all 12 `tools/smoke.py` steps pass against Stronghold Crusader HD 1.41 in the documented container.

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

[Unreleased]: https://github.com/smwitkowski/crusader-sdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/smwitkowski/crusader-sdk/compare/v0.1.0a1...v0.1.0
[0.1.0a1]: https://github.com/smwitkowski/crusader-sdk/releases/tag/v0.1.0a1
