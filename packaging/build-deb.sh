#!/bin/sh
# Build dist/livegrab_0.1.0_all.deb. ffmpeg and yt-dlp are package dependencies.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

APP="$STAGE/usr/share/livegrab"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/bin" "$APP/livegrab_lib" "$APP/static" \
  "$STAGE/usr/share/doc/livegrab"

cp "$ROOT/packaging/debian/control" "$STAGE/DEBIAN/control"
cp "$ROOT/livegrab.py" "$APP/livegrab.py"
find "$ROOT/livegrab_lib" -maxdepth 1 -name '*.py' -exec cp {} "$APP/livegrab_lib/" \;
find "$ROOT/static" -maxdepth 1 -type f -exec cp {} "$APP/static/" \;

cat > "$STAGE/usr/bin/livegrab" << 'EOF'
#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/.." && pwd)
exec python3 "$ROOT/share/livegrab/livegrab.py"
EOF

cat > "$STAGE/usr/share/doc/livegrab/copyright" << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: livegrab

Files: *
Copyright: 2026 Livegrab contributors
License: LicenseRef-unspecified
 The upstream tree does not ship a separate license file.
EOF

chmod 755 "$STAGE" "$STAGE/usr/bin/livegrab"
find "$STAGE" -type d -exec chmod 755 {} \;
chmod 644 "$STAGE/DEBIAN/control" "$APP/livegrab.py" \
  "$APP/livegrab_lib/"*.py "$APP/static/"* \
  "$STAGE/usr/share/doc/livegrab/copyright"

mkdir -p "$ROOT/dist"
dpkg-deb --root-owner-group --build "$STAGE" "$ROOT/dist/livegrab_0.1.0_all.deb"
echo "wrote $ROOT/dist/livegrab_0.1.0_all.deb"
