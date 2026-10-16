import * as THREE from './vendor/three.module.js';
import { MapControls } from './vendor/MapControls.js';

// SydMap's viewer. Its 3D engine began as LAYRS: Amsterdam's (github.com/alexbarakov/amsterdam-by-building, MIT);
// the page around it, the line through time and the dock, is SydMap's own.

// Colours are authored in sRGB and drawn as they are.
THREE.ColorManagement.enabled = false;

// The Third Script's palette (see styles.css): a white wall for the sky, warm stone for the land, the logo's cypress
// teal for the harbour, its terracotta sun for the marks. Distant buildings fade into the white.
const SKY = '#ffffff';
const LAND = '#f3f0ea';
const CONTEXT = '#e9e6df';
const WATER = '#b9d0d2';
const MAQUETTE = '#f1eee8';
const INK = '#2c2f2a';
const MUTED = '#5f625c';
const ACCENT = '#b04f3e';
// Layer groups, in a fixed order checked for colour-blind separation between neighbours (design/README.md).
const GROUP_COLORS = ['#c0594e', '#2a7f93', '#d9a22c', '#5e8f4a', '#6b4a8c', '#c4687f', '#8a5a32', '#34548a'];
const MAX_GROUPS = GROUP_COLORS.length;
const ATTR_W = 256;
const WORKERS = Math.min(4, navigator.hardwareConcurrency || 2);
const MODE = { period: 0, floors: 1, heritage: 2, layers: 3, suburbs: 4 };
// The Suburbs lens: one hue, light to dark, from the newest age's dusk violet (clear of the Heights lens's teal); its
// light end stays clear of the white of a suburb with no figure (checked with the dataviz validator, --ordinal).
const SUB_RAMP = ['#f5d470', '#88bf8a', '#3f9b9b', '#386aa0', '#4a3486', '#2b1d45']; // sandstone to dusk violet (DESIGN.md)
const SUB_W = 512;                                  // buildings per row of the building-to-suburb texture
// Drawn icons, in the line icons' stroke (styles.css .x, .arrow).
const CLOSE = '<svg class="x" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>';
const BACK = '<svg class="arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M13 8H3.5M7.5 4L3.5 8l4 4"/></svg>';
const REPO = 'https://github.com/amarashi/SydMap';

// The binary files are stored gzipped, because Cloudflare compresses text on the way to the browser but not binary
// files (see write_bin in pipeline/s03_tiles.py). A file that starts with gzip's two magic bytes is unpacked here.
async function fetchBin(url) {
  const buf = await (await fetch(url)).arrayBuffer();
  const head = new Uint8Array(buf, 0, Math.min(2, buf.byteLength));
  if (head[0] !== 0x1f || head[1] !== 0x8b) return buf;
  return new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
}

const [config, layers, attrBuf, subData, subOf] = await Promise.all([
  fetch('data/sydney.json').then(r => r.json()),
  fetch('data/layers.json').then(r => r.json()),
  fetchBin('data/attrs.bin'),
  fetch('data/suburbs.json').then(r => r.json()).catch(() => null),
  fetchBin('data/suburbs.bin').then(b => new Uint8Array(b)).catch(() => null),
]);
const attrs = new DataView(attrBuf);
const HERITAGE_COLORS = config.heritage.colors;
const periods = config.periods;
const fmt = n => n.toLocaleString('en-AU');

// ---------- Scene ----------
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: /[?&]shot\b/.test(location.search) });
renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(SKY);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 5, 60000);
const controls = new MapControls(camera, canvas);
controls.enableDamping = true;
// Left drag turns and tilts the city; right drag, or Shift with the left, moves it.
controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
controls.rotateSpeed = 0.6;
controls.maxPolarAngle = Math.PI * 0.47;
controls.minDistance = 60;
controls.maxDistance = 22000;

// ?cam=x,z,azimuth,elevation,span overrides the home view (for sharing a view, and for screenshots).
const camParam = new URLSearchParams(location.search).get('cam')?.split(',').map(Number);
function goHome() {
  const h = camParam?.length === 5 && camParam.every(Number.isFinite)
    ? { x: camParam[0], z: camParam[1], azimuth: camParam[2], elevation: camParam[3], span: camParam[4] } : config.home;
  const az = THREE.MathUtils.degToRad(h.azimuth), el = THREE.MathUtils.degToRad(h.elevation);
  const d = h.span * 0.9;
  controls.target.set(h.x, 0, h.z);
  camera.position.set(h.x + d * Math.cos(el) * Math.sin(az), d * Math.sin(el), h.z + d * Math.cos(el) * Math.cos(az));
  controls.update();
}
goHome();

// Land and water: flat polygons in the local frame (see pipeline/s04_water.py).
async function loadPolygons(url) {
  const buf = await fetchBin(url);
  const [nPoly, nRing, nVert] = new Uint32Array(buf, 0, 3);
  const ringStart = new Uint32Array(buf, 12, nPoly + 1);
  const vertStart = new Uint32Array(buf, 12 + 4 * (nPoly + 1), nRing + 1);
  const xz = new Float32Array(buf, 12 + 4 * (nPoly + 1) + 4 * (nRing + 1), 2 * nVert);
  const ring = r => {
    const pts = [];
    for (let v = vertStart[r]; v < vertStart[r + 1]; v++) pts.push(new THREE.Vector2(xz[2 * v], -xz[2 * v + 1]));
    return pts;
  };
  const shapes = [];
  for (let p = 0; p < nPoly; p++) {
    const shape = new THREE.Shape(ring(ringStart[p]));
    for (let r = ringStart[p] + 1; r < ringStart[p + 1]; r++) shape.holes.push(new THREE.Path(ring(r)));
    shapes.push(shape);
  }
  const g = new THREE.ShapeGeometry(shapes);
  g.rotateX(-Math.PI / 2);
  return g;
}
const flat = new THREE.Group();
scene.add(flat);
const [landGeo, waterGeo, contextGeo] = await Promise.all(['land', 'water', 'context'].map(n => loadPolygons(`data/${n}.bin`)));
// The ground fades into the white wall with distance from the nearest building, so the edge follows the outline of
// the councils (their shores, the harbour between them) rather than any box. A coarse distance field over the mapped
// ground (about 50 m a cell, metres stored in tens), smoothed, sampled by the ground's shader.
const EDGE = (() => {
  contextGeo.computeBoundingBox();
  const g = contextGeo.boundingBox, cell = 50;
  const W = Math.ceil((g.max.x - g.min.x) / cell) + 1, H = Math.ceil((g.max.z - g.min.z) / cell) + 1;
  const d = new Float32Array(W * H).fill(1e6);
  const [ox, oz] = [config.attrFields.x[0], config.attrFields.z[0]];
  for (let o = 0; o < attrBuf.byteLength; o += config.attrStride) {
    const i = Math.round((attrs.getFloat32(o + ox, true) - g.min.x) / cell), j = Math.round((attrs.getFloat32(o + oz, true) - g.min.z) / cell);
    if (i >= 0 && i < W && j >= 0 && j < H) d[j * W + i] = 0;
  }
  // Two chamfer passes (straight steps of one cell, diagonal ones of 1.414), then a box blur to soften the steps.
  const pass = (dirs, ys, xs) => { for (const y of ys) for (const x of xs) { let v = d[y * W + x];
    for (const [dx, dy, w] of dirs) { const X = x + dx, Y = y + dy; if (X >= 0 && X < W && Y >= 0 && Y < H) v = Math.min(v, d[Y * W + X] + w); }
    d[y * W + x] = v; } };
  const range = (n, back) => Array.from({ length: n }, (_, k) => back ? n - 1 - k : k);
  pass([[-1, 0, 1], [0, -1, 1], [-1, -1, 1.414], [1, -1, 1.414]], range(H), range(W));
  pass([[1, 0, 1], [0, 1, 1], [1, 1, 1.414], [-1, 1, 1.414]], range(H, true), range(W, true));
  const bytes = new Uint8Array(W * H), r = 3;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let sum = 0, n = 0;
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) { const X = x + dx, Y = y + dy; if (X >= 0 && X < W && Y >= 0 && Y < H) { sum += d[Y * W + X]; n++; } }
    bytes[y * W + x] = Math.min(255, Math.round(sum / n * cell / 10));
  }
  const tex = new THREE.DataTexture(bytes, W, H, THREE.RedFormat, THREE.UnsignedByteType);
  tex.magFilter = tex.minFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return { uEdge: { value: tex }, uEdgeMin: { value: new THREE.Vector2(g.min.x, g.min.z) }, uEdgeSize: { value: new THREE.Vector2((W - 1) * cell, (H - 1) * cell) } };
})();
const EDGE_GLSL = `
  uniform sampler2D uEdge;
  uniform vec2 uEdgeMin, uEdgeSize;
  uniform vec2 uFadeRange;
  // A slow wobble of a few hundred metres, so no edge of the fade runs straight.
  float wobble(vec2 p) {
    return 0.55 * sin(p.x / 830.0 + 1.3) * sin(p.y / 1070.0 + 0.7) + 0.45 * sin((p.x - p.y) / 1530.0 + 2.1);
  }
  float edgeFade(vec2 p) {
    float metres = texture2D(uEdge, (p - uEdgeMin) / uEdgeSize).r * 2550.0;
    // Also into the wall before the mapped ground ends (only 700 m past the last buildings in the north).
    vec2 q = min(p - uEdgeMin, uEdgeMin + uEdgeSize - p);
    float w = wobble(p);
    return max(smoothstep(uFadeRange.x, uFadeRange.y, metres + 220.0 * w), 1.0 - smoothstep(0.0, 700.0, min(q.x, q.y) + 260.0 * w));
  }`;
