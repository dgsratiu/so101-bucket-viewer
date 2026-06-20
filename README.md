# SO101 Claw Bucket Viewer

GitHub Pages viewer for an SO101 bucket attachment derived from the original
SO101 claw geometry.

## Model

The viewer loads the checked-in source claw STLs directly:

- `assets/source-claw/Wrist_Roll_Follower_SO101.stl`
- `assets/source-claw/Moving_Jaw_SO101.stl`

The page preserves the original wrist-roll follower mesh and moving-jaw mesh as
visible geometry, places the moving jaw in a gripper pose, then adds an open
bucket around the moving-jaw interface.

The viewer also includes an **Action traces** toggle. When enabled, it shows an
animated four-step push sequence with a visible status panel: approach, ground
contact, push forward, and reset/recover. The translucent claw/bucket ghost pose
continues stepping through the sequence even when Spin is off, and disabling the
toggle hides and pauses both the traces and status panel.

The generated assembly STL is retained for compatibility:

- `assets/so101-claw-bucket-attachment.stl`

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
python3 -m py_compile scripts/generate_viewer.py
node --check assets/scripts/viewer.js
python3 - <<'PY'
from pathlib import Path
import re, struct

for path in [
    Path("assets/source-claw/Wrist_Roll_Follower_SO101.stl"),
    Path("assets/source-claw/Moving_Jaw_SO101.stl"),
]:
    data = path.read_bytes()
    assert not data.startswith(b"version https://git-lfs.github.com/spec/v1"), path
    assert len(data) > 100_000, path
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + count * 50, path

html = Path("index.html").read_text()
viewer = Path("assets/scripts/viewer.js").read_text()
assert 'id="traces"' in html
assert 'id="action-status"' in html
assert 'id="action-message"' in html
assert "Action traces" in html
assert "action-traces" in viewer
assert "ACTION_STEPS" in viewer
assert "Ground contact" in viewer
assert "Push forward" in viewer
assert "ground-contact-push-direction" in viewer
assert "push-direction-arrow" in viewer
assert re.search(r"source-claw/.+SO101\\.stl", viewer)
print("validated action trace viewer markers")
PY
```
