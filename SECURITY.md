# Security

Please report vulnerabilities privately using GitHub private vulnerability reporting for this repository. Do not disclose security vulnerabilities in public issues.

## Threat model

The bridge is a local, single-user tool that reads and writes game process memory. Keep it on loopback, set `CRUSADER_TOKEN`, and do not expose it to untrusted networks. Host, Origin, and JSON content-type checks reduce browser-based attacks; they do not protect against a compromised local process.
