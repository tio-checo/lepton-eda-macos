# Native macOS build (experimental)

This branch builds Lepton EDA with GTK3 and the native Quartz backend, without
an X11 server or XQuartz. The scripts currently target Apple Silicon with
Homebrew installed in `/opt/homebrew`. Intel Macs and older macOS versions have
not been validated. See [VALIDATION.md](VALIDATION.md) for the tested scope.

## Dependencies

Install Apple's Command Line Tools (`xcode-select --install`) and Homebrew.
Then install the build tools and runtime data:

```sh
brew install autoconf automake libtool pkgconf gettext texinfo flex gawk groff \
  guile gtk+3 adwaita-icon-theme hicolor-icon-theme shared-mime-info \
  gsettings-desktop-schemas librsvg python
```

The scripts use a clean environment with Homebrew's compiler tools and
`pkg-config` paths. They do not alter your shell configuration or installed
libraries. GTK must expose the `quartz` backend. Python 3.9 or later is required
for packaging. Dependency versions are reported by the preflight check.

## Build and check

Run from the repository root:

```sh
sh contrib/macos/preflight.sh
sh contrib/macos/build.sh
sh contrib/macos/check.sh
sh contrib/macos/run.sh
```

The build uses `--with-gtk3 --disable-attrib --disable-update-xdg-database`.
This disables the separate spreadsheet attribute editor; editing attributes
inside the schematic editor remains available. `BUILD_JOBS=4 sh
contrib/macos/build.sh` changes the parallel build limit (default: 6).

Build files, logs, installation and the isolated development profile live in
`build/macos/`. To launch another installed tool, use for example:

```sh
sh contrib/macos/run.sh lepton-cli --help
```

The development launcher changes the working directory to its private profile;
pass absolute paths for input and output files. It needs this checkout and
Homebrew. The bundle below is relocatable.

`check.sh` exercises renderer context ownership, font defaults, missing and
malformed geometry cache, relocatable data/config paths, and the upstream
`liblepton` tests. These checks do not replace manual GUI testing or the full
upstream test suite.

## Build the application

After a successful build and checks:

```sh
python3 contrib/macos/build-app.py
python3 contrib/macos/audit-app.py dist/LeptonEDA.app
open dist/LeptonEDA.app
```

The builder refuses to overwrite an existing application. Move the previous
bundle aside before rebuilding. It copies dependencies and runtime resources,
rewrites native library references, applies ad hoc signatures, and runs the
audit automatically. It writes dependency provenance to
`build/macos/reports/build-manifest.json`. The bundle contains Lepton source
at the current Git commit, a patch of tracked local changes, packaging source,
dependency license files and Homebrew receipts. Build from a clean committed
checkout so that the source archive includes all packaging files.

The application embeds Guile and includes GTK, fonts/icons support, schemas,
symbols and the upstream TwoStageAmp example. It does not require Homebrew at
runtime. Its default profile is `~/Library/Application Support/LeptonEDA-Quartz/`.
An absolute `LEPTON_BUNDLE_PROFILE` selects another isolated profile. Existing
gEDA configuration is not imported automatically. Add personal symbol libraries
through your own project configuration; no personal designs are included.

Bundled command line tools can be invoked directly:

```sh
dist/LeptonEDA.app/Contents/Resources/bin/lepton-cli --help
dist/LeptonEDA.app/Contents/Resources/bin/lepton-export --help
dist/LeptonEDA.app/Contents/Resources/bin/lepton-netlist --help
```

The bundle is locally ad hoc signed, without Developer ID signing or Apple
notarization. It is a development build, not a signed public binary release.
The minimum macOS version is conservatively set to the build host's major
version; this does not demonstrate compatibility with other macOS releases.

## Standalone reproductions

The optional probes below investigate dependency behavior. They are deliberately
excluded from `check.sh`: the clipboard probe replaces the system clipboard,
and the empty-font probe can crash on affected Pango/CoreText versions.

```sh
sh contrib/macos/build-env.sh sh -c '
  clang contrib/macos/tests/clipboard-repro.c \
    $(pkg-config --cflags --libs gtk+-3.0) -o build/macos/checks/clipboard-mime
  clang -DMIME=\"org.lepton-eda.schematic\" contrib/macos/tests/clipboard-repro.c \
    $(pkg-config --cflags --libs gtk+-3.0) -o build/macos/checks/clipboard-native
  clang contrib/macos/tests/pango-metrics-repro.c \
    $(pkg-config --cflags --libs pangocairo) -o build/macos/checks/pango-metrics
'
GDK_BACKEND=quartz build/macos/checks/clipboard-mime
GDK_BACKEND=quartz build/macos/checks/clipboard-native
build/macos/checks/pango-metrics 'Sans'
# Optional crash reproduction on affected versions:
build/macos/checks/pango-metrics ''
```

The Quartz clipboard workaround advertises a native type alongside the original
MIME target. Compatibility with other Lepton versions has not been established.
Do not register that native type in the application plist without retesting
GTK's type conversion in both directions.
