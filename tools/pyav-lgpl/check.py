"""Prove the LGPL PyAV build has no x264 or x265 in it (tools/pyav-lgpl/README.md).

    python check.py files <archive.whl|archive.tar.gz> ...   no file named like x264 or x265 inside
    python check.py av --version 19.0.2                      the installed av: no x264 or x265 codec, FFmpeg's
                                                             own H.264 decoder works, h264_mf is there, LGPL only

Prints what it finds either way, so a failed run's log says why.
"""

import argparse
import base64
import sys
import tarfile
import zipfile
from fractions import Fraction
from pathlib import Path

GPL = ("x264", "x265")

# One 64 x 64 H.264 frame (made with x264, its options SEI removed): left half light grey, right half black.
H264_FRAME = "AAAAAWdCwAraEJoQAAADABAAAAMDIPEiagAAAAFozg/IAAAAAWWIhDomKAAIg0nJigACZbJ1111111111114"

problems = []


def problem(message: str) -> None:
    print(f"  PROBLEM: {message}")
    problems.append(message)


def check_files(paths: list[str]) -> None:
    for path in paths:
        if path.endswith(".whl"):
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
        else:
            with tarfile.open(path) as t:
                names = t.getnames()
        dlls = sorted(Path(n).name for n in names if n.lower().endswith(".dll"))
        print(f"{path}: {len(names)} files, {len(dlls)} DLLs")
        for dll in dlls:
            print(f"  {dll}")
        bad = [n for n in names if any(g in n.lower() for g in GPL)]
        if bad:
            problem(f"{path} holds x264 or x265 files: {bad}")
        if not any(Path(n).name.lower().startswith("avcodec") for n in names):
            problem(f"{path} has no avcodec: not an FFmpeg build")


def check_av(version: str | None) -> None:
    import av
    import av._core
    import av.codec

    print(f"av {av.__version__} from {av.__file__}")
    if version and av.__version__ != version:
        problem(f"av is {av.__version__}, expected {version}")
    print(f"library_versions: {av.library_versions}")

    codecs = av.codecs_available
    bad = sorted(c for c in codecs if any(g in c for g in GPL))
    if bad:
        problem(f"GPL codecs in av.codecs_available: {bad}")
    h264 = sorted(c for c in codecs if "264" in c or "hevc" in c or "265" in c)
    print(f"H.264 and HEVC codecs: {h264}")
    for name in ("h264", "hevc"):
        if av.codec.Codec(name, "r").name != name:
            problem(f"the {name} decoder is not FFmpeg's own")
    if "h264_mf" not in codecs:
        problem("h264_mf (Media Foundation) is not in av.codecs_available")
    for name in ("h264_nvenc", "h264_amf", "h264_qsv"):
        print(f"  {name}: {'yes' if name in codecs else 'no'}")

    for lib, meta in sorted(av._core.library_meta.items()):
        print(f"{lib} {meta['version']}: licence {meta['license']!r}")
        if not meta["license"].startswith("LGPL"):
            problem(f"{lib} licence is {meta['license']!r}, not LGPL")
    config = av._core.library_meta["libavcodec"]["configuration"]
    print(f"configuration: {config}")
    for flag in ("--enable-gpl", "--enable-nonfree", "--enable-libx264", "--enable-libx265"):
        if flag in config:
            problem(f"FFmpeg was configured with {flag}")

    libs = Path(av.__file__).parent.parent / "av.libs"
    dlls = sorted(p.name for p in libs.glob("*.dll")) if libs.is_dir() else []
    print(f"av.libs: {dlls}")
    bad = [d for d in dlls if any(g in d.lower() for g in GPL)]
    if bad:
        problem(f"GPL DLLs installed beside av: {bad}")

    ctx = av.CodecContext.create("h264", "r")
    data = base64.b64decode(H264_FRAME)
    frames = [f for p in ctx.parse(data) + ctx.parse(None) for f in ctx.decode(p)] + list(ctx.decode(None))
    if len(frames) != 1 or (frames[0].width, frames[0].height) != (64, 64):
        problem(f"H.264 decode gave {[(f.width, f.height) for f in frames]}, expected one 64 x 64 frame")
    else:
        y = frames[0].planes[0]
        row = bytes(y)[32 * y.line_size:32 * y.line_size + 64]
        print(f"H.264 decode: 64 x 64, luma left {row[8]}, right {row[56]}")
        if not row[8] > row[56] + 100:
            problem("the decoded H.264 frame is not light on the left and dark on the right")

    # Media Foundation may have no H.264 encoder on a Windows Server runner, so this one is reported, not required.
    try:
        enc = av.CodecContext.create("h264_mf", "w")
        enc.width, enc.height, enc.pix_fmt = 64, 64, "nv12"
        enc.time_base, enc.framerate = Fraction(1, 25), Fraction(25)
        frame = frames[0].reformat(format="nv12")
        frame.pts = 0
        packets = enc.encode(frame) + enc.encode(None)
        print(f"h264_mf encode on this runner: {sum(p.size for p in packets)} bytes")
    except Exception as e:
        print(f"h264_mf encode on this runner: not available ({e}); not required here")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    files = sub.add_parser("files")
    files.add_argument("archives", nargs="+")
    installed = sub.add_parser("av")
    installed.add_argument("--version")
    args = parser.parse_args()
    if args.mode == "files":
        check_files(args.archives)
    else:
        check_av(args.version)
    if problems:
        print(f"check: FAILED, {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        sys.exit(1)
    print("check: passed")


if __name__ == "__main__":
    main()
