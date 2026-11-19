#!/bin/sh
# Download a static Linux ffmpeg and the yt-dlp Linux binary into dist/livegrab-linux.
# Does not change system packages. The launcher puts dist/livegrab-linux/bin first on PATH.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DEST="$ROOT/dist/livegrab-linux"
CACHE="$ROOT/packaging/build/cache"
mkdir -p "$DEST/bin" "$DEST/app/livegrab_lib" "$DEST/app/static" "$CACHE"

fetch() {
  url=$1
  out=$2
  if [ -s "$out" ]; then
    return 0
  fi
  curl -fL --retry 3 -o "$out.partial" "$url"
  mv "$out.partial" "$out"
}

fetch "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux" \
  "$CACHE/yt-dlp_linux"
fetch "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
  "$CACHE/ffmpeg-release-amd64-static.tar.xz"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
tar -xJf "$CACHE/ffmpeg-release-amd64-static.tar.xz" -C "$work"
ffmpeg=$(find "$work" -type f -name ffmpeg | head -n 1)
ffprobe=$(find "$work" -type f -name ffprobe | head -n 1)
if [ -z "$ffmpeg" ] || [ -z "$ffprobe" ]; then
  echo "static ffmpeg archive did not contain ffmpeg and ffprobe" >&2
  exit 1
fi
cp "$ffmpeg" "$DEST/bin/ffmpeg"
cp "$ffprobe" "$DEST/bin/ffprobe"
cp "$CACHE/yt-dlp_linux" "$DEST/bin/yt-dlp"
chmod 755 "$DEST/bin/ffmpeg" "$DEST/bin/ffprobe" "$DEST/bin/yt-dlp"

cp "$ROOT/livegrab.py" "$DEST/app/livegrab.py"
find "$ROOT/livegrab_lib" -maxdepth 1 -name '*.py' -exec cp {} "$DEST/app/livegrab_lib/" \;
find "$ROOT/static" -maxdepth 1 -type f -exec cp {} "$DEST/app/static/" \;

cat > "$DEST/livegrab" << 'EOF'
#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
export PATH="$HERE/bin:${PATH:-}"
exec python3 "$HERE/app/livegrab.py"
EOF
chmod 755 "$DEST/livegrab"
echo "wrote $DEST"
