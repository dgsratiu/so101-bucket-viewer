#!/usr/bin/env python3
"""Generate the SO101 bucket STL and GitHub Pages viewer.

The model is intentionally mesh-generated because the original repository only
contained an opaque embedded STL.  Dimensions are millimeters.
"""

from __future__ import annotations

import base64
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_PATH = ROOT / "assets" / "so101-bucket-servo-mount.stl"
INDEX_PATH = ROOT / "index.html"

TRIANGLES: list[tuple[tuple[float, float, float], ...]] = []


def add_tri(a, b, c):
    TRIANGLES.append((a, b, c))


def add_quad(a, b, c, d):
    add_tri(a, b, c)
    add_tri(a, c, d)


def add_box(name: str, center, size):
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


def add_tri_prism(points_xz, y0, y1):
    a, b, c = [(x, z) for x, z in points_xz]
    front = [(a[0], y0, a[1]), (b[0], y0, b[1]), (c[0], y0, c[1])]
    back = [(a[0], y1, a[1]), (b[0], y1, b[1]), (c[0], y1, c[1])]
    add_tri(front[0], front[1], front[2])
    add_tri(back[2], back[1], back[0])
    for i, j in ((0, 1), (1, 2), (2, 0)):
        add_quad(front[i], back[i], back[j], front[j])


def add_ring_y(center_x, center_y, center_z, outer_r, inner_r, depth, segments=64):
    """Annular cylinder with axis along Y."""
    y0, y1 = center_y - depth / 2, center_y + depth / 2
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        co0, so0 = math.cos(a0), math.sin(a0)
        co1, so1 = math.cos(a1), math.sin(a1)
        o0f = (center_x + outer_r * co0, y0, center_z + outer_r * so0)
        o1f = (center_x + outer_r * co1, y0, center_z + outer_r * so1)
        o0b = (center_x + outer_r * co0, y1, center_z + outer_r * so0)
        o1b = (center_x + outer_r * co1, y1, center_z + outer_r * so1)
        i0f = (center_x + inner_r * co0, y0, center_z + inner_r * so0)
        i1f = (center_x + inner_r * co1, y0, center_z + inner_r * so1)
        i0b = (center_x + inner_r * co0, y1, center_z + inner_r * so0)
        i1b = (center_x + inner_r * co1, y1, center_z + inner_r * so1)
        add_quad(o0f, o1f, o1b, o0b)
        add_quad(i1f, i0f, i0b, i1b)
        add_quad(o1f, o0f, i0f, i1f)
        add_quad(o0b, o1b, i1b, i0b)


def build_model():
    # Bucket: 80 mm wide, 77 mm deep, 40 mm tall, open at the top.
    add_box("floor", (0, 9.5, 2), (80, 77, 4))
    add_box("rear_wall", (0, -27, 20), (80, 4, 40))
    add_box("left_wall", (-38, 9.5, 20), (4, 77, 40))
    add_box("right_wall", (38, 9.5, 20), (4, 77, 40))
    add_box("front_lip", (0, 46, 10), (80, 4, 20))
    add_box("top_rear_flange", (0, -34, 38), (78, 10, 4))

    # Two SO101-style wrist/claw servo attachment stations.
    # Servo axes are along Y, so the horn rings face rearward and share
    # centered bolt/standoff geometry with the bucket bracket.
    station_xs = (-22, 22)
    horn_z = 28
    for sx in station_xs:
        add_box("servo_yoke_plate", (sx, -39, horn_z), (24, 8, 32))
        add_box("bucket_to_yoke_web", (sx, -33, horn_z), (18, 8, 20))
        add_box("upper_tab", (sx, -37, 45), (26, 16, 6))
        add_box("lower_tab", (sx, -37, 11), (26, 16, 6))

        # Horn clearance ring and central axle clearance.
        add_ring_y(sx, -45.5, horn_z, 10.5, 3.2, 5.0)

        # Four through-standoff tubes; their open centers are screw clearances.
        for dx, dz in ((-7.5, -7.5), (7.5, -7.5), (-7.5, 7.5), (7.5, 7.5)):
            add_ring_y(sx + dx, -39.0, horn_z + dz, 2.6, 1.35, 16.0, 32)

        # Diagonal gussets from the bucket back wall to the servo yoke.
        add_tri_prism([(sx - 12, 34), (sx - 12, 18), (sx - 3, 18)], -35.0, -27.0)
        add_tri_prism([(sx + 12, 34), (sx + 12, 18), (sx + 3, 18)], -35.0, -27.0)

    # A bridge locks both servo stations together and into the rear wall.
    add_box("servo_bridge", (0, -41, horn_z), (66, 6, 8))
    add_box("rear_spine", (0, -32, horn_z), (70, 6, 12))


