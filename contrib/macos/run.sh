#!/bin/sh
# Isolated development profile; requires this checkout and Homebrew.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tool=${1:-lepton-schematic}
if [ "$#" -gt 0 ]; then shift; fi
case "$tool" in
  lepton-*) case "$tool" in */*) exit 2;; esac ;;
  *) echo 'Expected an installed lepton-* tool name' >&2; exit 2 ;;
esac
prefix="$root/build/macos/install"
profile="$root/build/macos/runtime"
mkdir -p "$profile/home" "$profile/config" "$profile/cache" "$profile/data"
cd "$profile"
exec sh "$root/contrib/macos/build-env.sh" env \
  HOME="$profile/home" XDG_CONFIG_HOME="$profile/config" \
  XDG_CACHE_HOME="$profile/cache" XDG_DATA_HOME="$profile/data" \
  XDG_DATA_DIRS="$prefix/share:/opt/homebrew/share" \
  LEPTON_DATA_DIR="$prefix/share/lepton-eda" \
  GUILE_AUTO_COMPILE=0 GDK_BACKEND=quartz \
  LIBLEPTON="$prefix/lib/liblepton.dylib" \
  LIBLEPTONGUI="$prefix/lib/libleptongui.dylib" \
  "$prefix/bin/$tool" "$@"
