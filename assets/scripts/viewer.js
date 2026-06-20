import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

const SOURCE_STLS = {
  wrist: 'assets/source-claw/Wrist_Roll_Follower_SO101.stl',
  jaw: 'assets/source-claw/Moving_Jaw_SO101.stl',
};

const err = document.getElementById('err');

function fail(error) {
  err.style.display = 'block';
  err.textContent = error && error.stack ? error.stack : String(error);
  console.error(error);
}

function box(center, size, material) {
  const geometry = new THREE.BoxGeometry(size.x, size.y, size.z);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(center);
  return mesh;
}

function makeBucketGroup(material) {
  const group = new THREE.Group();
  const jawZ = 52;
  const bucketY = -128;
  const bucketZ = jawZ - 5;

  group.add(box(new THREE.Vector3(0, bucketY, bucketZ - 20), new THREE.Vector3(74, 68, 4), material));
  group.add(box(new THREE.Vector3(-37, bucketY, bucketZ), new THREE.Vector3(4, 68, 44), material));
  group.add(box(new THREE.Vector3(37, bucketY, bucketZ), new THREE.Vector3(4, 68, 44), material));
  group.add(box(new THREE.Vector3(0, bucketY - 34, bucketZ), new THREE.Vector3(74, 4, 44), material));
  group.add(box(new THREE.Vector3(0, bucketY + 34, bucketZ - 10), new THREE.Vector3(74, 4, 24), material));

  group.add(box(new THREE.Vector3(0, -55, jawZ), new THREE.Vector3(34, 34, 9), material));
  group.add(box(new THREE.Vector3(-15.5, -55, jawZ), new THREE.Vector3(5, 42, 24), material));
  group.add(box(new THREE.Vector3(15.5, -55, jawZ), new THREE.Vector3(5, 42, 24), material));
  group.add(box(new THREE.Vector3(0, -36, jawZ + 12), new THREE.Vector3(34, 5, 20), material));
  group.add(box(new THREE.Vector3(0, -84, jawZ - 6), new THREE.Vector3(32, 54, 10), material));

  for (const x of [-9.5, 9.5]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.72, 0.9, 10, 32), material);
    ring.position.set(x, -55, jawZ + 13);
    ring.rotation.x = Math.PI / 2;
    group.add(ring);
  }

  return group;
}

function cloneWithMaterial(object, material) {
  const clone = object.clone(true);
  clone.traverse((child) => {
    if (child.isMesh) {
      child.material = material;
      child.renderOrder = -1;
    }
  });
  return clone;
}

function makeGhostAssembly(jawMesh, bucketGroup, material) {
  const ghost = new THREE.Group();
  const jaw = cloneWithMaterial(jawMesh, material);
  const bucket = cloneWithMaterial(bucketGroup, material);
  ghost.add(jaw, bucket);
  return ghost;
}

function makeCurve(points, color, opacity, dashed = false) {
  const curve = new THREE.CatmullRomCurve3(points);
  const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(80));
  const material = dashed
    ? new THREE.LineDashedMaterial({ color, transparent: true, opacity, dashSize: 10, gapSize: 6 })
    : new THREE.LineBasicMaterial({ color, transparent: true, opacity });
  const line = new THREE.Line(geometry, material);
  if (dashed) line.computeLineDistances();
  return line;
}

