#!/bin/sh
# Run a build command with Homebrew tools and without inherited SDK/library flags.
set -eu
if [ "$#" -eq 0 ]; then
  echo 'Usage: sh contrib/macos/build-env.sh COMMAND [ARG ...]' >&2
  exit 2
fi
macos_major=$(/usr/bin/sw_vers -productVersion | /usr/bin/cut -d. -f1)
exec /usr/bin/env -i \
  HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" \
  PATH='/opt/homebrew/opt/texinfo/bin:/opt/homebrew/opt/flex/bin:/opt/homebrew/opt/gettext/bin:/opt/homebrew/opt/libtool/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin' \
  LC_ALL=C CC=/usr/bin/clang CXX=/usr/bin/clang++ \
  PKG_CONFIG=/opt/homebrew/bin/pkg-config \
  PKG_CONFIG_LIBDIR="/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig:/opt/homebrew/opt/libffi/lib/pkgconfig:/opt/homebrew/Library/Homebrew/os/mac/pkgconfig/$macos_major" \
  LIBTOOLIZE=/opt/homebrew/opt/libtool/bin/glibtoolize \
  "$@"
