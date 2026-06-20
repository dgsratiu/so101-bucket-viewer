#!/usr/bin/env python3
"""Generate a claw-derived SO101 bucket attachment viewer.

The assembly keeps the original SO101 wrist-roll follower and moving jaw STL
triangles visible, then adds a bucket attached around the moving-jaw interface.
Dimensions are millimeters.
"""

from __future__ import annotations

import base64
import math
import shutil
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE_ASSETS = ASSETS / "source-claw"
ASSEMBLY_PATH = ASSETS / "so101-claw-bucket-attachment.stl"
INDEX_PATH = ROOT / "index.html"

WRIST_SOURCE = SOURCE_ASSETS / "Wrist_Roll_Follower_SO101.stl"
JAW_SOURCE = SOURCE_ASSETS / "Moving_Jaw_SO101.stl"

CANONICAL_CANDIDATES = [
    Path("/tmp/SO-ARM100"),
]

Triangle = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
TRIANGLES: list[Triangle] = []


def reject_lfs_pointer(path: Path) -> None:
    head = path.read_bytes()[:160]
    if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError(f"{path} is a Git LFS pointer, not CAD bytes")


def seed_source_assets() -> None:
    SOURCE_ASSETS.mkdir(parents=True, exist_ok=True)
    if WRIST_SOURCE.exists() and JAW_SOURCE.exists():
        reject_lfs_pointer(WRIST_SOURCE)
        reject_lfs_pointer(JAW_SOURCE)
        return

    for root in CANONICAL_CANDIDATES:
        wrist = root / "STL" / "SO101" / "Individual" / "Wrist_Roll_Follower_SO101.stl"
        jaw = root / "STL" / "SO101" / "Individual" / "Moving_Jaw_SO101.stl"
        if wrist.exists() and jaw.exists():
            reject_lfs_pointer(wrist)
            reject_lfs_pointer(jaw)
            shutil.copyfile(wrist, WRIST_SOURCE)
            shutil.copyfile(jaw, JAW_SOURCE)
            return

    raise FileNotFoundError(
        "Missing SO101 claw source STLs. Clone https://github.com/TheRobotStudio/SO-ARM100 "
        "to /tmp/SO-ARM100 or place the two source STLs under assets/source-claw/."
    )


def read_binary_stl(path: Path) -> list[Triangle]:
    reject_lfs_pointer(path)
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if expected != len(data):
        raise ValueError(f"{path} is not a binary STL with matching triangle count")
    tris: list[Triangle] = []
    offset = 84
    for _ in range(count):
        pts = []
        for j in range(3):
            pts.append(struct.unpack_from("<fff", data, offset + 12 + j * 12))
        tris.append((pts[0], pts[1], pts[2]))
        offset += 50
    return tris


def transform_triangles(triangles: list[Triangle], translate=(0.0, 0.0, 0.0)) -> list[Triangle]:
    tx, ty, tz = translate
    return [
        tuple((x + tx, y + ty, z + tz) for x, y, z in tri)  # type: ignore[misc]
        for tri in triangles
    ]


def add_tri(a, b, c) -> None:
    TRIANGLES.append((a, b, c))


def add_quad(a, b, c, d) -> None:
    add_tri(a, b, c)
    add_tri(a, c, d)


def add_box(center, size) -> None:
    cx, cy, cz = center
    sx, sy, sz = (v / 2 for v in size)
    x0, x1 = cx - sx, cx + sx
    y0, y1 = cy - sy, cy + sy
    z0, z1 = cz - sz, cz + sz
    p = {
        "000": (x0, y0, z0),
        "100": (x1, y0, z0),
        "110": (x1, y1, z0),
        "010": (x0, y1, z0),
        "001": (x0, y0, z1),
        "101": (x1, y0, z1),
        "111": (x1, y1, z1),
        "011": (x0, y1, z1),
    }
    add_quad(p["000"], p["010"], p["110"], p["100"])
    add_quad(p["001"], p["101"], p["111"], p["011"])
    add_quad(p["000"], p["100"], p["101"], p["001"])
    add_quad(p["010"], p["011"], p["111"], p["110"])
    add_quad(p["000"], p["001"], p["011"], p["010"])
    add_quad(p["100"], p["110"], p["111"], p["101"])


