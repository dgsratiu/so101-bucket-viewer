# SO101 Claw Bucket Viewer

GitHub Pages viewer for an SO101 bucket attachment derived from the original
SO101 claw geometry.

## Model

The generated assembly STL is:

- `assets/so101-claw-bucket-attachment.stl`

The checked-in source claw STLs are copied from TheRobotStudio SO-ARM100:

- `assets/source-claw/Wrist_Roll_Follower_SO101.stl`
- `assets/source-claw/Moving_Jaw_SO101.stl`

The generator preserves the original wrist-roll follower mesh and moving-jaw
mesh as visible geometry, places the moving jaw in a gripper pose, then adds an
open bucket attached around the moving-jaw interface. The bucket is no longer a
standalone servo-yoke model.

Current generated assembly:

- Triangles: 24,028
- Bounding box: 78.0 x 191.8 x 105.4 mm
- Source claw STL bytes: 602,884 and 563,084 bytes
- Assembly STL bytes: 1,201,484 bytes

## Regenerate

```bash
python3 scripts/generate_viewer.py
```

The script rewrites the assembly STL and the embedded fallback STL inside
`index.html`. If the source claw STLs are missing, it looks for the canonical
SO-ARM100 checkout at `/tmp/SO-ARM100`.

## Validate

```bash
python3 scripts/generate_viewer.py
python3 -m py_compile scripts/generate_viewer.py
python3 - <<'PY'
from pathlib import Path
import re, struct

for path in [
    Path("assets/source-claw/Wrist_Roll_Follower_SO101.stl"),
    Path("assets/source-claw/Moving_Jaw_SO101.stl"),
    Path("assets/so101-claw-bucket-attachment.stl"),
]:
    data = path.read_bytes()
    assert not data.startswith(b"version https://git-lfs.github.com/spec/v1"), path
    assert len(data) > 100_000, path
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + count * 50, path

html = Path("index.html").read_text()
assert "assets/so101-claw-bucket-attachment.stl" in html
assert "FALLBACK_ASSEMBLY_STL_B64" in html
assert re.search(r"const ASSEMBLY_STL_URL\\s*=\\s*'assets/so101-claw-bucket-attachment\\.stl'", html)
print("validated claw-derived viewer assets")
PY
```