def normal(a, b, c):
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    vx, vy, vz = (c[i] - a[i] for i in range(3))
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / mag, ny / mag, nz / mag


def write_binary_stl(path: Path):
    header = b"SO101 bucket with aligned servo horn mounts".ljust(80, b" ")
    with path.open("wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(TRIANGLES)))
        for tri in TRIANGLES:
            f.write(struct.pack("<fff", *normal(*tri)))
            for pt in tri:
                f.write(struct.pack("<fff", *pt))
            f.write(struct.pack("<H", 0))


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>SO101 Bucket 3D Viewer</title>
<style>
html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}#app{{position:fixed;inset:0;touch-action:none}}.hud{{position:fixed;left:12px;right:12px;top:max(10px,env(safe-area-inset-top));display:flex;gap:8px;align-items:center;justify-content:space-between;pointer-events:none}}.card{{pointer-events:auto;background:rgba(255,255,255,.86);color:#0f172a;border:1px solid rgba(15,23,42,.12);border-radius:14px;padding:10px 12px;backdrop-filter:blur(10px);box-shadow:0 8px 30px rgba(15,23,42,.18)}}.title{{font-weight:800;font-size:14px}}.sub{{font-size:11px;color:#475569;margin-top:2px}}.buttons{{display:flex;gap:8px}}button{{pointer-events:auto;border:0;border-radius:12px;padding:10px 12px;font-weight:800;color:#111827;background:#ffd43b;box-shadow:0 4px 18px rgba(0,0,0,.18)}}button.secondary{{background:#dbeafe}}.bottom{{position:fixed;left:12px;right:12px;bottom:max(12px,env(safe-area-inset-bottom));text-align:center;pointer-events:none}}.pill{{display:inline-block;background:rgba(255,255,255,.86);color:#334155;border:1px solid rgba(15,23,42,.12);border-radius:999px;padding:8px 12px;font-size:12px;backdrop-filter:blur(10px)}}#err{{display:none;position:fixed;inset:20px;color:white;background:#321;border:1px solid #f66;border-radius:16px;padding:16px;overflow:auto;z-index:5}}
</style>
</head><body>
<div id="app"></div>
<div class="hud"><div class="card"><div class="title">SO101 bucket</div><div class="sub">servo-yoke STL · 80×96×48 mm</div></div><div class="buttons"><button id="reset">Reset</button><button id="spin" class="secondary">Spin</button></div></div>
<div class="bottom"><span class="pill">Drag rotate · pinch zoom · two-finger pan</span></div><pre id="err"></pre>
<script type="importmap">{{"imports":{{"three":"https://unpkg.com/three@0.166.1/build/three.module.js","three/addons/":"https://unpkg.com/three@0.166.1/examples/jsm/"}}}}</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ STLLoader }} from 'three/addons/loaders/STLLoader.js';
const STL_B64 = '{stl_b64}';
const err=document.getElementById('err');function fail(e){{err.style.display='block';err.textContent=(e&&e.stack)?e.stack:String(e);console.error(e)}}
try{{
const app=document.getElementById('app'), scene=new THREE.Scene(); scene.background=new THREE.Color(0xf8fafc);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.1,2000);
const renderer=new THREE.WebGLRenderer({{antialias:true,powerPreference:'high-performance'}}); renderer.setPixelRatio(Math.min(devicePixelRatio||1,2)); renderer.setSize(innerWidth,innerHeight); renderer.outputColorSpace=THREE.SRGBColorSpace; app.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x9ab0c6,2.5)); const key=new THREE.DirectionalLight(0xffffff,2.7); key.position.set(80,-100,140); scene.add(key); const fill=new THREE.DirectionalLight(0xffffff,1.4); fill.position.set(-90,80,90); scene.add(fill);
function b64buf(b64){{const bin=atob(b64), bytes=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i); return bytes.buffer}}
const geometry=new STLLoader().parse(b64buf(STL_B64)); geometry.computeVertexNormals(); geometry.center(); geometry.computeBoundingSphere();
const bucketMat=new THREE.MeshStandardMaterial({{color:0xffd21f,roughness:.38,metalness:.02,side:THREE.DoubleSide}});
const mesh=new THREE.Mesh(geometry,bucketMat); scene.add(mesh);
const edges=new THREE.EdgesGeometry(geometry,24); const lines=new THREE.LineSegments(edges,new THREE.LineBasicMaterial({{color:0x111827}})); scene.add(lines);

