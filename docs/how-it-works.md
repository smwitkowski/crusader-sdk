# How it works

The Python client sends command requests to the bridge. The bridge validates the command and arguments, serializes backend calls, and returns JSON. The real backend starts or attaches to the supported game under Linux/Wine, reads game state from process memory, and uses the included UCP3 module for tick control and a command mailbox. The module submits game commands through the game's own command queue. Some driver operations also write limited process memory directly.

## Memory boundary

The process-memory layer verifies the executable SHA-256 and that the verified file is mapped by the process, then requires a layout sanity check. It checks mappings and permissions on access, bounds each operation to a single mapped region and at most 1 MiB, and limits writes to fixed ranges or validated dynamic module regions. Dynamic hook addresses come from the module log. These checks reduce accidental misuse; they are not a security sandbox for a compromised local process or trusted driver. Arbitrary memory access is not exposed as a bridge command. The module mailbox includes in-game write and function-call primitives used by the trusted driver; a compromised same-user process or a driver bug could abuse them.

The backend depends on a specific executable and memory layout, process permissions, Wine and the module. Other versions can fail or behave incorrectly. The port and Docker integration have been tested offline only and still require a live game run. Game state and command support are not complete; in particular, `look` is refused by the current real backend.

The container starts UCP3 with `--ucp-no-security` so it can load the unsigned local module; this also enables the UCP3 console.