// Land and water fade together, from 650 m beyond the nearest building to 1.6 km: the harbour between the shores
// stays clear, and the far shores and the open water go into the wall as one.
function groundMaterial(color, from = 650, to = 1600) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uWall: { value: new THREE.Color(SKY) }, uFadeRange: { value: new THREE.Vector2(from, to) }, ...EDGE },
    vertexShader: 'varying vec2 vXZ; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vXZ = w.xz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: `uniform vec3 uColor, uWall; varying vec2 vXZ; ${EDGE_GLSL}
      void main() { gl_FragColor = vec4(mix(uColor, uWall, edgeFade(vXZ)), 1.0); }`,
  });
}
const land = new THREE.Mesh(landGeo, groundMaterial(LAND));
const water = new THREE.Mesh(waterGeo, groundMaterial(WATER));
const context = new THREE.Mesh(contextGeo, groundMaterial(CONTEXT));
land.position.y = -0.05;
context.position.y = -0.1;
water.position.y = -0.4;
flat.add(land, context, water);

// ---------- Street and water names ----------
// Flat on the ground, turned along the street (pipeline/s07_labels.py). Textures are drawn on first use.
const labelData = await fetch('data/labels.json').then(r => r.json());
const labelGroup = new THREE.Group();
scene.add(labelGroup);
const labelTex = new Map();
const LABEL_PX = 64;
function textureFor(L) {
  let t = labelTex.get(L.name + L.water);
  if (t) return t;
  const c = document.createElement('canvas'), ctx = c.getContext('2d');
  // Water names in the serif's italic, as on an old harbour chart; streets in the sans.
  const font = L.water ? `italic 400 ${LABEL_PX * 0.8}px "Cormorant Garamond", Georgia, serif` : `500 ${LABEL_PX * 0.6}px Inter, sans-serif`;
  ctx.font = font;
  c.width = Math.ceil(ctx.measureText(L.name).width + LABEL_PX * 0.4);
  c.height = LABEL_PX;
  ctx.font = font;
  ctx.textBaseline = 'middle';
  ctx.lineWidth = LABEL_PX * 0.12;
  ctx.strokeStyle = L.water ? 'rgba(185,208,210,0.85)' : 'rgba(243,240,234,0.85)';
  ctx.fillStyle = L.water ? '#2a535a' : MUTED;
  ctx.strokeText(L.name, LABEL_PX * 0.2, LABEL_PX / 2);
  ctx.fillText(L.name, LABEL_PX * 0.2, LABEL_PX / 2);
  t = new THREE.CanvasTexture(c);
  t.anisotropy = 4;
  t.userData = { aspect: c.width / c.height };
  labelTex.set(L.name + L.water, t);
  return t;
}
const labelPlane = new THREE.PlaneGeometry(1, 1);
const labels = labelData.flatMap(L => L.pts.map(([x, z, ang, len, wid]) => ({ L, x, z, ang, len, wid: wid || 20, mesh: null })))
  .sort((a, b) => a.L.tier - b.L.tier || b.len - a.len);
const LABEL_FONTS = ['500 16px Inter', 'italic 400 16px "Cormorant Garamond"'];
LABEL_FONTS.forEach(f => document.fonts.load(f));
function updateLabels(dist) {
  if (!LABEL_FONTS.every(f => document.fonts.check(f))) return;
  // Label height in metres, roughly constant on screen; the harbour and main streets read larger.
  const h1 = THREE.MathUtils.clamp(dist * 0.014, 4, 60), h2 = THREE.MathUtils.clamp(dist * 0.01, 3, 15);
  // Names appear only when the camera comes close: water and main streets first, the rest closer still.
  const near = dist * 1.2, far = dist * 2;
  // Greedy collision: water and main streets first, then the longest stretches; a label is dropped
  // when an accepted one already sits within a few label heights of it.
  const taken = new Map(), C = h1 * 5; // one grid, cells as wide as the largest separation
  const cellOf = (x, z) => `${Math.floor(x / C)},${Math.floor(z / C)}`;
  const clear = (l, sep) => {
    const cx = Math.floor(l.x / C), cz = Math.floor(l.z / C);
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
      for (const q of taken.get(`${cx + i},${cz + j}`) || []) if ((q.x - l.x) ** 2 + (q.z - l.z) ** 2 < sep * sep) return false;
    }
    return true;
  };
  for (const l of labels) {
    const d = Math.hypot(l.x - camera.position.x, l.z - camera.position.z);
    const big = l.L.tier === 1, wide = l.L.tier === 0;
    let show = d < (big || wide ? far * (wide ? 1.6 : 1) : near) && dist < (wide ? 9000 : big ? 3200 : 1300);
    const sep = (big || wide ? h1 : h2) * 5;
    if (show && !clear(l, sep)) show = false;
    if (show) {
      const key = cellOf(l.x, l.z);
      if (!taken.has(key)) taken.set(key, []);
      taken.get(key).push(l);
    }
    if (show && !l.mesh) {
      const tex = textureFor(l.L);
      l.mesh = new THREE.Mesh(labelPlane, new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
      // Turn about the vertical first, then lay the plane flat.
      l.mesh.rotation.set(-Math.PI / 2, THREE.MathUtils.degToRad(-l.ang), 0, "YXZ"); // ang is measured towards +z, Y turns towards -z
      l.mesh.position.set(l.x, l.L.water ? 0.4 : 0.6, l.z);
      l.mesh.renderOrder = 2;
      labelGroup.add(l.mesh);
    }
    if (l.mesh) {
      // Never taller than the street is wide, so a name stays off the buildings; the harbour has room.
      const h = Math.min(big || wide ? h1 * (wide ? 1.5 : 1) : h2, l.wid * 0.55);
      const w = h * l.mesh.material.map.userData.aspect;
      // A name much longer than its stretch of street would spill over the buildings.
      if (show && (w > l.len * 1.1 || h < 2.5)) show = false;
      l.mesh.visible = show;
      if (show) l.mesh.scale.set(w, h, 1);
    }
  }
}

// ---------- Shared uniforms ----------
const col = c => new THREE.Color(c);
// A ramp of evenly spaced colours as a GLSL function of 0–1.
function glslRamp(name, hexes) {
  const v = hexes.map(h => { const c = col(h); return `vec3(${c.r.toFixed(3)}, ${c.g.toFixed(3)}, ${c.b.toFixed(3)})`; });
  const n = v.length - 1;
  return `vec3 ${name}(float t) { t = clamp(t, 0.0, 1.0) * ${n}.0;
    ${v.slice(0, -1).map((a, i) => `if (t <= ${i + 1}.0) return mix(${a}, ${v[i + 1]}, t - ${i}.0);`).join(' ')}
    return ${v[n]}; }`;
}
// The Suburbs lens's lookups: building to suburb (by gid, SUB_W a row), and the suburbs' values, refilled each year.
const nB = attrBuf.byteLength / config.attrStride;
const subOk = !!(subData && subOf && subOf.length === nB);
const subOfTex = (() => {
  const rows = Math.ceil(nB / SUB_W), d = new Float32Array(SUB_W * rows).fill(255);
  if (subOk) d.set(subOf);
  const t = new THREE.DataTexture(d, SUB_W, rows, THREE.RedFormat, THREE.FloatType);
  t.needsUpdate = true;
  return t;
})();
const subValTex = new THREE.DataTexture(new Float32Array(256).fill(-1), 256, 1, THREE.RedFormat, THREE.FloatType);
subValTex.needsUpdate = true;
const uniforms = {
  uYear: { value: config.yearMax },
  uYearFrom: { value: config.yearMin - 1 },
  uMode: { value: MODE.period },
  uPalette: { value: periods.map(p => col(p.color)) },
  uMask: { value: periods.map(() => 1) },
  uNow: { value: 0 },                              // seconds, for tiles dropping in as they load
  uPlaying: { value: 0 },                          // while the film plays buildings fly in rather than grow
  uRise: { value: 0.01 },                          // years a building's entrance spans; only the film widens it
  uLayerAt: { value: -10 },                        // seconds; when a context layer opened, its buildings rise
  uGroupBit: { value: Array(MAX_GROUPS).fill(-1) },
  uGroupColor: { value: GROUP_COLORS.map(col) },
  uMaquette: { value: col(MAQUETTE) },
  uHeritage: { value: HERITAGE_COLORS.map(col) },
  uDocOnly: { value: 0 },                          // 1: estimated years in white, documented ones in colour
  uHover: { value: -1 },
  uSelected: { value: -1 },
  uBlind: { value: 0 },
  uSubOf: { value: subOfTex },                     // each building's suburb (s10_suburbs), 255 none
  uSubVal: { value: subValTex },                   // each suburb's measure in the year, 0–1 along the ramp, -1 none
  uFogColor: { value: col(SKY) },
  uFog: { value: new THREE.Vector2(9000, 26000) },
};

// The Suburbs lens's ground: each suburb's land tinted by its value, with its outline in white (pipeline/s10_suburbs.py).
// The polygons share land.bin's layout; subData.poly names the suburb of each.
const subGround = new THREE.Group();
subGround.visible = false;
flat.add(subGround);
if (subOk) {
  const buf = await fetchBin('data/suburbs-land.bin');
  const [nPoly, nRing, nVert] = new Uint32Array(buf, 0, 3);
  const ringStart = new Uint32Array(buf, 12, nPoly + 1);
  const vertStart = new Uint32Array(buf, 12 + 4 * (nPoly + 1), nRing + 1);
  const xz = new Float32Array(buf, 12 + 4 * (nPoly + 1) + 4 * (nRing + 1), 2 * nVert);
  const ring = r => Array.from({ length: vertStart[r + 1] - vertStart[r] }, (_, k) => new THREE.Vector2(xz[2 * (vertStart[r] + k)], -xz[2 * (vertStart[r] + k) + 1]));
  const pos = [], sub = [], idx = [], line = [];
  for (let p = 0; p < nPoly; p++) {
    const outer = ring(ringStart[p]), holes = [];
    for (let r = ringStart[p] + 1; r < ringStart[p + 1]; r++) holes.push(ring(r));
    const base = pos.length / 3, pts = [outer, ...holes].flat();
    for (const v of pts) { pos.push(v.x, 0, -v.y); sub.push(subData.poly[p]); }
    for (const t of THREE.ShapeUtils.triangulateShape(outer, holes)) idx.push(base + t[0], base + t[1], base + t[2]);
    for (const r of [outer, ...holes]) r.forEach((v, k) => { const w = r[(k + 1) % r.length]; line.push(v.x, 0, -v.y, w.x, 0, -w.y); });
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('sub', new THREE.Float32BufferAttribute(sub, 1));
  g.setIndex(idx);
  const fill = new THREE.Mesh(g, new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    uniforms: { uLand: { value: col(LAND) }, uWall: { value: col(SKY) }, uFadeRange: { value: new THREE.Vector2(650, 1600) }, uSubVal: uniforms.uSubVal, ...EDGE },
    vertexShader: `in float sub; out vec2 vXZ; flat out int vSub;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vXZ = w.xz; vSub = int(sub + 0.5); gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 uLand, uWall; uniform sampler2D uSubVal; in vec2 vXZ; flat in int vSub; out vec4 outColor;
      ${EDGE_GLSL.replace(/texture2D/g, 'texture')} ${glslRamp('subRamp', SUB_RAMP)}
      void main() { float v = texelFetch(uSubVal, ivec2(vSub, 0), 0).r;
        vec3 c = v < 0.0 ? uLand : mix(uLand, subRamp(v), 0.5);
        outColor = vec4(mix(c, uWall, edgeFade(vXZ)), 1.0); }`,
  }));
  fill.position.y = -0.03;
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(line, 3));
  const outline = new THREE.LineSegments(lineGeo, new THREE.LineBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9 }));
  outline.position.y = 0.05;
  subGround.add(fill, outline);
}

const VERT = /* glsl */`
  in float bld;
  uniform sampler2D uAttr, uSubOf, uSubVal;
  uniform float uYear, uYearFrom, uMode, uHover, uSelected, uBlind, uNow, uBorn, uPlaying, uRise, uLayerAt, uDocOnly;
  uniform vec3 uPalette[${periods.length}];
  uniform float uMask[${periods.length}];
  uniform int uGroupBit[${MAX_GROUPS}];
  uniform vec3 uGroupColor[${MAX_GROUPS}];
  uniform vec3 uMaquette;
  uniform vec3 uHeritage[${HERITAGE_COLORS.length}];
  out vec3 vColor;
  out vec3 vWorld;
  out float vGid;
  out float vShaped;

  vec3 floorsRamp(float f) {
    float t = clamp(log(f) / log(40.0), 0.0, 1.0);
    // The logo's cypress teal, from a pale wash to the deepest shade of its trees.
    vec3 a = vec3(0.89, 0.925, 0.925), b = vec3(0.576, 0.718, 0.741), c = vec3(0.204, 0.353, 0.376), d = vec3(0.075, 0.157, 0.169);
    return t < 0.33 ? mix(a, b, t / 0.33) : t < 0.66 ? mix(b, c, (t - 0.33) / 0.33) : mix(c, d, (t - 0.66) / 0.34);
  }

  ${glslRamp('subRamp', SUB_RAMP)}

  bool hasBit(vec4 words, int bit) {
    int w = bit / 16;
    float v = w == 0 ? words.x : w == 1 ? words.y : w == 2 ? words.z : words.w;
    return ((int(v + 0.5) >> (bit - w * 16)) & 1) == 1;
  }

  void main() {
    int i = int(bld + 0.5);
    bool shaped = i >= 32768;          // a pale surface: the Opera House's shells (pipeline/s03_tiles.py)
    i = i % 32768;
    ivec2 tc = ivec2(2 * (i % ${ATTR_W}), i / ${ATTR_W});
    vec4 a = texelFetch(uAttr, tc, 0);
    vec4 lay = texelFetch(uAttr, tc + ivec2(1, 0), 0);
    float year = a.x;
    int pf = int(a.y + 0.5);
    int period = pf % 16;
    int flag = pf / 16;
    vGid = a.w;
    vShaped = shaped ? 1.0 : 0.0;
    float vis = uMode < 0.5 ? uMask[period] : 1.0;
    float g = clamp((uYear - year + 1.0) / uRise, 0.0, 1.0);
    g = g * g * (3.0 - 2.0 * g);
    if (g <= 0.003 || vis <= 0.003) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }

    // Entrances, only while the film plays and while tiles load: a building drops in from its own side of the
    // sky, the same side every time (seeded by its id). Filters and scrubbing change the city at once.
    vec3 p = position;
    float seed = fract(sin(a.w * 12.9898) * 43758.5453);
    float arrive = clamp((uNow - uBorn) / 0.9 - seed * 0.35, 0.0, 1.0);
    float fly = 1.0 - arrive;
    if (uPlaying > 0.5) fly = max(fly, 1.0 - g);
    if (fly > 0.0) {
      float e = fly * fly * fly;
      float ang = seed * 6.2831853;
      // positions are in decimetres: a few hundred metres sideways and up
      p += vec3(cos(ang), 0.0, sin(ang)) * (1800.0 + 1600.0 * fract(seed * 7.13)) * e;
      p.y += (2600.0 + 2400.0 * fract(seed * 3.71)) * e;
    }
    vec3 c;
    if (uMode < 0.5) {
      c = uPalette[period];
      // Estimated years are paler; with "documented only" they leave the colour altogether.
      if (flag >= 1) c = mix(c, uMaquette, uDocOnly > 0.5 && flag >= 2 ? 1.0 : 0.32);
    } else if (uMode < 1.5) {
      c = floorsRamp(mod(a.z, 128.0));
    } else if (uMode < 2.5) {
      c = uHeritage[int(a.z / 128.0)];
    } else if (uMode < 3.5) {
      c = uMaquette;
      for (int g = 0; g < ${MAX_GROUPS}; g++) {
        if (uGroupBit[g] >= 0 && hasBit(lay, uGroupBit[g])) {
          c = uGroupColor[g];
          // Opening a layer: its buildings rise out of the ground in a quick wave, overshoot a little, settle.
          float k = clamp((uNow - uLayerAt) / 0.55 - seed * 0.6, 0.0, 1.0);
          float q = k - 1.0;
          p.y *= 1.0 + 2.70158 * q * q * q + 1.70158 * q * q;
          break;
        }
      }
    } else {
      int gi = int(a.w + 0.5);
      float s = texelFetch(uSubOf, ivec2(gi % ${SUB_W}, gi / ${SUB_W}), 0).r;
      float v = s > 254.5 ? -1.0 : texelFetch(uSubVal, ivec2(int(s + 0.5), 0), 0).r;
      c = v < 0.0 ? uMaquette : subRamp(v);
    }
    // The Opera House's shells, a lighter tint of its colour: white tiles over a granite podium.
    if (shaped) c = mix(c, vec3(1.0), 0.3);
    if (year <= uYearFrom) c = mix(c, uMaquette, 0.8);
    // A quest's question about one building turns it the sun's terracotta; a year riddle also hides every other age.
    if (uBlind > 0.5 && vGid == uSelected) c = vec3(0.690, 0.310, 0.243);
    else if (uBlind > 0.5 && uBlind < 1.5) c = uMaquette;
    if (vGid == uHover || (vGid == uSelected && uBlind < 0.5)) c = mix(c, vec3(0.173, 0.184, 0.165), 0.38);
    vColor = c;
    vec4 w = modelMatrix * vec4(p, 1.0);
    vWorld = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }
