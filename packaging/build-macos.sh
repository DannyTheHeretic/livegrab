#!/bin/sh
# Lay out Livegrab.app with the macOS yt-dlp binary and a macOS ffmpeg build
# inside Contents/MacOS. This script is not run on the Linux machine that
# builds the Windows installer and the Debian package.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
APP="$ROOT/dist/Livegrab.app"
MACOS="$APP/Contents/MacOS"
RES="$APP/Contents/Resources"
CACHE="$ROOT/packaging/build/cache"
mkdir -p "$MACOS" "$RES/livegrab_lib" "$RES/static" "$CACHE"

fetch() {
  url=$1
  out=$2
  if [ -s "$out" ]; then
    return 0
  fi
  curl -fL --retry 3 -o "$out.partial" "$url"
  mv "$out.partial" "$out"
}

fetch "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos" \
  "$CACHE/yt-dlp_macos"
fetch "https://evermeet.cx/ffmpeg/getrelease/zip" "$CACHE/ffmpeg-macos.zip"
fetch "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip" "$CACHE/ffprobe-macos.zip"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unzip -o "$CACHE/ffmpeg-macos.zip" -d "$work/ffmpeg"
unzip -o "$CACHE/ffprobe-macos.zip" -d "$work/ffprobe"
ffmpeg=$(find "$work/ffmpeg" -type f -name ffmpeg | head -n 1)
ffprobe=$(find "$work/ffprobe" -type f -name ffprobe | head -n 1)
if [ -z "$ffmpeg" ] || [ -z "$ffprobe" ]; then
  echo "macOS ffmpeg archive did not contain ffmpeg and ffprobe" >&2
  exit 1
fi
cp "$CACHE/yt-dlp_macos" "$MACOS/yt-dlp"
cp "$ffmpeg" "$MACOS/ffmpeg"
cp "$ffprobe" "$MACOS/ffprobe"
chmod 755 "$MACOS/yt-dlp" "$MACOS/ffmpeg" "$MACOS/ffprobe"

cp "$ROOT/livegrab.py" "$RES/livegrab.py"
find "$ROOT/livegrab_lib" -maxdepth 1 -name '*.py' -exec cp {} "$RES/livegrab_lib/" \;
find "$ROOT/static" -maxdepth 1 -type f -exec cp {} "$RES/static/" \;

cat > "$MACOS/livegrab" << 'EOF'
#!/bin/sh
MACOS=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$MACOS/../Resources" && pwd)
export PATH="$MACOS:${PATH:-}"
exec python3 "$ROOT/livegrab.py"
EOF
chmod 755 "$MACOS/livegrab"

cat > "$APP/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Livegrab</string>
  <key>CFBundleDisplayName</key>
  <string>Livegrab</string>
  <key>CFBundleIdentifier</key>
  <string>local.livegrab.app</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleExecutable</key>
  <string>livegrab</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
</dict>
</plist>
EOF

echo "wrote $APP"
