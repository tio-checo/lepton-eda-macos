#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
# Re-enter through the same environment used by build.sh.
if [ "${1:-}" != --inside ]; then
  exec sh "$root/contrib/macos/build-env.sh" sh "$0" --inside
fi
sw_vers
test "$(uname -m)" = arm64
git -C "$root" log -1 --format='%H %s'
for tool in clang pkg-config autoconf automake glibtoolize gettextize flex gawk makeinfo groff guile guild python3; do
  command -v "$tool"
done
for pkg in gtk+-3.0 gdk-3.0 glib-2.0 gio-2.0 cairo cairo-pdf cairo-png cairo-ps cairo-svg pangocairo pango gdk-pixbuf-2.0 guile-3.0; do
  echo "$pkg $(pkg-config --modversion "$pkg") $(pkg-config --variable=prefix "$pkg")"
done
targets=$(pkg-config --variable=targets gdk-3.0)
echo "GDK targets: $targets"
case "$targets" in *quartz*) ;; *) echo 'GTK must support Quartz' >&2; exit 1;; esac