def add_tri_prism(points_yz, x0, x1) -> None:
    a, b, c = [(y, z) for y, z in points_yz]
    left = [(x0, a[0], a[1]), (x0, b[0], b[1]), (x0, c[0], c[1])]
    right = [(x1, a[0], a[1]), (x1, b[0], b[1]), (x1, c[0], c[1])]
    add_tri(left[0], left[1], left[2])
    add_tri(right[2], right[1], right[0])
    for i, j in ((0, 1), (1, 2), (2, 0)):
        add_quad(left[i], right[i], right[j], left[j])


def add_ring_z(center_x, center_y, center_z, outer_r, inner_r, height, segments=48) -> None:
    z0, z1 = center_z - height / 2, center_z + height / 2
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        co0, so0 = math.cos(a0), math.sin(a0)
        co1, so1 = math.cos(a1), math.sin(a1)
        o0b = (center_x + outer_r * co0, center_y + outer_r * so0, z0)
        o1b = (center_x + outer_r * co1, center_y + outer_r * so1, z0)
        o0t = (center_x + outer_r * co0, center_y + outer_r * so0, z1)
        o1t = (center_x + outer_r * co1, center_y + outer_r * so1, z1)
        i0b = (center_x + inner_r * co0, center_y + inner_r * so0, z0)
        i1b = (center_x + inner_r * co1, center_y + inner_r * so1, z0)
        i0t = (center_x + inner_r * co0, center_y + inner_r * so0, z1)
        i1t = (center_x + inner_r * co1, center_y + inner_r * so1, z1)
        add_quad(o0b, o1b, o1t, o0t)
        add_quad(i1b, i0b, i0t, i1t)
        add_quad(o1b, o0b, i0b, i1b)
        add_quad(o0t, o1t, i1t, i0t)


def build_bucket_attachment() -> None:
    jaw_z = 52.0
    bucket_y = -128.0
    bucket_z = jaw_z - 5.0

    add_box((0, bucket_y, bucket_z - 20), (74, 68, 4))
    add_box((-37, bucket_y, bucket_z), (4, 68, 44))
    add_box((37, bucket_y, bucket_z), (4, 68, 44))
    add_box((0, bucket_y - 34, bucket_z), (74, 4, 44))
    add_box((0, bucket_y + 34, bucket_z - 10), (74, 4, 24))

    add_box((0, -55, jaw_z), (34, 34, 9))
    add_box((-15.5, -55, jaw_z), (5, 42, 24))
    add_box((15.5, -55, jaw_z), (5, 42, 24))
    add_box((0, -36, jaw_z + 12), (34, 5, 20))
    add_box((0, -84, jaw_z - 6), (32, 54, 10))
    add_tri_prism([(-98, jaw_z + 12), (-65, jaw_z + 12), (-65, jaw_z - 14)], -32, -18)
    add_tri_prism([(-98, jaw_z + 12), (-65, jaw_z + 12), (-65, jaw_z - 14)], 18, 32)

    for x in (-9.5, 9.5):
        add_ring_z(x, -55, jaw_z + 13, 3.7, 1.75, 6.0, 36)


def normal(a, b, c):
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    vx, vy, vz = (c[i] - a[i] for i in range(3))
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / mag, ny / mag, nz / mag


