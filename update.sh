#!/usr/bin/env bash
# Query SignalRGB's package repos and print what needs bumping in signalrgb.spec.
# Usage: ./update.sh [stable|beta|alpha]
set -euo pipefail
channel="${1:-stable}"
base="https://pkgs.signalrgb.com"

if [ "$channel" = stable ]; then
  pkgurl="$base/apt/dists/stable/main/binary-amd64/Packages"
else
  # Arch db exists for all channels; apt only feeds stable reliably.
  echo "NOTE: apt channel '$channel' may not exist; using Arch repo data as reference." >&2
  pkgurl=""
fi

if [ -n "$pkgurl" ]; then
  tmp=$(mktemp)
  curl -fsSL "$pkgurl" -o "$tmp"
  version=$(awk '/^Version:/{print $2; exit}' "$tmp")
  sha=$(awk '/^SHA256:/{print $2; exit}' "$tmp")
  upstream_deb=$(awk '/^Filename:/{print $2; exit}' "$tmp")
  echo "Latest upstream ($channel):"
  echo "  Version:        $version"
  echo "  Filename:       $upstream_deb  (URL: https://pkgs.signalrgb.com/apt/$upstream_deb)"
  echo "  SHA256:         $sha"
  rm -f "$tmp"
else
  echo "point Source0 at the Arch repo and cross-check manually"
fi

echo
echo "Then verify the bundled-soname filter is still sufficient:"
echo "  (the %global bundled_sonames regex in signalrgb.spec should cover"
echo "   every internal library under /opt/signalrgb/lib in the new payload)"
