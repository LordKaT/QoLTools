#!/usr/bin/env bash
set -euo pipefail

CACHE_DIR="$HOME/.local/share/discord-updater"
DOWNLOAD_URL="https://discord.com/api/download?platform=linux&format=deb"
mkdir -p "$CACHE_DIR"

get_installed_version() {
  dpkg-query -W -f='${Version}' discord 2>/dev/null || echo "none"
}

get_remote_version() {
  local redirect
  redirect=$(curl -Ls -o /dev/null -w "%{url_effective}" "$DOWNLOAD_URL")
  echo "$redirect" | grep -oP '(?<=discord-)[0-9.]+(?=\.deb)'
}

download_version() {
  local version="$1"
  local pkg_path="$CACHE_DIR/discord-${version}.deb"

  if [[ -f "$pkg_path" ]]; then
    echo "Cached copy of Discord $version found." >&2
  else
    echo "Downloading Discord $version..." >&2
    # -sS keeps stdout clean; progress/errors go to stderr
    curl -sS -L -o "$pkg_path" "$DOWNLOAD_URL"
  fi

  # IMPORTANT: only the path is printed to stdout
  printf '%s\n' "$pkg_path"
}

restart_discord() {
  if pgrep -x discord >/dev/null; then
    echo "Restarting Discord..." >&2
    pkill -x discord
    nohup discord >/dev/null 2>&1 &
  fi
}

installed=$(get_installed_version)
remote=$(get_remote_version)

echo "Installed version: $installed"
echo "Available version: $remote"

if [[ "$installed" == "$remote" ]]; then
  echo "✅ Discord is already up to date."
  exit 0
fi

pkg_path="$(download_version "$remote")"

echo "Updating Discord from $installed → $remote..."
if [[ $EUID -eq 0 ]]; then
  apt install -y "$pkg_path"
else
  sudo apt install -y "$pkg_path"
fi

find "$CACHE_DIR" -maxdepth 1 -type f -name "discord-*.deb" ! -name "$(basename "$pkg_path")" -delete

restart_discord
echo "🎉 Discord updated to version $remote"
