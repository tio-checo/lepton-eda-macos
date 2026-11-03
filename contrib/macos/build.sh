#!/bin/sh
# Build and install without changing the user's Homebrew installation.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tools="$root/contrib/macos"
work="$root/build/macos"
mkdir -p "$work/build" "$work/logs"
cd "$root"
sh "$tools/build-env.sh" ./autogen.sh > "$work/logs/bootstrap.log" 2>&1
cd "$work/build"
sh "$tools/build-env.sh" "$root/configure" \
  --prefix="$work/install" --with-gtk3 --disable-attrib \
  --disable-update-xdg-database > "$work/logs/configure.log" 2>&1
sh "$tools/build-env.sh" make -j"${BUILD_JOBS:-6}" > "$work/logs/build.log" 2>&1
sh "$tools/build-env.sh" make install > "$work/logs/install.log" 2>&1
echo "Installed in $work/install; logs in $work/logs"
