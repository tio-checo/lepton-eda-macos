#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tools="$root/contrib/macos"
if [ "${1:-}" != --inside ]; then
  exec sh "$tools/build-env.sh" sh "$0" --inside
fi
prefix="$root/build/macos/install"
checks="$root/build/macos/checks"
mkdir -p "$checks"
cd "$checks"
for test in renderer-context-test renderer-font-test bundle-data-path-test; do
  # pkg-config emits compiler arguments, intentionally split here.
  clang "$tools/tests/$test.c" $(pkg-config --cflags --libs gtk+-3.0 pangocairo) \
    -L"$prefix/lib" -llepton -Wl,-rpath,"$prefix/lib" -o "$checks/$test"
done
./renderer-context-test
./renderer-font-test
for override in /private/tmp/lepton-test-data relative ''; do
  LEPTON_DATA_DIR="$override" ./bundle-data-path-test "$prefix/share/lepton-eda"
done
sh "$tools/run.sh" lepton-cli shell -s "$tools/tests/geometry-cache-test.scm"
sh "$tools/run.sh" lepton-cli shell -s "$tools/tests/recent-file-context-test.scm"
make -C "$root/build/macos/build/liblepton" check