`;

const FRAG = /* glsl */`
  precision highp float;
  uniform vec3 uFogColor;
  uniform vec2 uFog;
  in vec3 vColor;
  in vec3 vWorld;
  in float vGid;
  in float vShaped;
  out vec4 outColor;
  void main() {
    #ifdef PICK
      float id = vGid + 1.0;
      outColor = vec4(mod(id, 256.0), mod(floor(id / 256.0), 256.0), floor(id / 65536.0), 255.0) / 255.0;
    #else
      vec3 n = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
      // A low afternoon sun from the north-west (the southern hemisphere's sunny side), a soft sky from above.
      float sun = max(dot(n, normalize(vec3(-0.55, 0.55, -0.62))), 0.0);
      float light = mix(0.66 + 0.34 * sun, 1.04, smoothstep(0.86, 0.94, n.y));
      // The Opera House's curved shells also take a soft fill from the south-east, to keep their form against the sun.
      if (vShaped > 0.5) light = 0.6 + 0.3 * sun + 0.2 * max(dot(n, normalize(vec3(0.6, 0.45, 0.66))), 0.0);
      float foot = mix(0.82, 1.0, clamp(vWorld.y / 12.0, 0.0, 1.0));
      vec3 c = vColor * light * foot;
      float d = length(vWorld - cameraPosition);
      c = mix(c, uFogColor, smoothstep(uFog.x, uFog.y, d));
      outColor = vec4(c, 1.0);
    #endif
  }
`;

function makeMaterial(tex, pick, born) {
  return new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    uniforms: { ...uniforms, uAttr: { value: tex }, uBorn: born },
    vertexShader: VERT,
    fragmentShader: FRAG,
    defines: pick ? { PICK: 1 } : {},
    side: THREE.DoubleSide,
  });
}

// ---------- Tiles ----------
const meshes = [];
let loaded = 0;
const queue = [...config.tiles];
const pool = Array.from({ length: WORKERS }, () => new Worker('worker.js', { type: 'module' }));

function addTile(m) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(m.pos, 3));
  g.setAttribute('bld', new THREE.BufferAttribute(m.bld, 1));
  g.setIndex(new THREE.BufferAttribute(m.idx, 1));
  const rows = Math.ceil(m.nB / ATTR_W);
  const data = new Float32Array(ATTR_W * 2 * rows * 4);
  data.set(m.attr);
  const tex = new THREE.DataTexture(data, ATTR_W * 2, rows, THREE.RGBAFormat, THREE.FloatType);
  tex.needsUpdate = true;
  const born = { value: performance.now() / 1000 };
  const mesh = new THREE.Mesh(g, makeMaterial(tex, false, born));
  mesh.userData = { draw: mesh.material, pick: makeMaterial(tex, true, born) };
  mesh.scale.setScalar(0.1);
  mesh.position.set(m.origin[0], 0, m.origin[1]);
  scene.add(mesh);
  meshes.push(mesh);
}

// Tiles come in packs (see pipeline/s03_tiles.py); a tile is ready once its pack has arrived.
const packs = Object.fromEntries(config.packs.map(name => [name, fetchBin(`data/${name}`)]));
for (const w of pool) {
  const next = async () => {
    const t = queue.shift();
    if (!t) return;
    const buf = (await packs[t.pack]).slice(t.offset, t.offset + t.length);
    w.postMessage({ buf, id: t.file }, [buf]);
  };
  w.onmessage = ({ data }) => {
    addTile(data);
    loaded++;
    document.getElementById('progress').textContent = Math.round(100 * loaded / config.tiles.length);
    if (loaded === config.tiles.length) { document.getElementById('loading').hidden = true; document.body.dataset.ready = '1'; }
    next();
  };
  next();
}

// ---------- Picking ----------
const pickTarget = new THREE.WebGLRenderTarget(1, 1);
const pickPixel = new Uint8Array(4);
function pick(x, y) {
  const w = renderer.domElement.clientWidth, h = renderer.domElement.clientHeight;
  camera.setViewOffset(w, h, x, y, 1, 1);
  for (const m of meshes) m.material = m.userData.pick;
  flat.visible = false;
  labelGroup.visible = false;
  renderer.setRenderTarget(pickTarget);
  renderer.setClearColor(0x000000, 0);
  renderer.clear();
  renderer.render(scene, camera);
  renderer.readRenderTargetPixels(pickTarget, 0, 0, 1, 1, pickPixel);
  renderer.setRenderTarget(null);
  renderer.setClearColor(SKY, 1);
  flat.visible = true;
  labelGroup.visible = true;
  for (const m of meshes) m.material = m.userData.draw;
  camera.clearViewOffset();
  return pickPixel[0] + pickPixel[1] * 256 + pickPixel[2] * 65536 - 1;
}

// ---------- Building lookup ----------
// attrs.bin: one fixed-size record per building; config.attrFields gives each field's offset and type.
const READ = { '<f8': 'getFloat64', '<f4': 'getFloat32', '<i4': 'getInt32', '<u4': 'getUint32', '<i2': 'getInt16', '<u2': 'getUint16', '|u1': 'getUint8' };
const FIELDS = Object.entries(config.attrFields).map(([name, [off, type]]) => [name, off, READ[type]]);
const groupsByBit = layers.flatMap(L => L.groups.map(g => ({ ...g, layer: L })));
function building(gid) {
  const o = gid * config.attrStride, b = { gid };
  for (const [name, off, fn] of FIELDS) b[name] = attrs[fn](o + off, true);
  b.height = b.h / 10;
  b.groups = groupsByBit.filter(g => g.bit < 32 ? (b.lay0 >>> g.bit) & 1 : (b.lay1 >>> (g.bit - 32)) & 1);
  return b;
}

const periodOf = y => periods.find(p => y >= p.from && y <= p.to) || periods[0];

// ---------- Reading ----------
let wiki = [], names = [], heritageItems = [];
const ready = Promise.all([
  fetch('data/wiki.json').then(r => r.json()).then(w => { wiki = w; }),
  fetch('data/names.json').then(r => r.json()).then(n => { names = n; }),
  fetch('data/heritage.json').then(r => r.json()).then(h => { heritageItems = h; }),
]);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const link = (href, text) => `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(text)}</a>`;
const phone = matchMedia('(max-width: 720px)');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const dot = color => `<i class="dot" style="background:${color}"></i>`;
// An age's label is its dates and its name ("1870–1890 The boom years"); the line shows them apart.
const ageParts = p => { const m = p.label.match(/^(Before \d{4}|\d{4}–(?:\d{4})?)\s+(.*)$/); return m ? { dates: m[1], name: m[2] } : { dates: '', name: p.label }; };
const nameOf = (b, w = b.wk >= 0 ? wiki[b.wk] : null) => w?.label || (b.nm >= 0 ? names[b.nm] : null);

const HEIGHT_NOTE = ['measured, OpenStreetMap', 'from its storeys, OpenStreetMap', 'modelled, GlobalBuildingAtlas', 'assumed: two storeys', 'highest point above sea level, Wikipedia'];
const range = b => b.yfrom !== b.yto ? `${b.yfrom}–${b.yto}` : `${b.yfrom}`;
// How the year is known, in a sentence: the first words name the kind of evidence, as Notes does.
function datingNote(b, w, h) {
  const src = { 0: 'Wikidata', 1: 'its Wikipedia article', 2: 'OpenStreetMap' }[b.dsrc] || 'a documented source';
  switch (b.flag) {
    case 0: return `Documented: the year comes from ${src}.`;
    case 1: return `Documented, roughly: ${src} gives ${range(b)}, so read it as “around then”.`;
    case 2: return `From its strata plan, SP${b.sp}, registered around ${b.year}. Apartments are strata-titled when they are
      finished; an older building turned into apartments later shows the year it was converted.`;
    case 3: if (b.dsrc === 4) return `From its heritage listing: part of ${esc(h?.name || 'a State Heritage Register listing')}, which its Wikipedia article dates ${range(b)}. Not every building of a listed place is as old as the place.`;
      return `Estimated from its heritage area: ${h?.hca ? `the City counts it in the historic fabric of the ${esc(h.hca)} heritage conservation area` : 'it is heritage-listed'}, and it is dated from the documented heritage buildings around it.`;
    default: return `Estimated from its neighbours: the dated buildings around it of a similar height.${b.height >= 46 ? ' At over 46 m, Sydney’s height limit until 1957, it was built after that.' : ''}${b.heritage === 5 ? ' Its heritage area counts it as later than the area’s historic fabric.' : ''}`;
  }
}
function groupColor(g) {
  return GROUP_COLORS[g.layer.groups.findIndex(x => x.bit === g.bit)] || GROUP_COLORS[0];
}

// A building in the dock: photo, name and year, how the year is known, the stories it is in, facts, sources.
function buildingHtml(gid) {
  const b = building(gid);
  const w = b.wk >= 0 ? wiki[b.wk] : null;
  const hItem = b.hi >= 0 ? heritageItems[b.hi] : null;
  const name = nameOf(b, w);
  const period = periodOf(b.year);
  const shape = config.shapes?.[gid];
  const im = w?.image;
  const photo = im?.thumb ? `<figure class="b-photo"><img src="${esc(im.thumb)}" alt=""><figcaption>Photo: ${link(im.page || im.thumb, im.artist || 'Wikimedia Commons')}${im.license ? `, ${im.licenseUrl ? link(im.licenseUrl, im.license) : esc(im.license)}` : ''}</figcaption></figure>` : '';
  const facts = [
    ['Height', `${b.height.toFixed(1)} m<small class="src-note">${HEIGHT_NOTE[b.hsrc]}</small>`],
    shape && ['Shape', `${esc(shape[0])}<small class="src-note">${link(shape[2], shape[1])}</small>`],
    !(shape && b.fsrc !== 0) && ['Storeys', `${b.floors ?? Math.max(1, Math.round(b.height / 3.2))}<small class="src-note">${b.fsrc === 0 ? 'OpenStreetMap' : 'height ÷ 3.2 m'}</small>`],
    w?.architects?.length && [w.architects.length > 1 ? 'Architects' : 'Architect', w.architects.map(esc).join(', ')],
    w?.styles?.length && ['Style', w.styles.map(esc).join(', ')],
    b.heritage && ['Heritage', `${esc(config.heritage.labels[b.heritage - 1])}`],
    hItem?.name && [hItem.kind === 'shr' ? 'Listing' : 'Heritage item', esc(hItem.name)],
    hItem?.hca && ['Heritage area', esc(hItem.hca)],
    b.sp && ['Strata plan', `SP${b.sp}`],
  ].filter(Boolean);
  const osmUrl = b.osm > 0 ? `https://www.openstreetmap.org/way/${b.osm}` : b.osm < 0 ? `https://www.openstreetmap.org/relation/${-b.osm}` : null;
  const sources = [
    w?.wiki?.url && link(w.wiki.url, 'Wikipedia'),
    w?.qid && link(`https://www.wikidata.org/wiki/${w.qid}`, 'Wikidata'),
    hItem?.shrId && link(`https://www.hms.heritage.nsw.gov.au/App/Item/ViewItem?itemId=${hItem.shrId}`, 'State Heritage Register'),
    osmUrl && link(osmUrl, 'OpenStreetMap'),
  ].filter(Boolean);
  const stories = b.groups.map(g => {
    const note = g.layer.notes?.[gid];
    return `<li>${dot(groupColor(g))}<div><b>${esc(g.layer.title)}</b> <span>${esc(g.label)}</span>
      ${note?.story ? `<p>${esc(note.story)}${note.source ? ` ${link(note.source, 'Source')}` : ''}</p>` : ''}</div></li>`;
  }).join('');
  return `<article class="dock-page b-card${photo ? ' has-photo' : ''}">${photo}
    <header class="b-head"><h2 id="dock-title">${name ? esc(name) : 'A building'}</h2>
      <div class="b-when"><span class="y">${b.flag >= 1 ? 'c. ' : ''}${b.year}</span><span class="age">${dot(period.color)}${esc(ageParts(period).name)}</span></div></header>
    <section><h3>How we know the year</h3><p class="how">${datingNote(b, w, hItem)}${b.flag >= 1 && b.yfrom !== b.yto ? `<span class="range">Likely ${b.yfrom}–${b.yto}</span>` : ''}</p></section>
    <section><dl>${facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl></section>
    ${w?.wiki?.extract ? `<section><h3>From Wikipedia</h3><p class="extract">${esc(w.wiki.extract)}</p><button class="read-on" hidden>Read on</button></section>` : ''}
    ${stories ? `<section><h3>In the stories</h3><ul class="chips">${stories}</ul></section>` : ''}
    ${sources.length ? `<section class="sources"><h3>Sources</h3><p>${sources.join(' · ')}</p></section>` : ''}</article>`;
}

