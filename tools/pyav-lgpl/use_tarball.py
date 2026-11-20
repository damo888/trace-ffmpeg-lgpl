"""Point PyAV's build at our FFmpeg tarball instead of upstream's (tools/pyav-lgpl/README.md).

Rewrites scripts/ffmpeg-latest.json in a checkout of PyAV-Org/PyAV so scripts/fetch-vendor.py copies our tarball
(a file:// URL) rather than downloading pyav-ffmpeg's release. Fails loudly unless the json names exactly the
pyav-ffmpeg release we expect PyAV to pin (--pyav-names, default --tag), so PyAV and its FFmpeg never drift apart
unnoticed. For PyAV v19.0.2 that is 9.0.2-1 while we build 9.0.2-4 (same FFmpeg 9.0.2; README.md says why).

    python tools/pyav-lgpl/use_tarball.py <PyAV checkout> <ffmpeg-windows-x86_64.tar.gz> --tag <tag built from>
        [--pyav-names <tag PyAV's json names>]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

UPSTREAM = "https://github.com/PyAV-Org/pyav-ffmpeg/releases/download/{tag}/ffmpeg-{{platform}}.tar.gz"
NAME = "ffmpeg-windows-x86_64.tar.gz"


def fail(message: str) -> None:
    print(f"use_tarball: FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pyav")
    parser.add_argument("tarball")
    parser.add_argument("--tag", required=True, help="the pyav-ffmpeg tag the tarball was built from")
    parser.add_argument("--pyav-names", help="the pyav-ffmpeg tag PyAV's json names, if not --tag")
    args = parser.parse_args()

    root = Path(args.pyav)
    config = root / "scripts" / "ffmpeg-latest.json"
    fetch = root / "scripts" / "fetch-vendor.py"
    tarball = Path(args.tarball).resolve()
    for path in (config, fetch, tarball):
        if not path.is_file():
            fail(f"{path} is not there")
    if tarball.name != NAME:
        fail(f"the tarball must be called {NAME} (fetch-vendor.py fills in the platform), not {tarball.name}")
    if '"{platform}"' not in fetch.read_text(encoding="utf-8"):
        fail(f"{fetch} no longer fills in {{platform}}: read it and change this script to match")
    # fetch-vendor.py skips the download if a file of that name is already in its cache folder.
    if (root / "tarballs").exists():
        fail(f"{root / 'tarballs'} exists: a cached tarball there would be used instead of ours")

    before = config.read_text(encoding="utf-8")
    data = json.loads(before)
    named = args.pyav_names or args.tag
    expected = UPSTREAM.format(tag=named)
    if data != {"url": expected}:
        fail(f"{config} should be exactly {{\"url\": \"{expected}\"}}, found {data}.\n"
             "PyAV pins a different FFmpeg build: set PYAV_PINS_FFMPEG_TAG (and PYAV_FFMPEG_TAG and its SHA) "
             "in the workflow to match.")
    if named != args.tag:
        print(f"use_tarball: PyAV names pyav-ffmpeg {named}; our tarball is built from pyav-ffmpeg {args.tag} "
              "instead (same FFmpeg 9.0.2), as the workflow's PYAV_PINS_FFMPEG_TAG expects")

    url = tarball.parent.as_uri() + "/ffmpeg-{platform}.tar.gz"
    config.write_text(json.dumps({"url": url}, indent=4) + "\n", encoding="utf-8")
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    print(f"use_tarball: {config}\n  was: {expected}\n  now: {url}\n  tarball sha256: {digest}")


if __name__ == "__main__":
    main()