const servoGroup=new THREE.Group();
const servoMat=new THREE.MeshStandardMaterial({{color:0x64748b,roughness:.5,metalness:.05}});
const hornMat=new THREE.MeshStandardMaterial({{color:0x2563eb,roughness:.32,metalness:.1}});
for (const x of [-22,22]) {{
  const body=new THREE.Mesh(new THREE.BoxGeometry(20,28,34), servoMat);
  body.position.set(x,-59,28); servoGroup.add(body);
  const horn=new THREE.Mesh(new THREE.CylinderGeometry(10.5,10.5,4,48,1,false), hornMat);
  horn.rotation.x=Math.PI/2; horn.position.set(x,-45.5,28); servoGroup.add(horn);
  const axle=new THREE.Mesh(new THREE.CylinderGeometry(3.1,3.1,6,32), new THREE.MeshStandardMaterial({{color:0x0f172a}}));
  axle.rotation.x=Math.PI/2; axle.position.set(x,-45.6,28); servoGroup.add(axle);
}}
servoGroup.position.copy(mesh.position); scene.add(servoGroup);

const r=geometry.boundingSphere.radius||75; const grid=new THREE.GridHelper(Math.max(190,r*4),19,0x94a3b8,0xdbe3ec); grid.rotation.x=Math.PI/2; grid.position.z=-.5; scene.add(grid); scene.add(new THREE.AxesHelper(45));
function frameModel(){{camera.position.set(r*2.1,-r*2.7,r*1.65);controls.target.set(0,0,0);controls.update()}}
const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.dampingFactor=.08; controls.screenSpacePanning=true; controls.minDistance=r*.8; controls.maxDistance=r*8; frameModel();
let spinning=false; document.getElementById('reset').onclick=frameModel; document.getElementById('spin').onclick=()=>{{spinning=!spinning;document.getElementById('spin').textContent=spinning?'Stop':'Spin'}};
addEventListener('resize',()=>{{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)}});
(function anim(){{requestAnimationFrame(anim); if(spinning){{mesh.rotation.z+=.008;lines.rotation.z=mesh.rotation.z;servoGroup.rotation.z=mesh.rotation.z}} controls.update(); renderer.render(scene,camera)}})();
}}catch(e){{fail(e)}}
</script></body></html>
"""


def main():
    TRIANGLES.clear()
    build_model()
    ASSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_binary_stl(ASSET_PATH)
    stl_b64 = base64.b64encode(ASSET_PATH.read_bytes()).decode("ascii")
    INDEX_PATH.write_text(HTML_TEMPLATE.format(stl_b64=stl_b64), encoding="utf-8")
    print(f"wrote {ASSET_PATH.relative_to(ROOT)} ({ASSET_PATH.stat().st_size} bytes)")
    print(f"wrote {INDEX_PATH.relative_to(ROOT)}")
    print(f"triangles {len(TRIANGLES)}")


if __name__ == "__main__":
    main()
