#!/usr/bin/env bash
# CI helper: compare the pinned SignalRGB version in signalrgb.spec against the
# latest in the upstream apt repo. Prints a machine-readable report.
# Exit codes:
#   0 = up to date
#   1 = new upstream version available
#   2 = error
set -euo pipefail
spec_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="$spec_dir/signalrgb.spec"

pinned_version=$(awk '/^Version:/{print $2; exit}' "$spec")
pinned_rev=$(awk '/^%global buildrev/{print $3; exit}' "$spec")
pinned_sha=$(awk '/^%global deb_sha256/{print $3; exit}' "$spec")

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
curl -fsSL https://pkgs.signalrgb.com/apt/dists/stable/main/binary-amd64/Packages -o "$tmp"

latest_full=$(awk '/^Version:/{print $2; exit}' "$tmp")        # e.g. 2.5.86-7617
latest_version=${latest_full%-*}
latest_rev=${latest_full##*-}
latest_sha=$(awk '/^SHA256:/{print $2; exit}' "$tmp")
latest_file=$(awk '/^Filename:/{print $2; exit}' "$tmp")
latest_url="https://pkgs.signalrgb.com/apt/$latest_file"

echo "pinned = $pinned_version-$pinned_rev (sha256 $pinned_sha)"
echo "latest = $latest_version-$latest_rev (sha256 $latest_sha)"
echo "url    = $latest_url"

if [ "$pinned_version" = "$latest_version" ] && [ "$pinned_rev" = "$latest_rev" ]; then
  echo "STATUS: up-to-date"
  exit 0
fi
if [ "$pinned_sha" = "$latest_sha" ]; then
  echo "WARNING: version differs but sha256 identical?"
fi
echo "STATUS: update-available"
exit 1