def write_binary_stl(path: Path) -> None:
    header = b"SO101 claw-derived bucket attachment; original claw STL triangles included".ljust(80, b" ")
    with path.open("wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(TRIANGLES)))
        for tri in TRIANGLES:
            f.write(struct.pack("<fff", *normal(*tri)))
            for pt in tri:
                f.write(struct.pack("<fff", *pt))
            f.write(struct.pack("<H", 0))


def bounds(triangles: list[Triangle]) -> tuple[list[float], list[float]]:
    mn = [float("inf"), float("inf"), float("inf")]
    mx = [float("-inf"), float("-inf"), float("-inf")]
    for tri in triangles:
        for point in tri:
            for i in range(3):
                mn[i] = min(mn[i], point[i])
                mx[i] = max(mx[i], point[i])
    return mn, mx


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>SO101 Claw Bucket Viewer</title>
<style>
html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#f7f7f4;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}#app{{position:fixed;inset:0;touch-action:none}}.hud{{position:fixed;left:12px;right:12px;top:max(10px,env(safe-area-inset-top));display:flex;gap:8px;align-items:flex-start;justify-content:space-between;pointer-events:none}}.card{{pointer-events:auto;background:rgba(255,255,255,.88);color:#111827;border:1px solid rgba(17,24,39,.13);border-radius:8px;padding:10px 12px;backdrop-filter:blur(10px);box-shadow:0 8px 28px rgba(17,24,39,.14);max-width:min(470px,calc(100vw - 132px))}}.title{{font-weight:800;font-size:14px}}.sub{{font-size:11px;color:#4b5563;margin-top:2px;line-height:1.35}}.buttons{{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}}button{{pointer-events:auto;border:1px solid rgba(17,24,39,.16);border-radius:8px;padding:9px 11px;font-weight:800;color:#111827;background:#facc15;box-shadow:0 4px 16px rgba(0,0,0,.14)}}button.secondary{{background:#bfdbfe}}.bottom{{position:fixed;left:12px;right:12px;bottom:max(12px,env(safe-area-inset-bottom));text-align:center;pointer-events:none}}.pill{{display:inline-block;background:rgba(255,255,255,.88);color:#374151;border:1px solid rgba(17,24,39,.13);border-radius:999px;padding:8px 12px;font-size:12px;backdrop-filter:blur(10px)}}#err{{display:none;position:fixed;inset:20px;color:white;background:#321;border:1px solid #f66;border-radius:8px;padding:16px;overflow:auto;z-index:5}}
</style>
</head><body>
<div id="app"></div>
<div class="hud"><div class="card"><div class="title">SO101 claw bucket</div><div class="sub">Claw-derived assembly STL: wrist-roll follower + moving jaw + jaw-mounted bucket attachment</div></div><div class="buttons"><button id="reset">Reset</button><button id="spin" class="secondary">Spin</button></div></div>
<div class="bottom"><span class="pill">Drag rotate · pinch zoom · two-finger pan</span></div><pre id="err"></pre>
<script type="importmap">{{"imports":{{"three":"https://unpkg.com/three@0.166.1/build/three.module.js","three/addons/":"https://unpkg.com/three@0.166.1/examples/jsm/"}}}}</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ STLLoader }} from 'three/addons/loaders/STLLoader.js';
const ASSEMBLY_STL_URL = 'assets/so101-claw-bucket-attachment.stl';
const FALLBACK_ASSEMBLY_STL_B64 = '{stl_b64}';
const err=document.getElementById('err');function fail(e){{err.style.display='block';err.textContent=(e&&e.stack)?e.stack:String(e);console.error(e)}}
function b64buf(b64){{const bin=atob(b64), bytes=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i); return bytes.buffer}}
async function loadAssembly(loader){{try{{const res=await fetch(ASSEMBLY_STL_URL); if(!res.ok) throw new Error(`${{ASSEMBLY_STL_URL}} returned ${{res.status}}`); return loader.parse(await res.arrayBuffer())}}catch(e){{console.warn('Using embedded fallback STL', e); return loader.parse(b64buf(FALLBACK_ASSEMBLY_STL_B64))}}}}
try{{
const app=document.getElementById('app'), scene=new THREE.Scene(); scene.background=new THREE.Color(0xf7f7f4);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.1,2500);
const renderer=new THREE.WebGLRenderer({{antialias:true,powerPreference:'high-performance'}}); renderer.setPixelRatio(Math.min(devicePixelRatio||1,2)); renderer.setSize(innerWidth,innerHeight); renderer.outputColorSpace=THREE.SRGBColorSpace; app.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0xaeb7c2,2.4)); const key=new THREE.DirectionalLight(0xffffff,2.8); key.position.set(100,-130,170); scene.add(key); const fill=new THREE.DirectionalLight(0xffffff,1.2); fill.position.set(-120,90,110); scene.add(fill);
const loader=new STLLoader();
const geometry=await loadAssembly(loader); geometry.computeVertexNormals(); geometry.center(); geometry.computeBoundingSphere();
const material=new THREE.MeshStandardMaterial({{color:0xeab308,roughness:.42,metalness:.03,side:THREE.DoubleSide}});
const mesh=new THREE.Mesh(geometry,material); scene.add(mesh);
const edges=new THREE.EdgesGeometry(geometry,25); const lines=new THREE.LineSegments(edges,new THREE.LineBasicMaterial({{color:0x1f2937,transparent:true,opacity:.55}})); scene.add(lines);
const r=geometry.boundingSphere.radius||110; const grid=new THREE.GridHelper(Math.max(260,r*3.2),20,0x9ca3af,0xd6d3d1); grid.rotation.x=Math.PI/2; grid.position.z=-r*.42; scene.add(grid); scene.add(new THREE.AxesHelper(55));
const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.dampingFactor=.08; controls.screenSpacePanning=true; controls.minDistance=r*.75; controls.maxDistance=r*7;
function frameModel(){{camera.position.set(r*1.6,-r*2.55,r*1.3);controls.target.set(0,0,0);controls.update()}} frameModel();
let spinning=false; document.getElementById('reset').onclick=frameModel; document.getElementById('spin').onclick=()=>{{spinning=!spinning;document.getElementById('spin').textContent=spinning?'Stop':'Spin'}};
addEventListener('resize',()=>{{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)}});
(function anim(){{requestAnimationFrame(anim); if(spinning){{mesh.rotation.z+=.007;lines.rotation.z=mesh.rotation.z}} controls.update(); renderer.render(scene,camera)}})();
}}catch(e){{fail(e)}}
</script></body></html>
"""


def main() -> None:
    TRIANGLES.clear()
    seed_source_assets()
    wrist = read_binary_stl(WRIST_SOURCE)
    jaw = transform_triangles(read_binary_stl(JAW_SOURCE), translate=(0, 0, 52))
    TRIANGLES.extend(wrist)
    TRIANGLES.extend(jaw)
    build_bucket_attachment()

    ASSETS.mkdir(parents=True, exist_ok=True)
    write_binary_stl(ASSEMBLY_PATH)
    reject_lfs_pointer(ASSEMBLY_PATH)
    stl_b64 = base64.b64encode(ASSEMBLY_PATH.read_bytes()).decode("ascii")
    INDEX_PATH.write_text(HTML_TEMPLATE.format(stl_b64=stl_b64), encoding="utf-8")

    mn, mx = bounds(TRIANGLES)
    size = [mx[i] - mn[i] for i in range(3)]
    print(f"wrote {ASSEMBLY_PATH.relative_to(ROOT)} ({ASSEMBLY_PATH.stat().st_size} bytes)")
    print(f"wrote {WRIST_SOURCE.relative_to(ROOT)} ({WRIST_SOURCE.stat().st_size} bytes)")
    print(f"wrote {JAW_SOURCE.relative_to(ROOT)} ({JAW_SOURCE.stat().st_size} bytes)")
    print(f"wrote {INDEX_PATH.relative_to(ROOT)}")
    print(f"triangles {len(TRIANGLES)}")
    print("bbox min", [round(v, 3) for v in mn])
    print("bbox max", [round(v, 3) for v in mx])
    print("bbox size", [round(v, 3) for v in size])


if __name__ == "__main__":
    main()