// ---------- The dock ----------
// One thing to read at a time, on the right (a sheet from the bottom on a phone): the notes, the stories, a story, a
// building, the walks, or the walk in hand. A building opened from a story or a walk offers the way back.
const dock = document.getElementById('dock');
const dockLive = document.getElementById('dock-live');
const notesEl = document.getElementById('notes');
const dockBack = dock.querySelector('.dock-back');
let dockView = null;
function openDock(view, html, back = null) {
  dockView = view;
  notesEl.hidden = view !== 'notes';
  dockLive.innerHTML = view === 'notes' ? '' : html;
  dock.classList.toggle('has-back', !!back);
  dockBack.hidden = !back;
  if (back) { dockBack.innerHTML = `${BACK}${esc(back.label)}`; dockBack.onclick = back.go; }
  dock.setAttribute('aria-label', (view === 'notes' ? notesEl : dockLive).querySelector('h2')?.textContent || 'Details');
  dock.hidden = false;
  dock.scrollTop = 0;
  document.body.classList.add('docked');
  syncBar();
}
function closeDock() {
  dock.hidden = true;
  document.body.classList.remove('docked');
  dockView = null;
  syncBar();
}
dock.querySelector('.dock-close').onclick = () => {
  if (dockView === 'walk') { closeQuest(); return; }
  if (dockView === 'building') unpin();
  closeDock();
};
function syncBar() {
  document.querySelector('.walks-open').setAttribute('aria-pressed', String(dockView === 'walks' || dockView === 'walk'));
  document.querySelector('.notes-open').setAttribute('aria-pressed', String(dockView === 'notes'));
}

// ---------- A building: a label at the pointer, the dock on a click ----------
const tip = document.getElementById('tip');
let hoverGid = -1;
function showTip(gid, x, y) {
  if (phone.matches || gid < 0 || cardsLocked() || gid === pinnedGid) { tip.hidden = true; hoverGid = -1; return; }
  if (gid !== hoverGid) {
    hoverGid = gid;
    const b = building(gid), name = nameOf(b), p = periodOf(b.year), s = subOfGid(gid);
    if (uniforms.uMode.value === MODE.suburbs && s >= 0 && measure) {
      const a = subAt(measure, s, subYear());
      tip.innerHTML = `<b>${esc(SUBS[s].name)}</b><span>${a ? `${dot(subColor(subT(measure, a.v)))}${fmtM(measure, a.v)} ${esc(measure.unit)}` : `No figure for ${subYear()}`}</span>`;
    } else tip.innerHTML = `${name ? `<b>${esc(name)}</b>` : ''}<span>${dot(p.color)}${b.flag >= 1 ? 'c. ' : ''}${b.year} · ${esc(ageParts(p).name)}</span>`;
  }
  tip.hidden = false;
  const r = tip.getBoundingClientRect();
  tip.style.left = Math.max(12, Math.min(x + 16, innerWidth - r.width - 12)) + 'px';
  tip.style.top = (y + r.height + 30 > innerHeight ? y - r.height - 14 : y + 18) + 'px';
}

let pinnedGid = -1;
let buildingBack = null;
function unpin() {
  pinnedGid = -1;
  uniforms.uSelected.value = quizGid;
}
function openBuilding(gid, back = backFromHere()) {
  pinnedGid = gid;
  uniforms.uSelected.value = gid;
  tip.hidden = true;
  buildingBack = back;
  openDock('building', buildingHtml(gid), back);
  dockLive.querySelector('.b-photo img')?.addEventListener('error', e => e.target.closest('.b-photo')?.remove());
  const extract = dockLive.querySelector('.extract'), more = dockLive.querySelector('.read-on');
  if (extract && extract.scrollHeight > extract.clientHeight + 4) { more.hidden = false; more.onclick = () => { extract.classList.add('open'); more.remove(); }; }
}
// The way back from a building: to the walk in hand, the story open in the dock, or the stories.
function backFromHere() {
  if (dockView === 'building') return buildingBack;
  if (quest) return { label: 'Back to the walk', go: () => { unpin(); renderQuest(); } };
  if (dockView === 'story' && activeLayer) { const L = activeLayer; return { label: L.title, go: () => { unpin(); showStory(L); } }; }
  if (dockView === 'stories') return { label: 'All stories', go: () => { unpin(); showStories(); } };
  return null;
}
// Kept for the walks and the screenshots: a negative id lets go of the building, any other opens it.
function pinCard(gid) {
  if (gid < 0) { const was = dockView === 'building'; unpin(); if (was && !quest) closeDock(); return; }
  openBuilding(gid);
}
addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (document.body.classList.contains('finding') || !findList.hidden) { closeFind(); return; }
  if (dockView && dockView !== 'walk') { if (dockView === 'building') unpin(); closeDock(); }
});

// A click (not a drag) opens the building under the pointer, or lets it go on empty ground.
let pointer = null, dragging = false, downAt = null;
canvas.addEventListener('pointermove', e => { pointer = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerdown', e => { dragging = true; downAt = [e.clientX, e.clientY]; tip.hidden = true; });
canvas.addEventListener('pointerup', e => {
  dragging = false;
  if (!downAt) return;
  if (Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  const gid = pick(e.clientX, e.clientY);
  if (quest && !solved && qStep().kind === 'find') { questClick(gid); return; }
  if (cardsLocked()) return;
  if (uniforms.uMode.value === MODE.suburbs && subOfGid(gid) >= 0) { showSuburb(subOfGid(gid), gid, { label: 'All suburbs', go: showSuburbs }); return; }
  if (gid < 0 || gid === pinnedGid) { pinCard(-1); return; }
  openBuilding(gid);
});
canvas.addEventListener('pointerleave', () => { pointer = null; tip.hidden = true; uniforms.uHover.value = -1; });

// ---------- Flying to a building ----------
let flight = null;
function flyTo(x, z, done, distance = 520) {
  const dir = camera.position.clone().sub(controls.target).normalize();
  if (dir.y < 0.45) { dir.y = 0.45; dir.normalize(); }
  const target = new THREE.Vector3(x, 0, z);
  flight = { t0: performance.now(), dur: 1400, fromT: controls.target.clone(), toT: target,
    fromP: camera.position.clone(), toP: target.clone().add(dir.multiplyScalar(distance)), done };
}
function stepFlight(now) {
  if (!flight) return;
  const k = Math.min(1, (now - flight.t0) / flight.dur), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
  controls.target.lerpVectors(flight.fromT, flight.toT, e);
  camera.position.lerpVectors(flight.fromP, flight.toP, e);
  if (k >= 1) { const d = flight.done; flight = null; d?.(); }
}
// On a phone the dock is a sheet over the lower half: aim short of the building so it lands in the upper half.
function aimFly(x, z, dist, done = null) {
  if (phone.matches && !dock.hidden) {
    const f = controls.target.clone().sub(camera.position).setY(0).normalize();
    x -= f.x * dist * 0.35; z -= f.z * dist * 0.35;
  }
  flyTo(x, z, done, dist);
}

// ---------- Find a building or street ----------
// Every named building (from Wikipedia and Wikidata, or OpenStreetMap's names) and every street and stretch of water
// the map labels. Prefix matches first, then the start of a later word, then anywhere.
const findForm = document.querySelector('.find');
const findInput = document.getElementById('find');
const findList = document.getElementById('find-results');
const findIndex = [];
const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
ready.then(() => {
  const seen = new Map();
  const [ow, on, oy, ox, oz, oh] = ['wk', 'nm', 'year', 'x', 'z', 'h'].map(k => config.attrFields[k][0]);
  for (let gid = 0, o = 0; o < attrBuf.byteLength; gid++, o += config.attrStride) {
    const wk = attrs.getInt32(o + ow, true), nm = attrs.getInt32(o + on, true);
    const label = wk >= 0 ? wiki[wk]?.label : nm >= 0 ? names[nm] : null;
    if (!label) continue;
    const h = attrs.getUint16(o + oh, true), prev = seen.get(label);
    if (prev && prev.h >= h) continue;
    seen.set(label, { label, kind: 'building', gid, h, known: wk >= 0, year: attrs.getInt16(o + oy, true), x: attrs.getFloat32(o + ox, true), z: attrs.getFloat32(o + oz, true) });
  }
  findIndex.push(...seen.values());
  const places = new Map();
  for (const L of labelData) if (!places.has(L.name) && L.pts?.length) places.set(L.name, { label: L.name, kind: L.water ? 'water' : 'street', x: L.pts[0][0], z: L.pts[0][1] });
  findIndex.push(...places.values());
  SUBS.forEach((S, s) => findIndex.push({ label: S.name, kind: 'suburb', s, x: S.x, z: S.z }));
  for (const e of findIndex) e.key = fold(e.label);
});
let findHits = [], findAt = -1;
function search(q) {
  const k = fold(q.trim());
  if (k.length < 2) return [];
  const word = new RegExp(`(^|\\s)${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\s|$)`);
  const score = e => word.test(e.key) ? (e.key.startsWith(k) ? 0 : 1) : e.key.startsWith(k) ? 2 : e.key.includes(' ' + k) ? 3 : e.key.includes(k) ? 4 : -1;
  const rank = e => e.kind === 'building' ? (e.known ? 0 : 2) : e.kind === 'suburb' ? 0 : 1;
  return findIndex.map(e => [score(e), e]).filter(([s]) => s >= 0)
    .sort((a, b) => a[0] - b[0] || rank(a[1]) - rank(b[1]) || a[1].label.length - b[1].label.length)
    .slice(0, 8).map(([, e]) => e);
}
function renderFind() {
  findHits = search(findInput.value);
  findAt = findHits.length ? 0 : -1;
  const q = findInput.value.trim();
  findList.innerHTML = findHits.length ? findHits.map((e, i) => `<li role="option" id="find-${i}" data-i="${i}" aria-selected="${i === findAt}">
      <b>${esc(e.label)}</b><small>${e.kind === 'building' ? `Built ${e.year}` : e.kind === 'water' ? 'Water' : e.kind === 'suburb' ? 'Suburb' : 'Street'}</small></li>`).join('')
    : q.length >= 2 ? `<li class="empty">Nothing by that name on the map.</li>` : '';
  findList.hidden = !findList.innerHTML;
  findInput.setAttribute('aria-expanded', String(!findList.hidden));
  findInput.setAttribute('aria-activedescendant', findAt >= 0 ? `find-${findAt}` : '');
}
function moveFind(d) {
  if (!findHits.length) return;
  findAt = (findAt + d + findHits.length) % findHits.length;
  findList.querySelectorAll('[role="option"]').forEach((li, i) => li.setAttribute('aria-selected', String(i === findAt)));
  findInput.setAttribute('aria-activedescendant', `find-${findAt}`);
}
function choose(e) {
  closeFind();
  findInput.value = '';
  findInput.blur();
  if (e.kind === 'building') aimFly(e.x, e.z, 420, () => openBuilding(e.gid));
  else if (e.kind === 'suburb') flySuburb(e.s, () => { if (uniforms.uMode.value === MODE.suburbs) showSuburb(e.s, -1, { label: 'All suburbs', go: showSuburbs }); });
  else aimFly(e.x, e.z, e.kind === 'water' ? 1800 : 900);
}
function closeFind() {
  findList.hidden = true;
  findInput.setAttribute('aria-expanded', 'false');
  document.body.classList.remove('finding');
}
findInput.addEventListener('input', renderFind);
findInput.addEventListener('focus', renderFind);
findInput.addEventListener('keydown', e => {
  if (e.key === 'ArrowDown') { e.preventDefault(); moveFind(1); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); moveFind(-1); }
});
findForm.addEventListener('submit', e => { e.preventDefault(); if (findHits[findAt]) choose(findHits[findAt]); });
findList.addEventListener('pointerdown', e => { const li = e.target.closest('[data-i]'); if (li) { e.preventDefault(); choose(findHits[+li.dataset.i]); } });
findInput.addEventListener('blur', () => setTimeout(() => { if (document.activeElement !== findInput) closeFind(); }, 120));
document.querySelector('.find-open').onclick = () => { document.body.classList.add('finding'); findInput.focus(); };

// ---------- Walks ----------
// Short routes through the city told as riddles (pipeline/quests.py, checked by s08_quests): find a stop on the map,
// guess a building's year with the colours off, or pick one of three answers. Each stop earns up to three suns; a
// hint or a wrong answer costs one. Progress stays in this browser.
let quests = [];
fetch('data/quests.json').then(r => r.ok ? r.json() : []).then(q => { quests = q; }).catch(() => {});
const LEVEL = ['', 'Easy', 'Medium', 'Hard'];
const qStore = () => { try { return JSON.parse(localStorage.getItem('syd-quests') || '{}'); } catch { return {}; } };
function qSave(id, patch) {
  try { const p = qStore(); p[id] = { ...(p[id] || {}), ...patch }; localStorage.setItem('syd-quests', JSON.stringify(p)); } catch {}
}
// Suns: lit for each one earned, of three.
const suns = (n, of = 3) => `<span class="suns" role="img" aria-label="${n} of ${of}">${Array.from({ length: of }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</span>`;
// A small seeded generator: the same circle offset and answer order every time a step is played.
function rng(seed) { let h = 2166136261; for (const c of seed) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) ^ Math.imul(h ^ (h >>> 13), 3266489909)) >>> 0) / 4294967296; }

