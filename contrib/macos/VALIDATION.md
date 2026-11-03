# Validation scope

Development was validated on macOS 26.7.1, Apple Silicon, with Guile 3.0.11,
GTK 3.24.52, GLib 2.90.1, Cairo 1.18.6 and Pango 1.58.2. This is a local
development result, not a compatibility matrix or CI certification.

## Clean-checkout verification (2026-11-03)

The build scripts were exercised in a new local clone containing only
committed files. Bootstrap, out-of-tree build and installation succeeded; the
working tree remained clean. `check.sh` passed all targeted checks, five geometry
cases and all 17 upstream liblepton tests.

`build-app.py` produced a bundle with 65 native libraries/modules plus its native
launcher. Its audit passed for all 66 arm64 images. After moving the bundle to a
path containing a space, a macOS sandbox denied reads from Homebrew, MacPorts,
the development workspace and the clean clone. In that sandbox, bundled native
libraries loaded, Scheme search paths had no build dependencies, and the public
TwoStageAmp example exported successfully to a gEDA netlist and valid SVG.
The GUI checks below were completed earlier on the same source fixes; this
clean-checkout run repeated the build, targeted tests, bundle audit and command
line runtime checks.

## Source fixes

- Release the GTK3 frame's Cairo context after drawing. The renderer supports
  explicitly clearing its context and safely reassigning the same context.
  The targeted test repeats attach/reuse/release 100 times. Manual window
  resizing remained stable after the fix.
- Normalize empty or NULL renderer font names to Sans. Explicit font choices
  remain intact. The test obtains real Pango/CoreText font metrics.
- Restore default window geometry when cached integers are missing or malformed.
  Tests retain actual configuration parsing and stub only native window moves.
- Advertise and read a native Quartz clipboard type while retaining the original
  MIME target. A standalone GTK probe reproduced the MIME round trip failure
  and successful native-type round trip on the tested GTK version.
- Allow an absolute `LEPTON_DATA_DIR` to replace both system data and system
  configuration search directories. Empty or relative values retain existing
  XDG/compiled-prefix behavior. Values are cached on first use. This keeps the
  application independent of its original installation prefix.

## Manual checks already completed

- Native Quartz display, with no DISPLAY/X11 server required.
- Opening, saving and reopening schematics; symbol selection, previews,
  placement and movement; attribute editing; rotation, mirroring, undo/redo;
  internal copy and system clipboard copy/paste, including application restart.
- Upstream TwoStageAmp round trip preserved a netlist of 23 components,
  12 nets and 42 pins. A separate private-library fixture also preserved its
  netlist; that fixture is intentionally not distributed.
- Export to SVG through the bundled command dispatcher and GUI print to PDF.
- LaunchServices startup after moving the application to a path containing
  spaces outside the build tree.
- Standalone runtime checks while access to Homebrew, MacPorts and the original
  workspace was denied. Loaded native images were confined to Apple system
  locations and the bundle. Bundled Scheme paths resolved inside the bundle.

The packaging audit checks arm64 native images, contained library references
and symlinks, absence of external rpaths, code signatures and relocated Scheme
paths. Runtime checks are still necessary: a static audit cannot prove that
every dynamically loaded module or application feature works.

## Limits and remaining work

- No Intel, older macOS or second-machine validation yet.
- No Developer ID signing or notarization.
- No Finder document associations or Dock document drop support.
- Existing Control-key shortcuts are retained; Command-key integration is pending.
- The separate attribute spreadsheet, sch2pcb workflow and external PCB tools
  are not included in the standalone bundle. Physical printing is untested.
- Cross-version clipboard compatibility needs testing. GTK atom warnings and
  a CUPS/D-Bus warning were observed in development and remain unresolved.
- Lepton Scheme modules run from source; startup performance needs measurement.
- Targeted checks and the 17 upstream liblepton tests have passed. The full
  upstream `make distcheck` has not been run; do that before proposing a PR
  under the repository's contribution guidelines.