function makeActionTraces(jawMesh, bucketGroup) {
  const traces = new THREE.Group();
  traces.name = 'action-traces';

  const ghostMaterial = new THREE.MeshStandardMaterial({
    color: 0x22c55e,
    transparent: true,
    opacity: 0.18,
    roughness: 0.55,
    metalness: 0.02,
    depthWrite: false,
    side: THREE.DoubleSide,
  });

  const ghostPoses = [
    { y: 48, z: 18, rot: -0.14, scale: 0.985 },
    { y: 24, z: 9, rot: -0.07, scale: 0.995 },
    { y: -28, z: -6, rot: 0.09, scale: 1.01 },
  ];

  for (const pose of ghostPoses) {
    const ghost = makeGhostAssembly(jawMesh, bucketGroup, ghostMaterial);
    ghost.position.set(0, pose.y, pose.z);
    ghost.rotation.x = pose.rot;
    ghost.scale.setScalar(pose.scale);
    traces.add(ghost);
  }

  traces.add(makeCurve([
    new THREE.Vector3(0, -76, 92),
    new THREE.Vector3(0, -104, 78),
    new THREE.Vector3(0, -135, 60),
    new THREE.Vector3(0, -166, 48),
  ], 0x16a34a, 0.86));

  const contactPath = makeCurve([
    new THREE.Vector3(-45, -84, -8),
    new THREE.Vector3(-28, -112, -8),
    new THREE.Vector3(-8, -141, -8),
    new THREE.Vector3(20, -174, -8),
  ], 0xef4444, 0.8, true);
  contactPath.name = 'ground-contact-push-direction';
  traces.add(contactPath);

  const arrow = new THREE.ArrowHelper(
    new THREE.Vector3(0.55, -0.83, 0).normalize(),
    new THREE.Vector3(20, -174, -8),
    42,
    0xef4444,
    12,
    7,
  );
  arrow.name = 'push-direction-arrow';
  traces.add(arrow);

  for (const point of [
    new THREE.Vector3(-45, -84, -8),
    new THREE.Vector3(-8, -141, -8),
    new THREE.Vector3(20, -174, -8),
  ]) {
    const mark = new THREE.Mesh(
      new THREE.RingGeometry(5, 8, 32),
      new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.62, side: THREE.DoubleSide }),
    );
    mark.position.copy(point);
    traces.add(mark);
  }

  return traces;
}

async function loadStlMesh(loader, url, material) {
  const geometry = await loader.loadAsync(url);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

try {
  const app = document.getElementById('app');
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf7f7f4);

  const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.1, 2500);
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  app.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xaeb7c2, 2.4));
  const key = new THREE.DirectionalLight(0xffffff, 2.8);
  key.position.set(100, -130, 170);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 1.2);
  fill.position.set(-120, 90, 110);
  scene.add(fill);

  const clawMaterial = new THREE.MeshStandardMaterial({
    color: 0xeab308,
    roughness: 0.42,
    metalness: 0.03,
    side: THREE.DoubleSide,
  });
  const bucketMaterial = new THREE.MeshStandardMaterial({
    color: 0xf97316,
    roughness: 0.48,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });

  const loader = new STLLoader();
  const [wristMesh, jawMesh] = await Promise.all([
    loadStlMesh(loader, SOURCE_STLS.wrist, clawMaterial),
    loadStlMesh(loader, SOURCE_STLS.jaw, clawMaterial),
  ]);
  jawMesh.position.z = 52;

  const model = new THREE.Group();
  const bucketGroup = makeBucketGroup(bucketMaterial);
  model.add(wristMesh, jawMesh, bucketGroup);

  const box3 = new THREE.Box3().setFromObject(model);
  const center = new THREE.Vector3();
  box3.getCenter(center);
  model.position.sub(center);
  scene.add(model);

  const traces = makeActionTraces(jawMesh, bucketGroup);
  traces.position.copy(model.position);
  scene.add(traces);

  const size = new THREE.Vector3();
  box3.getSize(size);
  const r = Math.max(size.x, size.y, size.z, 120);
  const grid = new THREE.GridHelper(Math.max(260, r * 2.2), 20, 0x9ca3af, 0xd6d3d1);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = model.position.z - 12;
  scene.add(grid);
  scene.add(new THREE.AxesHelper(55));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = r * 0.75;
  controls.maxDistance = r * 7;

  function frameModel() {
    camera.position.set(r * 1.25, -r * 2.1, r * 1.05);
    controls.target.copy(model.position);
    controls.update();
  }
  frameModel();

  let spinning = false;
  document.getElementById('reset').onclick = frameModel;
  document.getElementById('spin').onclick = () => {
    spinning = !spinning;
    document.getElementById('spin').textContent = spinning ? 'Stop' : 'Spin';
  };
  document.getElementById('traces').onchange = (event) => {
    traces.visible = event.currentTarget.checked;
  };

  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });

  (function animate() {
    requestAnimationFrame(animate);
    if (spinning) {
      model.rotation.z += 0.007;
      traces.rotation.z = model.rotation.z;
    }
    controls.update();
    renderer.render(scene, camera);
  }());
} catch (error) {
  fail(error);
}
