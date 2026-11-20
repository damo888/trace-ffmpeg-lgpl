# PitchCraft Trace: the source of its FFmpeg (LGPL)

PitchCraft Trace, a Windows app by MatchdayLab, reads and writes video with FFmpeg 9.0.2 through PyAV 19.0.2. FFmpeg
and some of the libraries built with it are licensed under the GNU Lesser General Public License (LGPL). This
repository is how you get the exact source of the build inside Trace, and rebuild it.

Trace's FFmpeg is the normal PyAV build for Windows with two libraries left out: x264 and x265 (both GPL). Nothing
else is changed.

## The source

| What | Where | Commit |
| --- | --- | --- |
| PyAV v19.0.2 | https://github.com/PyAV-Org/PyAV | `a4ad0133b13eb84067dc6e8105eb1fc8f8b93c4f` |
| FFmpeg 9.0.2 and its libraries (pyav-ffmpeg 9.0.2-4) | https://github.com/PyAV-Org/pyav-ffmpeg | `6f3eed7b641b0095a965786c182de03f9aefcc59` |

pyav-ffmpeg's `scripts/pkg.py` names every library's source tarball by address and SHA-256 checksum, so the commit
above pins all of them.

The two changes Trace makes are the scripts in `tools/pyav-lgpl/`:

- `no_x264.py` turns `--enable-libx264` and `--enable-libx265` into `--disable-...` in pyav-ffmpeg's
  `scripts/build-ffmpeg.py` and drops the two packages from its build list.
- `use_tarball.py` points PyAV's `scripts/ffmpeg-latest.json` at the FFmpeg built that way.
- `check.py` proves the result has no x264 or x265 and that every FFmpeg library reports LGPL.

`tools/pyav-lgpl/RECIPE.md` explains every step, the pins and the licence of each library in the build.

## Rebuild it

The GitHub Action in `.github/workflows/pyav-lgpl.yml` builds it on GitHub's own Windows runners: fork this
repository, open Actions, pick **pyav-lgpl** and press **Run workflow**. About two hours later the run's artifact
`pyav-lgpl-v19.0.2` holds the wheel, the FFmpeg tarball and a `SOURCES.txt` with their SHA-256 checksums.

`SOURCES.txt` in this repository is the record of the run that made the wheel inside Trace 1.0.0 (the run itself was
in MatchdayLab's private repository, so its link will not open for you; the checksums are what matter):

- wheel `av-19.0.2-cp312-abi3-win_amd64.whl`: SHA-256 `8fe3584861f2d987d3a8b803ab2435dd5fedf59f89404d6d05cf1ae2e3f278bb`
- FFmpeg `ffmpeg-windows-x86_64.tar.gz`: SHA-256 `e3092ffc889f0ed9c39820fe54d3aeeac63285203dd9d141d8a2e68e7bbb9b1e`

A rebuild gives the same source and the same libraries; the files' checksums can differ, as builds are not
byte-for-byte reproducible.

## Changing FFmpeg inside Trace

The LGPL lets you replace these libraries with your own build. In an installed Trace they are separate DLL files in
`_internal\av.libs` in Trace's folder. Trace's licence agreement allows replacing them, and reverse engineering
Trace only as far as needed to debug that change.

## Contact

support@matchdaylab.com. We'll also send a copy of this source on request, for as long as we offer that version of
Trace.
