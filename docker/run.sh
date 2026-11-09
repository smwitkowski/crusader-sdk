#!/bin/sh
set -eu

# Verify the mounted source before copying and verify the copy before launch.
sh /opt/sdk/check-game-files.sh /game
cp -R /game/. /opt/crusader/
chmod -R u+rwX /opt/crusader
sh /opt/sdk/check-game-files.sh /opt/crusader
mkdir -p "$HOME/Stronghold Crusader/Saves"
if [ -d /game/Saves ]; then
    cp -R /game/Saves/. "$HOME/Stronghold Crusader/Saves/"
    chmod -R u+rwX "$HOME/Stronghold Crusader/Saves"
fi
cp -R /opt/ucp/. /opt/crusader/
mv /opt/crusader/binkw32.dll /opt/crusader/binkw32_real.dll
cp /opt/crusader/binkw32_ucp.dll /opt/crusader/binkw32.dll
cp /opt/sdk/ucp-config.yml /opt/crusader/ucp-config.yml
cp -R /opt/sdk/ucp3/crusader-bridge-0.1.0 /opt/crusader/ucp/modules/
cd /opt/crusader
Xvfb :99 -screen 0 1024x768x16 &
xvfb_pid=$!
attempt=0
until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
    if ! kill -0 "$xvfb_pid" 2>/dev/null || [ "$attempt" -ge 30 ]; then
        echo "Xvfb failed to start" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 1
done
wineboot -i
wineserver -w
wine reg add 'HKCU\Software\Wine\Drivers' /v Audio /d '' /f
wineserver -w
wine 'Stronghold Crusader.exe' --ucp-no-security &
exec /opt/venv/bin/crusader-bridge "$@"
