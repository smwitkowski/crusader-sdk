# Security

Please report vulnerabilities privately using GitHub private vulnerability reporting for this repository. Do not disclose security vulnerabilities in public issues.

## Threat model

The bridge is a local, single-user tool that reads and writes game process memory. Keep it on loopback, set `CRUSADER_TOKEN`, and do not expose it to untrusted networks. Host, Origin, and JSON content-type checks reduce browser-based attacks; they do not protect against a compromised local process.

## Security review, 2026-11-15

| Check | Result |
|---|---|
| `pip-audit` on every locked dependency (all extras) | No known vulnerabilities |
| `gitleaks` over the full history (all refs) | No leaks |
| `bandit` (`src`, `tools`, `scripts`) | One Medium: `urlopen` accepted any URL scheme in the client. **Fixed**: `Game` now refuses anything but `http://` and `https://`. The remaining Lows are type-narrowing `assert`s after explicit checks, plus `pgrep`/`xdotool` run with argument lists and fixed names. |
| `semgrep` (`p/python`, `p/secrets`) | Two subprocess calls with argument lists (`pgrep`, `xdotool`/`docker exec` with an operator-set container name); no shell, no request data |
| Manual review of `crusader.bridge.server` | See below |

The bridge server's request handling holds up on manual review:
- **Requests.** Bodies are capped at 64 KiB before parsing. The Host check and loopback Origin check block DNS
  rebinding and browser pages. POSTs must be JSON, which rules out simple cross-site requests.
- **Token.** When it is set, the bearer token is compared in constant time as bytes.
- **Arguments.** They are type-checked against the command catalog, with unknown arguments refused and ranges bounded.
  No file path or shell command is built from request data.
- **Logs.** The call log stores only arguments that passed the size cap.

One change came out of the review: `crusader-bridge` now prints a warning when it binds beyond loopback without a
token, which is the documented Docker setup when `CRUSADER_TOKEN` is not set.
