"""Build every diagram: write docs/diagrams/NN_name.drawio, then export a 2x PNG.

    python3 docs/diagrams/build.py [01 02 ...]

Sources are docs/diagrams/src/dNN_*.py; each defines build(page_path). Rendering uses
the draw.io desktop CLI. Stdlib only, plus the gcp-architecture-diagram skill's builder.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "gcp-architecture-diagram" / "scripts"))
CLI = shutil.which("drawio") or "/Applications/draw.io.app/Contents/MacOS/draw.io"


def main(only: list[str]) -> None:
    for src in sorted((HERE / "src").glob("d[0-9][0-9]_*.py")):
        number = src.stem[1:3]
        if only and number not in only:
            continue
        spec = importlib.util.spec_from_file_location(src.stem, src)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = HERE / f"{src.stem[1:]}.drawio"
        module.build(target)
        png = target.with_suffix(".png")
        subprocess.run(
            [
                CLI,
                "--export",
                "--format",
                "png",
                "--scale",
                "2",
                "--border",
                "0",
                "--output",
                str(png),
                str(target),
            ],
            check=True,
            capture_output=True,
        )
        print(f"{target.name} -> {png.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