function showWalks() {
  const p = qStore();
  const total = quests.reduce((n, q) => n + (p[q.id]?.best || 0), 0), max = quests.reduce((n, q) => n + q.steps.length * 3, 0);
  const route = q => {
    const st = p[q.id] || {}, n = q.steps.length, done = Math.min(st.step || 0, n), complete = done >= n;
    return `<li class="route"><h3>${esc(q.title)}</h3><p>${esc(q.intro)}</p>
      <div class="route-meta"><span>${LEVEL[q.level]} · ${n} stops · ${complete ? `${st.score || 0} of ${n * 3} suns` : done ? `${done} of ${n} done` : 'not started'}</span>
        <button class="pill${complete ? '' : ' primary'}" data-q="${q.id}">${complete ? 'Walk again' : done ? 'Carry on' : 'Start'}</button></div></li>`;
  };
  openDock('walks', `<article class="dock-page"><h2 id="dock-title">Walks</h2>
    <p class="lede">Five short routes through the city, told as riddles. Find each stop on the map, guess a building’s age
      with the colours off, or pick the right answer. Each stop earns up to three suns; a hint or a wrong guess costs one.</p>
    <p class="walk-score">Your suns: <b>${total}</b> of ${max}</p>
    <ul class="routes">${quests.map(route).join('')}</ul></article>`);
  dockLive.querySelectorAll('[data-q]').forEach(b => b.onclick = () => {
    const q = quests.find(q => q.id === b.dataset.q), st = qStore()[q.id] || {};
    const fresh = !st.step || st.step >= q.steps.length;
    startQuest(q, fresh ? 0 : st.step, fresh ? 0 : st.score || 0, fresh ? [] : st.marks || []);
  });
}
document.querySelector('.walks-open').onclick = () => {
  if (quest) { if (dockView !== 'walk') renderQuest(); return; }
  if (dockView === 'walks') closeDock(); else showWalks();
};

// The search circle: a terracotta ring on the ground around (not centred on) the answer.
const ring = new THREE.Group();
ring.add(new THREE.Mesh(new THREE.RingGeometry(0.97, 1, 128), new THREE.MeshBasicMaterial({ color: ACCENT, depthTest: false, transparent: true, opacity: 0.95 })));
ring.add(new THREE.Mesh(new THREE.CircleGeometry(0.97, 128), new THREE.MeshBasicMaterial({ color: ACCENT, depthTest: false, transparent: true, opacity: 0.06 })));
ring.children.forEach(m => { m.rotation.x = -Math.PI / 2; m.renderOrder = 20; });
ring.visible = false;
scene.add(ring);

let quest = null, step = 0, score = 0, marks = [], hintsShown = 0, tries = 0, solved = false, revealed = false, lastDist = null;
let folded = false, guess = 1900;
const qStep = () => quest.steps[step];
const stepGids = s => s.gids.filter(g => g >= 0);
function centre(gids) {
  const bs = gids.map(building);
  return [bs.reduce((a, b) => a + b.x, 0) / bs.length, bs.reduce((a, b) => a + b.z, 0) / bs.length];
}
// The map's state while a stop asks about one building: no card for it, and its colours hidden for a year riddle.
let quizGid = -1;
function setQuiz(gid, blind) {
  quizGid = gid;
  uniforms.uSelected.value = gid;
  uniforms.uBlind.value = gid < 0 ? 0 : blind ? 1 : 2;
  if (gid >= 0) { pinnedGid = -1; uniforms.uSelected.value = gid; }
}
const cardsLocked = () => quest && !solved && quizGid >= 0;

function startQuest(q, n, sc = 0, mk = []) {
  quest = q; step = n; score = sc; marks = mk;
  document.body.classList.add('walking');
  unpin();
  enterStep(true);
}
function enterStep(first) {
  hintsShown = 0; tries = 0; solved = false; revealed = false; lastDist = null; folded = false; guess = 1900;
  ring.visible = false;
  const s = qStep(), gids = stepGids(s);
  renderQuest();
  if (s.kind === 'find') {
    setQuiz(-1, false);
    if (first) {
      // Open on the whole walk: every stop in view.
      const all = quest.steps.flatMap(stepGids), [x, z] = centre(all);
      const spread = Math.max(...all.map(g => { const b = building(g); return Math.hypot(b.x - x, b.z - z); }));
      aimFly(x, z, Math.min(5200, Math.max(900, spread * 2.2)));
    }
  } else if (gids.length) {
    const b = building(gids[0]);
    setQuiz(gids[0], s.kind === 'year');
    aimFly(b.x, b.z, s.kind === 'year' ? 300 : 380);
  }
}
function closeQuest() {
  document.body.classList.remove('walking');
  quest = null; ring.visible = false; setQuiz(-1, false); unpin();
  if (dockView === 'walk' || dockView === 'building') closeDock();
}
function setModeNamed(name) { setMode(MODE[name]); }
function showRing() {
  const s = qStep(), [x, z] = centre(stepGids(s));
  const r = { 1: 220, 2: 300, 3: 380 }[quest.level] || 300;
  const k = rng(quest.id + step), a = k() * Math.PI * 2, d = r * 0.55 * Math.sqrt(k());
  const cx = x + Math.cos(a) * d, cz = z + Math.sin(a) * d;
  ring.position.set(cx, 2, cz); ring.scale.setScalar(r); ring.visible = true;
  aimFly(cx, cz, r * 5);
}
function photoOf(s) {
  if (s.clue?.thumb) return { src: s.clue.thumb, credit: link(s.clue.page || s.clue.thumb, [s.clue.artist, s.clue.license].filter(Boolean).join(', ') || 'Wikimedia Commons') };
  if (s.photo) {
    const g = stepGids(s)[0], b = g >= 0 && building(g), w = b && b.wk >= 0 ? wiki[b.wk] : null;
    if (w?.image?.thumb) return { src: w.image.thumb, credit: link(w.image.page || w.image.thumb, [w.image.artist, w.image.license].filter(Boolean).join(', ') || 'Wikimedia Commons') };
  }
  return null;
}
// The stops as ticket stubs: stamped with a sun once done.
const stubs = () => `<div class="stubs" aria-label="Stop ${step + 1} of ${quest.steps.length}">${quest.steps.map((_, i) =>
  `<span class="stub ${i < step || (i === step && solved) ? 'done' : i === step ? 'now' : ''}">${i + 1}</span>`).join('')}</div>`;
const worth = () => {
  const s = qStep();
  if (s.kind === 'find') return revealed ? 0 : Math.max(1, 3 - hintsShown);
  if (s.kind === 'choice') return [3, 1, 0][Math.min(tries, 2)];
  return 3;
};
function yearPoints(d) { return d <= 5 ? 3 : d <= 15 ? 2 : d <= 35 ? 1 : 0; }

