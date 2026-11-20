# Trace's own PyAV wheel, without x264 and x265

PyAV's Windows wheel on PyPI carries `libx264` and `libx265`, which are GPL. GPL code can't ship inside a closed,
paid app, so Trace uses its own build of the same PyAV with those two left out (Damo, 18 Nov 2026;
`docs/plans/lgpl-ffmpeg.md`). Everything else in FFmpeg is LGPL v3, and Trace's H.264 encoding goes through NVENC or
Windows' Media Foundation (`h264_mf`) instead.

## What builds it

`.github/workflows/pyav-lgpl.yml`, a GitHub Action. It runs by hand (Run workflow) or on a push to
`claude/pyav-lgpl` that touches the workflow or this folder. Four jobs:

1. **sources** checks the pinned tags still point at the pinned commits and downloads FFmpeg's and its libraries'
   source tarballs (upstream's own script, which checks each one's SHA-256).
2. **ffmpeg** builds FFmpeg for Windows x86_64 exactly as pyav-ffmpeg's workflow does (MSYS2, MinGW gcc,
   cibuildwheel), after `no_x264.py` has taken x264 and x265 out of `scripts/build-ffmpeg.py`.
3. **wheel** builds PyAV's cp312 win_amd64 wheel exactly as PyAV's workflow does, after `use_tarball.py` has pointed
   `scripts/ffmpeg-latest.json` at our FFmpeg tarball (a `file://` URL) instead of upstream's release.
4. **check** installs the wheel in a clean venv on a fresh runner and runs `check.py`: no x264 or x265 codec, file
   or configure flag, every FFmpeg library reports LGPL, FFmpeg's own H.264 decoder works and `h264_mf` is there.
   It also runs PyAV's own tests, report only (a few call `libx264` directly and are expected to fail).

The result is the artifact `pyav-lgpl-v19.0.2` (kept 90 days): the wheel, the FFmpeg tarball, these scripts and
`SOURCES.txt` (the upstream commits, the run, and the SHA-256 of the wheel and tarball).

## Where the wheel is kept

