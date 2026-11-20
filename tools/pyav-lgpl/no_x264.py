"""Leave x264 and x265 (both GPL) out of PyAV's FFmpeg build (tools/pyav-lgpl/README.md).

Edits scripts/build-ffmpeg.py in a checkout of PyAV-Org/pyav-ffmpeg so FFmpeg is configured without the two
libraries and they are not built. Fails loudly if the lines it expects are not there exactly once, so a new
pyav-ffmpeg release that moves them is caught here rather than shipping x264 by accident.

    python tools/pyav-lgpl/no_x264.py <pyav-ffmpeg checkout>
"""

import difflib
import sys
from pathlib import Path

MARK = "# Trace (tools/pyav-lgpl): x264 and x265 are GPL, so they are left out"

EDITS = [
    (
        "    # x264 is skipped on 32-bit ARM (armv7)\n"
        "    ffmpeg_package.build_arguments.append(\"--enable-libx265\")\n"
        "    if not is_arm32:\n"
        "        ffmpeg_package.build_arguments.append(\"--enable-libx264\")\n",
        f"    {MARK}\n"
        "    ffmpeg_package.build_arguments.extend([\"--disable-libx264\", \"--disable-libx265\"])\n",
    ),
    (
        "    if is_arm32:\n"
        "        # x264 is not built on 32-bit ARM (armv7)\n"
        "        packages += [p for p in codec_group if p.name != \"x264\"]\n"
        "    else:\n"
        "        packages += codec_group\n",
        f"    {MARK}\n"
        "    packages += [p for p in codec_group if p.name not in {\"x264\", \"x265\"}]\n",
    ),
]


def fail(message: str) -> None:
    print(f"no_x264: FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: no_x264.py <pyav-ffmpeg checkout>")
    root = Path(sys.argv[1])
    script = root / "scripts" / "build-ffmpeg.py"
    pkg = root / "scripts" / "pkg.py"
    for path in (script, pkg):
        if not path.is_file():
            fail(f"{path} is not there")

    raw = script.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    before = raw.replace("\r\n", "\n")
    if MARK in before:
        fail(f"{script} is already edited")

    after = before
    for old, new in EDITS:
        count = after.count(old)
        if count != 1:
            fail(f"expected these lines once in {script}, found them {count} times:\n{old}")
        after = after.replace(old, new)

    # Nothing else may still turn them on, and the filter above must name packages that exist.
    for needle in ("--enable-libx264", "--enable-libx265"):
        if needle in after:
            fail(f"{needle} is still in {script}")
    pkg_text = pkg.read_text(encoding="utf-8")
    for name in ("x264", "x265"):
        if f'name="{name}"' not in pkg_text:
            fail(f'{pkg} has no package named "{name}": the filter would do nothing, check the codec list')
    compile(after, str(script), "exec")

    script.write_bytes((after.replace("\n", "\r\n") if crlf else after).encode("utf-8"))
    sys.stdout.writelines(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        "a/scripts/build-ffmpeg.py", "b/scripts/build-ffmpeg.py"))
    print("no_x264: done, x264 and x265 left out")


if __name__ == "__main__":
    main()