function renderQuest() {
  if (!quest) return;
  const s = qStep(), ph = photoOf(s), tap = phone.matches ? 'tap' : 'click';
  let body = '';
  if (s.kind === 'find') {
    const hints = Array.from({ length: hintsShown }, (_, i) => i === 0 ? 'Look inside the circle on the map.' : s.hints[i - 1]);
    const more = hintsShown < s.hints.length + 1;
    body = `
      ${ph && !solved ? `<figure class="walk-photo"><img src="${esc(ph.src)}" alt="A photo of the stop to find"></figure><p class="walk-credit">${ph.credit}</p>` : ''}
      <p class="riddle">${esc(s.riddle)}</p>
      ${hints.length ? `<ul class="hints">${hints.map(h => `<li>${esc(h)}</li>`).join('')}</ul>` : ''}
      ${solved ? '' : `<p class="feedback">Find it on the map and ${tap} it.</p>
        <div class="walk-actions">${more ? `<button class="pill w-hint">A hint <small>−1</small></button>` : ''}
          ${s.mode ? `<button class="pill w-lens">${s.mode === 'floors' ? 'Show heights' : 'Show ages'}</button>` : ''}
          <button class="pill w-reveal">Show me</button><span class="worth">Worth ${suns(worth())}</span></div>`}`;
  } else if (s.kind === 'year') {
    body = `
      ${ph ? `<figure class="walk-photo"><img src="${esc(ph.src)}" alt=""></figure><p class="walk-credit">${ph.credit}</p>` : ''}
      <p class="riddle">${esc(s.ask)}</p>
      ${solved ? '' : `<div class="guess"><output>${guess}</output>
        <input type="range" min="1788" max="2026" step="1" value="${guess}" aria-label="Your guess">
        <div class="scale"><span>1788</span><span>1850</span><span>1900</span><span>1950</span><span>2000</span></div></div>
        <div class="walk-actions"><button class="pill primary w-guess">Guess</button><span class="worth">Worth ${suns(3)}</span></div>`}`;
  } else {
    const order = s.options.map((o, i) => i).sort((a, b) => rng(quest.id + step + a)() - rng(quest.id + step + b)());
    body = `
      <p class="riddle">${esc(s.ask)}</p>
      <div class="options">${order.map(i => `<button data-i="${i}" ${solved ? 'disabled' : ''} class="${solved && i === 0 ? 'right' : ''}">${esc(s.options[i])}</button>`).join('')}</div>
      ${solved ? '' : `<div class="walk-actions"><span class="feedback"></span><span class="worth">Worth ${suns(worth())}</span></div>`}`;
  }
  openDock('walk', `<article class="dock-page walk${folded ? ' folded' : ''}">
    <header class="walk-head"><h2 id="dock-title">${esc(quest.title)}</h2><span class="level">${LEVEL[quest.level]}</span></header>
    ${stubs()}${body}${solved ? revealHtml(s) : ''}</article>`);
  wireQuest(s);
}
function revealHtml(s) {
  const got = marks[step] ?? 0, last = step === quest.steps.length - 1, d = Math.abs(guess - s.year);
  const extra = s.kind === 'year' ? `<p>Your guess: <b>${guess}</b>. Built: <b>${s.year}</b>. ${d === 0 ? 'Spot on.' : `${d} ${d === 1 ? 'year' : 'years'} out.`}</p>` : '';
  return `<div class="walk-found">
    <div class="stamp" aria-hidden="true">${suns(got)}</div>
    ${extra}
    <p>${esc(s.reveal)}${s.sources?.length ? ' ' + s.sources.map((u, i) => link(u, s.sources.length > 1 ? `Source ${i + 1}` : 'Source')).join(', ') : ''}</p>
    <p class="earned">${revealed ? 'Shown, not found: no suns this time.' : got === 3 ? 'All three suns.' : ''}</p></div>
    <div class="walk-actions">${last ? `<button class="pill primary w-finish">See how you went</button>`
      : `<button class="pill primary w-next">Next stop</button>`}<button class="pill w-card">Open its card</button></div>`;
}
function wireQuest(s) {
  const el = dockLive, on = (sel, fn) => el.querySelector(sel)?.addEventListener('click', fn);
  const foldOnPhone = () => { if (phone.matches) { folded = true; el.querySelector('.walk')?.classList.add('folded'); } };
  on('.walk-head', () => { folded = !folded; el.querySelector('.walk').classList.toggle('folded', folded); });
  on('.w-hint', () => { hintsShown++; if (hintsShown === 1) showRing(); renderQuest(); if (hintsShown === 1) foldOnPhone(); });
  on('.w-lens', () => { setModeNamed(s.mode); foldOnPhone(); });
  on('.w-reveal', () => {
    const g = stepGids(s)[0]; if (g === undefined) return;
    revealed = true; const b = building(g);
    aimFly(b.x, b.z, 420, () => solve(g));
  });
  const slider = el.querySelector('.guess input');
  if (slider) slider.oninput = () => { guess = +slider.value; el.querySelector('.guess output').textContent = guess; };
  on('.w-guess', () => solve(stepGids(s)[0], yearPoints(Math.abs(guess - s.year))));
  el.querySelectorAll('.options button').forEach(b => b.onclick = () => {
    if (+b.dataset.i === 0) { b.classList.add('right'); solve(stepGids(s)[0]); return; }
    tries++; b.classList.add('wrong'); b.disabled = true;
    el.querySelector('.walk-actions .worth').innerHTML = `Worth ${suns(worth())}`;
    const fb = el.querySelector('.feedback'); fb.textContent = 'Not that one.'; fb.classList.remove('miss'); void fb.offsetWidth; fb.classList.add('miss');
  });
  on('.w-next', () => { step++; qSave(quest.id, { step, score, marks }); enterStep(false); });
  on('.w-finish', finished);
  on('.w-card', () => { const g = stepGids(s)[0], b = building(g); quizGid = -1; uniforms.uBlind.value = 0; aimFly(b.x, b.z, 380, () => openBuilding(g)); });
}
function solve(gid, points) {
  solved = true; folded = false; ring.visible = false;
  const got = points ?? worth();
  marks[step] = got; score += got;
  uniforms.uBlind.value = 0;
  quizGid = -1;
  if (gid >= 0) { pinnedGid = -1; uniforms.uSelected.value = gid; }
  const st = qStore()[quest.id] || {};
  const patch = { step: step + 1, score, marks };
  if (step === quest.steps.length - 1) patch.best = Math.max(st.best || 0, score);
  qSave(quest.id, patch);
  renderQuest();
}
// The result, and a line to share: one group per stop, a filled sun for each one earned.
function finished() {
  const n = quest.steps.length, line = marks.map(m => '●'.repeat(m) + '○'.repeat(3 - m)).join(' ');
  const text = `SydMap · ${quest.title}\n${line}\n${score} of ${n * 3} suns\n${location.origin}${location.pathname}`;
  const verdict = score >= n * 3 - 1 ? 'A true Sydneysider.' : score >= n * 2 ? 'You know your way around.' : score >= n ? 'A good walk.' : 'Time for a walk through town.';
  openDock('walk', `<article class="dock-page walk"><header class="walk-head"><h2 id="dock-title">${esc(quest.title)}</h2></header>
    <div class="walk-result"><p class="total"><b>${score}</b> of ${n * 3} suns</p><p class="verdict">${verdict}</p>
      <p class="line">${marks.map(m => suns(m)).join('')}</p></div>
    <div class="walk-actions"><button class="pill primary w-share">Copy your result</button><button class="pill w-more">More walks</button></div></article>`);
  ring.visible = false; setQuiz(-1, false);
  dockLive.querySelector('.w-more').onclick = () => { closeQuest(); showWalks(); };
  dockLive.querySelector('.w-share').onclick = async e => {
    try { await navigator.clipboard.writeText(text); e.target.textContent = 'Copied'; } catch { e.target.textContent = line; }
  };
}
// Every click on the map while a find stop is open.
function questClick(gid) {
  if (!quest || solved || gid < 0 || qStep().kind !== 'find') return;
  const s = qStep(), targets = stepGids(s);
  if (targets.includes(gid)) { solve(gid); return; }
  const fb = dockLive.querySelector('.feedback');
  if (!fb) return;
  const b = building(gid);
  const d = Math.min(...targets.map(g => { const a = building(g); return Math.hypot(a.x - b.x, a.z - b.z); }));
  let msg = d < 40 ? 'Not this one, but right next to it.' : d < 200 ? 'Not this one. Very warm.'
    : d < 700 ? 'Not this one. A few streets away.' : 'Not this one. Far off.';
  if (lastDist !== null && d >= 40) msg += ' ' + (d < lastDist - 20 ? 'Warmer than before.' : d > lastDist + 20 ? 'Colder than before.' : '');
  lastDist = d;
  fb.textContent = msg.trim();
  fb.className = `feedback ${d < 40 ? 'hot' : d < 200 ? 'warm' : 'cold'}`;
  void fb.offsetWidth; fb.classList.add('miss');
}

// ---------- Lenses: ages, stories, heights, heritage ----------
const totals = periods.map(() => 0);
for (const v of Object.values(config.histogram)) v.forEach((n, i) => totals[i] += n);
let activeLayer = null;
const SECTION_ORDER = ['Country', 'Architecture', 'Faith and community', 'Everyday life', 'The changing city', 'The modern city'];
const groupOn = {};
let maskTarget = periods.map(() => 1);

const ICON = {
  'Country': '<path d="M2 13.5c2.2-1.3 4-1.3 6 0s3.8 1.3 6 0"/><circle cx="8" cy="6.5" r="3.2"/>',
  'Architecture': '<path d="M3 14.5V7l5-4.5L13 7v7.5z"/><path d="M6.5 14.5v-4h3v4"/>',
  'Faith and community': '<path d="M8 1.5v4M6.2 3.3h3.6"/><path d="M4 14.5V8.5L8 5.5l4 3v6z"/><path d="M7 14.5v-3h2v3"/>',
  'Everyday life': '<path d="M4 3h8l-1 11H5z"/><path d="M4.4 7h7.2"/>',
  'The changing city': '<circle cx="8" cy="8" r="6.2"/><path d="M8 4.5V8l2.6 1.6"/>',
  'The modern city': '<rect x="2.5" y="5" width="5" height="9.5"/><rect x="8.5" y="2" width="5" height="12.5"/><path d="M4.5 7.5h1M4.5 10h1M10.5 4.5h1M10.5 7h1M10.5 9.5h1"/>',
};
const sectionIcon = sec => `<svg class="icon" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round">${ICON[sec] || ''}</svg>`;

// The stories, by section, in the dock.
function showStories() {
  const sections = [...new Set(layers.map(L => L.section))].sort((a, b) => SECTION_ORDER.indexOf(a) - SECTION_ORDER.indexOf(b));
  openDock('stories', `<article class="dock-page"><h2 id="dock-title">Stories</h2>
    <p class="lede">Threads of Sydney’s history that live in its buildings. Choose one to light up its buildings and read about them.</p>
    ${sections.map(sec => `<h3 class="st-section">${sectionIcon(sec)}${esc(sec)}</h3><ul class="st-list">${layers.filter(L => L.section === sec).map(L =>
      `<li><button class="st-row" data-id="${L.id}"><b>${esc(L.title)}</b><span class="n">${fmt(L.count)}</span><span class="era">${esc(L.era)}</span></button></li>`).join('')}</ul>`).join('')}
    <p class="add-story"><a href="${REPO}/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener">Add a story on GitHub</a></p></article>`);
  dockLive.querySelectorAll('.st-row').forEach(b => b.onclick = () => { setLayer(layers.find(l => l.id === b.dataset.id)); showStory(activeLayer); });
}
// One story: what it is, its places and their stories, and where it comes from.
function showStory(L) {
  const seenName = new Set();
  const named = Object.entries(L.notes || {}).filter(([, n]) => n.name && n.at && !seenName.has(n.name) && seenName.add(n.name));
  openDock('story', `<article class="dock-page">
    <div class="story-head">${sectionIcon(L.section)}<h2 id="dock-title">${esc(L.title)}</h2></div>
    <p class="story-era">${esc(L.era)} · <span class="n">${fmt(L.count)}</span> buildings</p>
    <p class="story-text">${esc(L.text)}</p>
    ${named.length ? `<h3>Places and their stories</h3><ul class="places">${named.map(([gid, n]) => `
      <li><button class="place" data-gid="${gid}"><b>${esc(n.name)}</b><span>${esc(n.story || '')}</span></button></li>`).join('')}</ul>` : ''}
    ${L.caveat ? `<p class="caveat">${esc(L.caveat)}</p>` : ''}
    <p class="src">${link(L.source.url, L.source.label)}</p></article>`,
  { label: 'All stories', go: () => { setLayer(null); showStories(); } });
  dockLive.querySelectorAll('.place').forEach(b => b.onclick = () => {
    const n = L.notes[b.dataset.gid], back = { label: L.title, go: () => { unpin(); showStory(L); } };
    aimFly(n.at[0], n.at[1], 520, () => openBuilding(+b.dataset.gid, back));
  });
}
function setLayer(L) {
  if (L) uniforms.uLayerAt.value = performance.now() / 1000;
  activeLayer = L;
  const bits = Array(MAX_GROUPS).fill(-1);
  if (L) L.groups.forEach((g, i) => { if (i < MAX_GROUPS && groupOn[g.bit] !== false) bits[i] = g.bit; });
  uniforms.uGroupBit.value = bits;
  renderKey(); drawHist();
}

// ---------- The Suburbs lens ----------
// Each suburb painted by one measure in the year on the line (pipeline/s10_suburbs.py): its people, how closely they
// live, their income and schooling, recorded crime and what homes sell for. The buildings and the ground take the
// suburb's colour; a click opens the suburb, with every measure over the years.
const SUBS = subOk ? subData.suburbs : [];
const MEASURES = subOk ? subData.measures : [];
let measure = MEASURES[0] || null;
const firstYear = m => m.years[0], lastYear = m => m.years[m.years.length - 1];
// A measure in a year: that year's figure; for a census, between two censuses, a straight line between them; after the
// last figure, the last. Before the first, none.
function subAt(m, s, Y) {
  const vs = m.values[s];
  if (!vs) return null;
  let lo = -1, hi = -1;
  vs.forEach((v, k) => { if (v === null) return; if (m.years[k] <= Y) lo = k; else if (hi < 0) hi = k; });
  if (lo < 0) return null;
  const y0 = m.years[lo];
  if (y0 === Y || hi < 0 || !m.interp) return { v: vs[lo], y: y0 };
  const y1 = m.years[hi], f = (Y - y0) / (y1 - y0);
  return { v: vs[lo] + (vs[hi] - vs[lo]) * f, y: Y, between: [y0, y1] };
}
const subT = (m, v) => Math.max(0, Math.min(1, m.log ? Math.log(v / m.domain[0]) / Math.log(m.domain[1] / m.domain[0])
  : (v - m.domain[0]) / (m.domain[1] - m.domain[0])));