In the repo: `vendor/wheels/av-19.0.2-cp312-abi3-win_amd64.whl`, with the run's `SOURCES.txt` beside it as
`av-19.0.2-SOURCES.txt`. The repo is private, so a release URL would need a token and the network to install; a file
in the repo needs neither. `pyproject.toml` pins `av==19.0.2` and its `[tool.uv.sources]` points Windows at that file
(other platforms take PyPI's); `uv lock` records the wheel's SHA-256 in `uv.lock`.

After a re-run (a new PyAV, or a fix):

1. Download the run's artifact (Actions, the run, Artifacts) and unzip it somewhere outside the repo.
2. Copy the wheel into `vendor/wheels` and its `SOURCES.txt` beside it as `av-<version>-SOURCES.txt`; delete the old
   pair. Check the wheel's SHA-256 matches the one in `SOURCES.txt`.
3. Update the version and file name in `pyproject.toml` (`dependencies` and `[tool.uv.sources]`), and the file name,
   `WHEEL_SHA256` and version in `tests/server/test_ffmpeg_licence.py`.
4. `uv lock`, then `uv sync`, then `uv run python -I tools/pyav-lgpl/check.py av --version <version>` and
   `uv run pytest tests\server`.

## Pinned versions

| What | Tag | Commit |
| --- | --- | --- |
| PyAV-Org/PyAV | `v19.0.2` | `a4ad0133b13eb84067dc6e8105eb1fc8f8b93c4f` |
| PyAV-Org/pyav-ffmpeg (FFmpeg 9.0.2) | `9.0.2-4` | `6f3eed7b641b0095a965786c182de03f9aefcc59` |

Why `9.0.2-4` and not the `9.0.2-1` that PyAV v19.0.2's `scripts/ffmpeg-latest.json` names: `9.0.2-1` can't be
rebuilt as pinned (its lame source, `basswood-io/lamer`, was renamed `bwlame` and GitHub's archive of it changed
hash), and `9.0.2-4` is the same FFmpeg 9.0.2 with `bwlame` 4.1.0 pinned instead. We never accept a changed hash.
`use_tarball.py` checks PyAV still names exactly `9.0.2-1` and says in the log that the tarball is `9.0.2-4`.

What `9.0.2-4` changes from `9.0.2-1`, for Windows: libass is built in (`--enable-libass`, the `subtitles` filter),
libpng is no longer built, newer SVT-AV1 (4.3.0), libvpl (2.17.0), AMF and NVENC headers; the sonic encoder and
decoder (FFmpeg's own, LGPL) are no longer disabled; the tarball keeps only FFmpeg's headers and the DLLs and
import libraries needed at run time (`is_shipped`); the build uses CPython 3.12 for its dummy wheel. Nothing PyAV
v19.0.2 links against by name changed (avformat, avcodec, avdevice, avutil, avfilter, swscale, swresample).

## What is in the FFmpeg build, and its licence

FFmpeg itself is LGPL v3 here (`--enable-version3`). With x264 and x265 gone, every other library is
permissive or LGPL (from each project's licence file; re-check when a pin changes):

| Library | Licence |
| --- | --- |
| dav1d (AV1 decoder) | BSD-2-Clause |
| SVT-AV1 (AV1 encoder) | BSD-3-Clause-Clear, with the Alliance for Open Media Patent License 1.0 |
| libvpx (VP8, VP9) | BSD-3-Clause |
| libwebp, libwebpmux, libsharpyuv | BSD-3-Clause |
| opus | BSD-3-Clause |
| bwlame (libmp3lame; linked into avcodec, no DLL of its own) | LGPL-2.0-or-later (its source headers; the repo's LICENSE is the 2.1 text, which "or later" allows) |
| libvmaf | BSD-2-Clause-Patent |
| libvpl (Intel QSV dispatcher) | MIT |
| NVENC and AMF headers (`nv-codec-headers`, AMF) | MIT |
| libass (new in 9.0.2-4; linked into avfilter, no DLL of its own) | ISC |
| FreeType (for libass) | FreeType Licence (FTL; dual with GPL-2.0, we take FTL, which asks for a credit line) |
| FriBidi (for libass) | LGPL-2.1 |
| HarfBuzz (for libass) | Old MIT |
| libunibreak (for libass) | Zlib |
| zlib, libiconv, libwinpthread, libgcc, libstdc++ (from MinGW) | Zlib, LGPL-2.1, MIT and BSD, GPL with the GCC runtime exception |

`check.py` prints every DLL in the tarball and the wheel, so the run's log shows exactly what ships.

## How upstream gets x264 in without `--enable-gpl`

pyav-ffmpeg's `patches/ffmpeg.patch` edits FFmpeg's `configure`, moving `libx264` and `libx265` from its GPL list
to its "version 3" list. With `--enable-version3` FFmpeg then builds them in and reports "LGPL version 3 or later",
though x264 and x265 themselves are GPL v2 or later. That is why the PyPI wheel's licence string can't be trusted,
and why `check.py` looks for the codecs, files and flags rather than the licence line alone. We leave that patch in
place: with the two libraries neither built nor enabled, it changes nothing.

## What our two scripts change

`no_x264.py` (in pyav-ffmpeg's `scripts/build-ffmpeg.py`): `--enable-libx264` and `--enable-libx265` become
`--disable-libx264 --disable-libx265`, and the `x264` and `x265` packages are dropped from the build list. It fails
if those lines are not there exactly once.

`use_tarball.py` (in PyAV's `scripts/ffmpeg-latest.json`): the upstream URL becomes a `file://` URL to our tarball.
It fails unless the json names exactly the pyav-ffmpeg tag we expect (`9.0.2-1` for v19.0.2).

## A new PyAV

1. Read the new tag's `scripts/ffmpeg-latest.json` in PyAV-Org/PyAV for its pyav-ffmpeg tag: that is
   `PYAV_PINS_FFMPEG_TAG`, and normally `PYAV_FFMPEG_TAG` too (unless that tag can't be rebuilt, as above).
2. Get both tags' commits (`git ls-remote https://github.com/PyAV-Org/PyAV refs/tags/<tag>`, the same for
   pyav-ffmpeg) and set the five `PYAV_*` values in the workflow's `env`.
3. Compare upstream's Windows steps (pyav-ffmpeg's `.github/workflows/build-ffmpeg.yml`, PyAV's
   `.github/workflows/tests.yml`) with the steps marked "as upstream" in ours, and copy any change.
4. Push, run, read `check`. If `no_x264.py` fails, upstream moved the lines: read `build-ffmpeg.py` and update its
   `EDITS`.

## What LGPL asks of Trace when it ships

- FFmpeg's licence (LGPL v3, and the licences of the libraries bundled with it) in the installer and the app's About.
- FFmpeg's DLLs kept as separate files beside av (as the wheel already has them in `av.libs`), so they can be
  swapped. Never link them into one binary.
- The exact source offered: the two upstream repositories at the commits above, plus this folder's scripts and the
  workflow. A link in the licence notice to those, kept for as long as Trace ships that build, does it.
