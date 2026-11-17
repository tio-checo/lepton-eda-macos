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
  gsettings-desktop-schemas librsvg python meson ninja
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
`liblepton` tests. It also checks window/toplevel context when reopening recent
files. These checks do not replace manual GUI testing or the full
upstream test suite.

## Build the application

After a successful build and checks:

```sh
python3 contrib/macos/prepare-gtk.py
python3 contrib/macos/build-app.py
python3 contrib/macos/audit-app.py dist/LeptonEDA.app
open dist/LeptonEDA.app
```

`prepare-gtk.py` downloads GTK 3.24.52, verifies its pinned SHA256, applies
`patches/gtk3-quartz-print-preview.patch`, and builds a private Quartz copy in
`build/macos/gtk/`. It leaves Homebrew unchanged. Meson and Ninja may also be
provided with `--meson /absolute/path/to/meson --ninja /absolute/path/to/ninja`.
For a custom `--work` directory, set `LEPTON_GTK_PREFIX` to its `install/`
subdirectory when running `build-app.py`. A matching completed build is reused;
changed patches require a fresh work directory. The bundle includes the exact
GTK source archive, patch and build recipe.

On Quartz, Print Preview opens the generated PDF in the default macOS PDF
application through Launch Services. This replaces GTK's unsupported
`g_app_info_create_from_commandline()` path; drawing and page setup still use
the original GTK print operation. Previews are kept in
`~/Library/Application Support/LeptonEDA-Quartz/cache/gtk-3.0/print-preview/`.
Each preview has a unique name and private file permissions. On the next preview,
only matching cache PDFs older than seven days are removed; a failed launch
removes its PDF immediately. Custom `LEPTON_BUNDLE_PROFILE` values isolate this
cache too. Native PDF applications do not consume GTK/Evince's temporary print
settings file, so none is created for them.

The optional Quartz regression check runs the real GTK preview renderer and
captures the native viewer launch with a test-only interposer. It verifies the
original error, successful rendering, URI encoding, expiration and launch
failure cleanup, and ordinary PDF export. It needs a graphical macOS session:

```sh
python3 contrib/macos/tests/check-print-preview.py --work /private/tmp/lepton-preview-check
# Add --native to also open a real PDF viewer, or select the finished bundle:
python3 contrib/macos/tests/check-print-preview.py \
  --library-dir dist/LeptonEDA.app/Contents/Frameworks \
  --work /private/tmp/lepton-bundle-preview-check --native \
  --app dist/LeptonEDA.app
```

Use a new or empty test work directory. `--app` also calls Lepton's real
`x_print` with the bundled TwoStageAmp example in an isolated profile; a
test-only interposer selects preview without interacting with a printer.

The builder refuses to overwrite an existing application. Move the previous
bundle aside before rebuilding. It copies dependencies and runtime resources,
rewrites native library references, applies ad hoc signatures, and runs the
audit automatically. It writes dependency provenance to
`build/macos/reports/build-manifest.json`. The bundle contains Lepton source
at the current Git commit, a patch of tracked local changes, packaging source,
dependency license files and Homebrew receipts. Build from a clean committed
checkout so that the source archive includes all packaging files.

The application uses the upstream `libleptongui/data/lepton-schematic.svg`
artwork as its Finder/Dock icon. `make-icon.py` renders standard and Retina
representations from 16 to 1024 pixels into `LeptonEDA.icns`; the bundle audit
checks the icon resource and its `Info.plist` reference.

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