const subInv = (m, t) => m.log ? m.domain[0] * (m.domain[1] / m.domain[0]) ** t : m.domain[0] + t * (m.domain[1] - m.domain[0]);
const subColor = t => { const n = SUB_RAMP.length - 1, k = Math.min(n - 1, Math.floor(t * n)); return '#' + col(SUB_RAMP[k]).lerp(col(SUB_RAMP[k + 1]), t * n - k).getHexString(); };
// A value as people read it: dollars in thousands or millions, shares in per cent, the rest with the measure's decimals.
function fmtM(m, v, short = false) {
  if (m.money) return v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e7 || short ? 1 : 2)}m` : v >= 1e3 && short ? `$${(v / 1e3).toFixed(v >= 1e4 ? 0 : 1)}k` : `$${fmt(Math.round(v))}`;
  const d = short && v >= 100 ? 0 : m.decimals;
  return `${short && v >= 1e4 ? `${(v / 1e3).toFixed(v >= 1e5 ? 0 : 1)}k` : v.toLocaleString('en-AU', { minimumFractionDigits: d, maximumFractionDigits: d })}${m.pct ? '%' : ''}`;
}
const subYear = () => Math.min(config.yearMax, Math.round(uniforms.uYear.value));
// Which year a figure is, in words: "2021", "2019, between the 2016 and 2021 censuses", "none before 2001".
function yearWords(m, Y = subYear()) {
  if (Y < firstYear(m)) return `none before ${firstYear(m)}`;
  if (Y >= lastYear(m)) return `${lastYear(m)}${Y > lastYear(m) ? ', the latest' : ''}`;
  if (!m.interp || m.years.includes(Y)) return `${Y}`;
  const a = m.years.filter(y => y < Y).pop(), b = m.years.find(y => y > Y);
  return `${Y}, read between the ${a} and ${b} ${m.census ? 'censuses' : 'figures'}`;
}
function fillSubs() {
  const d = subValTex.image.data, Y = subYear();
  d.fill(-1);
  if (measure) SUBS.forEach((_, s) => { const a = subAt(measure, s, Y); if (a) d[s] = subT(measure, a.v); });
  subValTex.needsUpdate = true;
}
const subOfGid = gid => subOk && gid >= 0 && subOf[gid] !== 255 ? subOf[gid] : -1;

// All suburbs, ranked by the measure in the year.
function showSuburbs() {
  const m = measure, Y = subYear();
  const rows = SUBS.map((S, s) => ({ S, s, a: subAt(m, s, Y) })).sort((p, q) => (q.a?.v ?? -Infinity) - (p.a?.v ?? -Infinity));
  openDock('suburbs', `<article class="dock-page"><h2 id="dock-title">Suburbs</h2>
    <p class="lede">${esc(m.what)}</p>
    <p class="sub-measures">${MEASURES.map(x => `<button class="pill" data-m="${x.key}" aria-pressed="${x === m}">${esc(x.short)}</button>`).join('')}</p>
    <p class="sub-year"><b>${esc(m.label)}</b>, ${esc(yearWords(m, Y))}</p>
    <ol class="sub-rank">${rows.map(({ S, s, a }) => `<li><button class="sub-row" data-s="${s}"><b>${esc(S.name)}</b>
      <span class="n">${a ? fmtM(m, a.v) : 'no figure'}</span>
      <i class="bar"><i style="width:${a ? (4 + 96 * subT(m, a.v)).toFixed(1) : 0}%;background:${a ? subColor(subT(m, a.v)) : 'none'}"></i></i></button></li>`).join('')}</ol>
    ${m.note ? `<p class="caveat">${esc(m.note)}</p>` : ''}
    <p class="src">${link(m.source.url, m.source.label)}</p></article>`);
  dockLive.querySelectorAll('.sub-measures [data-m]').forEach(b => b.onclick = () => setMeasure(MEASURES.find(x => x.key === b.dataset.m)));
  dockLive.querySelectorAll('.sub-row').forEach(b => b.onclick = () => {
    const s = +b.dataset.s;
    flySuburb(s, () => showSuburb(s, -1, { label: 'All suburbs', go: showSuburbs }));
  });
}
function flySuburb(s, done) {
  const S = SUBS[s];
  aimFly(S.x, S.z, Math.max(900, Math.min(4000, Math.sqrt(S.km2) * 1700)), done);
}
// A measure's line over the years for one suburb: a dot for each figure, the year on the line marked.
function spark(m, s, Y) {
  const pts = m.years.map((y, k) => [y, m.values[s][k]]).filter(([, v]) => v !== null);
  if (!pts.length) return '<p class="caveat">No figures for this suburb.</p>';
  const W = 312, H = 64, x0 = firstYear(m), x1 = Math.max(lastYear(m), x0 + 1);
  const vs = pts.map(p => p[1]), lo = Math.min(...vs), hi = Math.max(...vs), pad = (hi - lo) * 0.12 || Math.abs(hi) * 0.1 || 1;
  const X = y => 6 + (y - x0) / (x1 - x0) * (W - 12), Yp = v => H - 14 - (v - lo + pad) / (hi - lo + 2 * pad) * (H - 22);
  const path = pts.map(([y, v], k) => `${k ? 'L' : 'M'}${X(y).toFixed(1)},${Yp(v).toFixed(1)}`).join('');
  const at = Math.max(x0, Math.min(x1, Y));
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(m.label)}: ${pts.map(([y, v]) => `${y} ${fmtM(m, v)}`).join(', ')}">
    ${Y >= x0 ? `<line class="now" x1="${X(at)}" x2="${X(at)}" y1="4" y2="${H - 12}"/>` : ''}
    <path d="${path}"/>
    ${pts.map(([y, v]) => `<circle cx="${X(y).toFixed(1)}" cy="${Yp(v).toFixed(1)}" r="${pts.length > 12 ? 2 : 3.2}" style="fill:${subColor(subT(m, v))}"><title>${y}: ${fmtM(m, v)}</title></circle>`).join('')}
    <text x="6" y="${H - 1}">${x0}</text><text x="${W - 6}" y="${H - 1}" text-anchor="end">${lastYear(m)}</text></svg>`;
}
// One suburb: every measure, its figure in the year and its line over the years.
let subOpen = null;
function showSuburb(s, gid = -1, back = null) {
  const S = SUBS[s], Y = subYear();
  subOpen = { s, gid, back };
  const rank = m => { const a = subAt(m, s, Y); if (!a) return ''; const n = SUBS.filter((_, t) => (subAt(m, t, Y)?.v ?? -Infinity) > a.v).length;
    const all = SUBS.filter((_, t) => subAt(m, t, Y)).length; return `${n + 1} of ${all} suburbs`; };
  openDock('suburb', `<article class="dock-page sub-card"><h2 id="dock-title">${esc(S.name)}</h2>
    <p class="story-era">${S.postcode ? `${S.postcode} · ` : ''}${S.km2.toFixed(2)} km² · <span class="n">${fmt(S.buildings)}</span> buildings on the map</p>
    ${gid >= 0 ? `<p><button class="pill sub-bld">The building you chose</button></p>` : ''}
    ${MEASURES.map(m => { const a = subAt(m, s, Y);
      return `<section class="sub-m${m === measure ? ' on' : ''}"><h3><button class="sub-pick" data-m="${m.key}" aria-pressed="${m === measure}">${esc(m.label)}</button></h3>
        <p class="sub-val">${a ? `<span class="v">${fmtM(m, a.v)}</span> ${esc(m.unit)}` : '<span class="none">No figure</span>'}<small>${esc(yearWords(m, Y))}${a ? ` · ${rank(m)}` : ''}</small></p>
        ${spark(m, s, Y)}<p class="src-note">${link(m.source.url, m.source.label)}</p></section>`; }).join('')}
    <p class="caveat">The figures are for the whole suburb, even where the map shows only part of it.</p></article>`, back);
  dockLive.querySelector('.sub-bld')?.addEventListener('click', () => openBuilding(gid, { label: S.name, go: () => { unpin(); showSuburb(s, gid, back); } }));
  dockLive.querySelectorAll('.sub-pick').forEach(b => b.onclick = () => setMeasure(MEASURES.find(m => m.key === b.dataset.m)));
}
function setMeasure(m) {
  measure = m;
  if (subYear() < firstYear(m)) uniforms.uYear.value = config.yearMax;
  renderKey(); drawHist();
}
// The dock follows the year, without losing its place.
let subShownYear = null;
function syncSubs() {
  fillSubs();
  const key = `${subYear()} ${measure?.key}`;
  if (key === subShownYear) return;
  subShownYear = key;
  renderKey();
  const top = dock.scrollTop;
  if (dockView === 'suburbs') showSuburbs();
  else if (dockView === 'suburb' && subOpen) showSuburb(subOpen.s, subOpen.gid, subOpen.back);
  else return;
  dock.scrollTop = top;
}

// The key beside the year: what the colours mean for the lens in hand.
const keyEl = document.getElementById('key');
const RAMP = ['#e3ecec', '#93b7bd', '#5d878d', '#345a60', '#13282b'];
function renderKey() {
  const mode = uniforms.uMode.value;
  if (mode === MODE.period) {
    const on = maskTarget.map((v, i) => v ? i : -1).filter(i => i >= 0);
    const solo = on.length === 1 ? periods[on[0]] : null;
    keyEl.innerHTML = (solo ? `<button class="chip k-all">${dot(solo.color)}Only ${esc(ageParts(solo).name.replace(/^The /, 'the '))} <span class="n">${fmt(totals[on[0]])}</span>${CLOSE}</button>`
      : `<span class="key-label">Each station on the line is an age: choose one to see its buildings</span>`) +
      `<button class="chip k-est" aria-pressed="${!uniforms.uDocOnly.value}" title="Estimated years are paler; switch them off to see the documented and strata years alone">${dot('#d9b2a8')}Estimated years</button>`;
    keyEl.querySelector('.k-all')?.addEventListener('click', () => { maskTarget = periods.map(() => 1); updateRail(); renderKey(); drawHist(); });
    keyEl.querySelector('.k-est').onclick = () => { uniforms.uDocOnly.value = uniforms.uDocOnly.value ? 0 : 1; renderKey(); };
  } else if (mode === MODE.floors) {
    const stops = ['1', '3', '8', '20', '40+'];
    keyEl.innerHTML = `<span class="key-label">Storeys</span><span class="ramp">${stops.map((s, i) =>
      `<div><span>${s}</span><i style="background:linear-gradient(90deg,${RAMP[i]},${RAMP[Math.min(i + 1, 4)]})"></i></div>`).join('')}</span>`;
  } else if (mode === MODE.heritage) {
    const h = config.heritage;
    keyEl.innerHTML = h.labels.map((l, i) => `<span class="chip plain">${dot(h.colors[i + 1])}${esc(l)} <span class="n">${fmt(h.counts[i + 1])}</span></span>`).join('');
  } else if (mode === MODE.suburbs) {
    const m = measure;
    if (!m) { keyEl.innerHTML = `<span class="key-label">No suburb figures on this map</span>`; return; }
    const ticks = SUB_RAMP.map((_, i) => fmtM(m, subInv(m, i / (SUB_RAMP.length - 1)), true));
    keyEl.innerHTML = MEASURES.map(x => `<button class="chip" data-m="${x.key}" aria-pressed="${x === m}">${esc(x.short)}</button>`).join('') +
      `<span class="key-label">${esc(m.label)}, ${esc(yearWords(m))}</span><span class="ramp">${SUB_RAMP.map((c, i) =>
        `<div><span>${ticks[i]}${i === SUB_RAMP.length - 1 && m.domainCut ? '+' : ''}</span><i style="background:linear-gradient(90deg,${c},${SUB_RAMP[Math.min(i + 1, SUB_RAMP.length - 1)]})"></i></div>`).join('')}</span>`;
    keyEl.querySelectorAll('[data-m]').forEach(b => b.onclick = () => setMeasure(MEASURES.find(x => x.key === b.dataset.m)));
  } else if (!activeLayer) {
    keyEl.innerHTML = `<span class="key-label">Choose a story to light up its buildings</span>`;
  } else if (activeLayer.groups.length > 1) {
    keyEl.innerHTML = activeLayer.groups.map((g, i) => `<button class="chip" data-bit="${g.bit}" aria-pressed="${groupOn[g.bit] !== false}">${dot(GROUP_COLORS[i])}${esc(g.label)} <span class="n">${fmt(g.count)}</span></button>`).join('');
    keyEl.querySelectorAll('[data-bit]').forEach(b => b.onclick = () => { groupOn[b.dataset.bit] = groupOn[b.dataset.bit] === false; setLayer(activeLayer); });
  } else {
    keyEl.innerHTML = `<span class="chip plain">${dot(GROUP_COLORS[0])}${esc(activeLayer.title)} <span class="n">${fmt(activeLayer.count)}</span></span>`;
  }
}

function setMode(m) {
  uniforms.uMode.value = m;
  hoverGid = -1;
  document.querySelectorAll('.lenses button').forEach(x => x.setAttribute('aria-pressed', String(+x.dataset.mode === m)));
  const bits = Array(MAX_GROUPS).fill(-1);
  if (activeLayer) activeLayer.groups.forEach((g, i) => { if (groupOn[g.bit] !== false) bits[i] = g.bit; });
  uniforms.uGroupBit.value = bits;
  subGround.visible = m === MODE.suburbs;
  land.visible = !subGround.visible || !subGround.children.length;  // the suburbs' land takes its place
  if (m === MODE.layers) {
    if (activeLayer) uniforms.uLayerAt.value = performance.now() / 1000;
    if (!quest) activeLayer ? showStory(activeLayer) : showStories();
  } else if (dockView === 'stories' || dockView === 'story') closeDock();
  if (m === MODE.suburbs && measure) {
    if (subYear() < firstYear(measure)) { stopPlay(); uniforms.uYear.value = config.yearMax; }
    if (!quest) { if (dockView === 'building') unpin(); showSuburbs(); }
  } else if (dockView === 'suburbs' || dockView === 'suburb') closeDock();
  renderKey(); updateRail(); drawHist();
}
document.querySelectorAll('.lenses button').forEach(b => b.onclick = () => setMode(+b.dataset.mode));
document.querySelector(`.lenses [data-mode="${MODE.suburbs}"]`).hidden = !measure;

