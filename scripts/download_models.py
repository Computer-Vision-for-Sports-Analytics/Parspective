"""Download the MediaPipe PoseLandmarker model files, pinned by version and SHA-256.

Model files are 5-30 MB, so they are not committed to git. Run this once after cloning:

    python scripts/download_models.py            # downloads the default "full" model
    python scripts/download_models.py --all      # lite, full and heavy

Files are saved to ``analysis/models/`` (git-ignored). The analysis core looks there by default.
The ``PARSPECTIVE_MODEL_DIR`` environment variable overrides that location.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = REPO_ROOT / "analysis" / "models"

_BASE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker"

# Versioned URLs ("/float16/1/") are used instead of "/latest/" so results are reproducible.
MODELS: dict[str, tuple[str, str]] = {
    "lite": (
        f"{_BASE}/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a",
    ),
    "full": (
        f"{_BASE}/pose_landmarker_full/float16/1/pose_landmarker_full.task",
        "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1",
    ),
    "heavy": (
        f"{_BASE}/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        "64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b",
    ),
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(variant: str, dest_dir: Path) -> Path:
    url, expected = MODELS[variant]
    dest = dest_dir / f"pose_landmarker_{variant}.task"
    if dest.exists() and sha256_of(dest) == expected:
        print(f"[ok] {dest} already present")
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    print(f"[..] downloading {variant} model from {url}")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 - fixed https URL above
    actual = sha256_of(tmp)
    if actual != expected:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"[!!] checksum mismatch for {variant}: expected {expected}, got {actual}")
    tmp.replace(dest)
    print(f"[ok] saved {dest}")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("variants", nargs="*", help=f"any of {list(MODELS)} (default: full)")
    parser.add_argument("--all", action="store_true", help="download every model variant")
    parser.add_argument(
        "--dir", type=Path, default=Path(os.environ.get("PARSPECTIVE_MODEL_DIR", DEFAULT_DIR))
    )
    args = parser.parse_args(argv)

    variants = list(MODELS) if args.all else (args.variants or ["full"])
    unknown = [v for v in variants if v not in MODELS]
    if unknown:
        parser.error(f"unknown model variant(s): {unknown}; choose from {list(MODELS)}")
    for variant in variants:
        download(variant, args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