// ---------- The line through time ----------
// The buildings of each year as bars, then the rail of ages: a coloured stretch per age with a station at its start.
// A station shows its age alone (on Ages) or takes the city to that age's last year (on the other lenses).
const hist = document.getElementById('hist');
const hctx = hist.getContext('2d');
const track = hist.parentElement;
const rail = document.getElementById('rail');
const yearSun = track.querySelector('.year-sun'), yearRing = track.querySelector('.year-ring'), fromMark = track.querySelector('.from-mark');
const T0 = Math.floor(config.yearMin / 25) * 25, T1 = config.yearMax + 1;
const years = Object.entries(config.histogram).map(([y, v]) => [+y, v]);
const yMax = Math.max(...years.map(([, v]) => v.reduce((a, b) => a + b, 0)));
const xOf = y => (y - T0) / (T1 - T0) * hist.clientWidth;
const yearOf = x => Math.round(T0 + x / hist.clientWidth * (T1 - T0));
const pct = y => `${((y - T0) / (T1 - T0) * 100).toFixed(3)}%`;
const NEUTRAL = '#a9a59c';
rail.innerHTML = periods.map((p, i) => {
  const { dates, name } = ageParts(p), end = i < periods.length - 1 ? periods[i + 1].from : T1;
  return `<i style="left:${pct(p.from)};width:calc(${pct(end)} - ${pct(p.from)})"></i>
    <button class="station" data-i="${i}" style="left:${pct(p.from)}" aria-label="${esc(dates)} ${esc(name)}: ${fmt(totals[i])} buildings" title="${esc(name)}"><span>${p.from}</span></button>`;
}).join('');
const segs = [...rail.querySelectorAll('i')], stations = [...rail.querySelectorAll('.station')];
stations.forEach(b => b.onclick = () => {
  const i = +b.dataset.i;
  if (uniforms.uMode.value === MODE.period) {
    const solo = maskTarget.every((v, j) => (j === i) === !!v);
    maskTarget = periods.map((_, j) => (solo || j === i) ? 1 : 0);
    renderKey();
  } else {
    stopPlay();
    uniforms.uYear.value = Math.min(config.yearMax, i < periods.length - 1 ? periods[i + 1].from - 1 : config.yearMax);
  }
  updateRail(); drawHist();
});
function updateRail() {
  const Y = uniforms.uYear.value, ages = uniforms.uMode.value === MODE.period, now = periods.indexOf(periodOf(Math.round(Y)));
  periods.forEach((p, i) => {
    const end = i < periods.length - 1 ? periods[i + 1].from : T1, f = Math.max(0, Math.min(1, (Y - p.from + 1) / (end - p.from)));
    const c = ages ? p.color : NEUTRAL, off = ages && !maskTarget[i];
    segs[i].style.background = `linear-gradient(90deg, ${c} ${(f * 100).toFixed(1)}%, ${c}38 ${(f * 100).toFixed(1)}%)`;
    segs[i].style.opacity = off ? 0.25 : 1;
    const s = stations[i];
    s.style.setProperty('--c', c);
    s.classList.toggle('past', p.from <= Y);
    s.classList.toggle('now', i === now && Y < config.yearMax);
    s.classList.toggle('off', off);
    s.setAttribute('aria-pressed', ages ? String(!!maskTarget[i] && maskTarget.filter(Boolean).length === 1) : 'false');
  });
  const x = Math.max(0, Math.min(hist.clientWidth, xOf(Y)));
  yearSun.style.left = yearRing.style.left = `${x}px`;
  const Yf = uniforms.uYearFrom.value;
  fromMark.hidden = Yf < config.yearMin;
  if (Yf >= config.yearMin) fromMark.style.left = `${xOf(Yf)}px`;
}

function layerGroupsShown() {
  if (uniforms.uMode.value !== MODE.layers || !activeLayer) return [];
  return activeLayer.groups.map((g, i) => ({ ...g, color: GROUP_COLORS[i] })).filter(g => groupOn[g.bit] !== false);
}
function visibleCount() {
  const Y = uniforms.uYear.value;
  const shown = layerGroupsShown();
  if (shown.length) return shown.reduce((n, g) => n + Object.entries(g.years).reduce((m, [y, c]) => m + (+y <= Y ? c : 0), 0), 0);
  let n = 0;
  for (const [y, v] of years) if (y <= Y) v.forEach((c, i) => { if (uniforms.uMode.value !== MODE.period || maskTarget[i]) n += c; });
  return n;
}

// The year on paper flaps: a digit turns over when it changes.
const flaps = [...document.querySelectorAll('.flap')];
const eraEl = document.getElementById('era'), yearEl = document.getElementById('year'), countEl = document.getElementById('count');
function showYear(Y) {
  const y = Math.min(config.yearMax, Math.round(Y)), digits = String(y).padStart(4, ' ');
  flaps.forEach((f, i) => {
    if (f.textContent === digits[i]) return;
    f.textContent = digits[i];
    if (!reduceMotion.matches) { f.classList.remove('turn'); void f.offsetWidth; f.classList.add('turn'); }
  });
  eraEl.textContent = ageParts(periodOf(y)).name;
  yearEl.textContent = Y >= config.yearMax ? 'Today, ' : `${y}, `;
  const n = visibleCount();
  countEl.textContent = `${fmt(n)} ${n === 1 ? 'building' : 'buildings'} standing`;
  hist.setAttribute('aria-valuenow', String(y));
  hist.setAttribute('aria-valuetext', `${Y >= config.yearMax ? 'Today' : y}: ${countEl.textContent}`);
}

function drawHist() {
  const w = hist.clientWidth, h = hist.clientHeight, dpr = devicePixelRatio;
  if (!w) return;
  hist.width = w * dpr; hist.height = h * dpr;
  hctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  hctx.clearRect(0, 0, w, h);
  const plotH = phone.matches ? 36 : 56, bw = Math.max(1, w / (T1 - T0));
  const Y = uniforms.uYear.value, Yf = uniforms.uYearFrom.value, ages = uniforms.uMode.value === MODE.period;
  const shown = layerGroupsShown();
  const bar = (y, bh, top, color, on) => {
    hctx.fillStyle = color;
    hctx.globalAlpha = on ? (y <= Yf ? 0.3 : 1) : 0.16;
    hctx.fillRect(xOf(y), top - bh, bw, bh);
  };
  if (shown.length) {
    // A story: the city in grey behind, the story's own buildings in its colours.
    for (const [y, v] of years) bar(y, Math.sqrt(v.reduce((a, b) => a + b, 0) / yMax) * (plotH - 4), plotH, '#d6d1c8', false);
    const total = {};
    for (const g of shown) for (const [y, c] of Object.entries(g.years)) total[y] = (total[y] || 0) + c;
    const lMax = Math.max(1, ...Object.values(total)), stack = {};
    for (const g of shown) for (const [ys, c] of Object.entries(g.years)) {
      const y = +ys, full = Math.sqrt(total[ys] / lMax) * (plotH - 4) * 0.9, bh = full * c / total[ys];
      bar(y, bh, plotH - (stack[y] || 0), g.color, y <= Y);
      stack[y] = (stack[y] || 0) + bh;
    }
  } else {
    for (const [y, v] of years) {
      let top = plotH;
      v.forEach((c, i) => {
        if (!c) return;
        const bh = Math.sqrt(c / yMax) * (plotH - 4);
        const alone = ages && maskTarget.filter(Boolean).length === 1 && maskTarget[i];
        bar(y, bh, top, alone ? periods[i].color : '#c9c4ba', !(ages && !maskTarget[i]) && y <= Y);
        top -= bh;
      });
    }
  }
  hctx.globalAlpha = 1;
  if (Yf >= config.yearMin) { hctx.fillStyle = MUTED; hctx.fillRect(xOf(Yf) - 0.5, 0, 1, plotH); }
  hctx.fillStyle = INK;
  hctx.fillRect(xOf(Y) - 0.75, 0, 1.5, plotH + (phone.matches ? 4 : 6));
  updateRail();
  showYear(Y);
  if (uniforms.uMode.value === MODE.suburbs) syncSubs();
}

let handle = null;
hist.addEventListener('pointerdown', e => {
  hist.setPointerCapture(e.pointerId);
  const x = e.offsetX;
  handle = Math.abs(x - xOf(uniforms.uYearFrom.value)) < Math.abs(x - xOf(uniforms.uYear.value)) ? 'uYearFrom' : 'uYear';
  moveHandle(x);
  stopPlay();
});
hist.addEventListener('pointermove', e => handle && moveHandle(e.offsetX));
hist.addEventListener('pointerup', () => handle = null);
function moveHandle(x) {
  const y = Math.max(T0, Math.min(config.yearMax, yearOf(x)));
  if (handle === 'uYear') uniforms.uYear.value = Math.max(y, uniforms.uYearFrom.value + 1);
  else uniforms.uYearFrom.value = Math.min(y, uniforms.uYear.value - 1);
  drawHist();
}
// The line is a slider for the keyboard too: arrows move a year, Shift with them ten, Home and End go to the ends.
hist.tabIndex = 0;
hist.setAttribute('role', 'slider');
hist.setAttribute('aria-valuemin', String(T0));
hist.setAttribute('aria-valuemax', String(config.yearMax));
hist.addEventListener('keydown', e => {
  const step = e.shiftKey ? 10 : 1, Y = Math.round(uniforms.uYear.value);
  const to = { ArrowLeft: Y - step, ArrowDown: Y - step, ArrowRight: Y + step, ArrowUp: Y + step, Home: T0, End: config.yearMax }[e.key];
  if (to === undefined) return;
  e.preventDefault(); stopPlay();
  uniforms.uYear.value = Math.max(uniforms.uYearFrom.value + 1, Math.min(config.yearMax, to));
  drawHist();
});

// Play: quickly through the convict town's sparse decades, then slowly through the dense ones.
let playing = false, playT0 = 0, playStart = 0;
const playBtn = document.getElementById('play');
const playIcon = document.getElementById('play-icon');
const DURATION = (+new URLSearchParams(location.search).get('film') || 30) * 1000; // ?film=6 for a short film
const PIVOT = 1860, PIVOT_SHARE = 0.2; // share of the film spent before PIVOT
function playYear(t) {
  return t < PIVOT_SHARE ? T0 + (PIVOT - T0) * (t / PIVOT_SHARE) : PIVOT + (config.yearMax - PIVOT) * ((t - PIVOT_SHARE) / (1 - PIVOT_SHARE));
}
function startPlay() {
  playing = true; playStart = performance.now();
  if (uniforms.uYear.value >= config.yearMax) uniforms.uYear.value = T0;
  playT0 = 0;
  while (playT0 < 1 && playYear(playT0) < uniforms.uYear.value) playT0 += 0.001;
  playIcon.setAttribute('d', 'M4 2.5h3v11H4zM9 2.5h3v11H9z');
  uniforms.uPlaying.value = 1;
  playBtn.setAttribute('aria-label', 'Pause');
}
function stopPlay() {
  if (!playing) return;
  playing = false;
  uniforms.uPlaying.value = 0;
  uniforms.uRise.value = 0.01;
  uniforms.uYear.value = Math.round(uniforms.uYear.value);
  playIcon.setAttribute('d', 'M4.5 2.5v11l9-5.5z');
  playBtn.setAttribute('aria-label', "Play the city's growth");
}
playBtn.onclick = () => playing ? stopPlay() : startPlay();

// ---------- Notes ----------
document.querySelector('.notes-open').onclick = () => { if (dockView === 'notes') closeDock(); else { if (dockView === 'building') unpin(); openDock('notes'); } };
{
  const f = config.stats.flags, set = (k, v) => notesEl.querySelectorAll(`[data-stat="${k}"]`).forEach(el => { el.textContent = fmt(v); });
  set('buildings', config.stats.buildings);
  set('documented', (f[0] || 0) + (f[1] || 0));
  set('strata', f[2] || 0);
  set('heritage', f[3] || 0);
  set('neighbours', f[4] || 0);
}

// ---------- Loop ----------
function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  drawHist();
}
addEventListener('resize', resize);
renderKey();
resize();
document.fonts?.ready.then(drawHist);

let frame = 0;
renderer.setAnimationLoop(now => {
  frame++;
  stepFlight(now);
  uniforms.uNow.value = now / 1000;
  uniforms.uMask.value = maskTarget;
  controls.update();
  const dist = camera.position.distanceTo(controls.target);
  uniforms.uFog.value.set(dist * 1.6, dist * 4);
  if (frame % 6 === 0) updateLabels(dist);
  if (playing) {
    const t = Math.min(1, playT0 + (now - playStart) / DURATION);
    uniforms.uYear.value = playYear(t);
    // A flight lasts about 0.8 s on screen whatever the film's pace: as many years as the film covers in that time.
    uniforms.uRise.value = Math.max(2, (playYear(Math.min(1, t + 800 / DURATION)) - playYear(t)));
    if (t >= 1) stopPlay();
    drawHist();
  }
  if (pointer && !dragging && frame % 3 === 0) {
    const gid = pick(pointer[0], pointer[1]);
    uniforms.uHover.value = gid;
    showTip(gid, pointer[0], pointer[1]);
  }
  renderer.render(scene, camera);
});

window.__dbg = { setMeasure, showSuburb, get measures() { return MEASURES; }, pick, uniforms, camera, controls, setLayer, setMode, layers, pinCard, openBuilding, showStory, showWalks, building, labelGroup, labels, flyTo, startPlay, questClick, startQuest, goHome, drawHist, get quests() { return quests; } };
