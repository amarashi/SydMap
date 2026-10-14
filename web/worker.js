// Turns one binary tile into a mesh: extruded parts, then any ready-made meshes (pipeline/s03_tiles.py has the
// layout). Positions stay in decimetres from the tile origin.
import { ShapeUtils, Vector2 } from './vendor/three.core.js';

function parse(buf) {
  const h = new DataView(buf);
  const nB = h.getUint32(4, true), nP = h.getUint32(8, true), nR = h.getUint32(12, true), nV = h.getUint32(16, true);
  const nMV = h.getUint32(20, true), nMT = h.getUint32(24, true);
  const origin = [h.getFloat32(28, true), h.getFloat32(32, true)];
  let o = 36;
  const take = (Type, n) => { const a = new Type(buf, o, n); o += Math.ceil(n * Type.BYTES_PER_ELEMENT / 4) * 4; return a; };
  return {
    nB, origin,
    gid: take(Uint32Array, nB), year: take(Int16Array, nB), flag: take(Uint8Array, nB),
    period: take(Uint8Array, nB), floors: take(Uint8Array, nB), heritage: take(Uint8Array, nB),
    lay0: take(Uint32Array, nB), lay1: take(Uint32Array, nB), partStart: take(Uint32Array, nB + 1),
    height: take(Float32Array, nP), base: take(Float32Array, nP), ringStart: take(Uint32Array, nP + 1),
    vertStart: take(Uint32Array, nR + 1), hole: take(Uint8Array, nR), xz: take(Int16Array, 2 * nV),
    meshBld: take(Uint16Array, nMV), meshPos: take(Int16Array, 3 * nMV), meshTri: take(Uint16Array, 3 * nMT),
  };
}

function build(t) {
  let nVert = 0, nIdx = 0;
  for (let p = 0; p < t.height.length; p++) {
    const lifted = t.base[p] > 0;
    for (let r = t.ringStart[p]; r < t.ringStart[p + 1]; r++) {
      const n = t.vertStart[r + 1] - t.vertStart[r];
      nVert += n * (lifted ? 6 : 5); nIdx += n * 6 + n * (lifted ? 6 : 3);
    }
  }
  nVert += t.meshBld.length; nIdx += t.meshTri.length;
  const pos = new Int16Array(nVert * 3), bld = new Uint16Array(nVert), idx = new Uint32Array(nIdx);
  let v = 0, k = 0;
  for (let b = 0; b < t.nB; b++) {
    for (let p = t.partStart[b]; p < t.partStart[b + 1]; p++) {
      const top = Math.round(t.height[p] * 10), bottom = Math.round(t.base[p] * 10);
      const r0 = t.ringStart[p], r1 = t.ringStart[p + 1];
      const contour = [], holes = [];
      // Walls, from the part's base (a bridge between towers starts above the ground) to its top.
      for (let r = r0; r < r1; r++) {
        const s = t.vertStart[r], e = t.vertStart[r + 1], n = e - s;
        const ring = [];
        for (let i = 0; i < n; i++) {
          const a = s + i, c = s + ((i + 1) % n);
          const ax = t.xz[2 * a], az = t.xz[2 * a + 1], cx = t.xz[2 * c], cz = t.xz[2 * c + 1];
          pos.set([ax, bottom, az, cx, bottom, cz, cx, top, cz, ax, top, az], v * 3);
          bld.fill(b, v, v + 4);
          idx.set([v, v + 1, v + 2, v, v + 2, v + 3], k);
          v += 4; k += 6;
          ring.push(new Vector2(ax, az));
        }
        if (!t.hole[r] && !contour.length) contour.push(...ring);
        else holes.push(ring);
      }
      if (!contour.length) continue;
      // Roof, and a floor under a part that floats.
      const all = contour.concat(...holes);
      const tris = ShapeUtils.triangulateShape(contour, holes);
      for (const y of bottom > 0 ? [top, bottom] : [top]) {
        const start = v;
        for (const pt of all) { pos.set([pt.x, y, pt.y], v * 3); bld[v] = b; v++; }
        for (const tri of tris) { idx.set([start + tri[0], start + tri[1], start + tri[2]], k); k += 3; }
      }
    }
  }
  // Meshes, as they come (the top bit of a building index marks a pale surface, see the shader).
  pos.set(t.meshPos, v * 3);
  bld.set(t.meshBld, v);
  for (let i = 0; i < t.meshTri.length; i++) idx[k + i] = v + t.meshTri[i];
  v += t.meshBld.length; k += t.meshTri.length;
  // Per-building lookup, two texels: [year, period + 16*flag, floors + 128*heritage, global id], [layer bits in four 16-bit words].
  const attr = new Float32Array(t.nB * 8);
  for (let b = 0; b < t.nB; b++) {
    attr.set([t.year[b], t.period[b] + 16 * t.flag[b], Math.min(t.floors[b], 127) + 128 * t.heritage[b], t.gid[b],
      t.lay0[b] & 0xffff, t.lay0[b] >>> 16, t.lay1[b] & 0xffff, t.lay1[b] >>> 16], b * 8);
  }
  return { pos: pos.subarray(0, v * 3), bld: bld.subarray(0, v), idx: idx.subarray(0, k), attr, origin: t.origin, nB: t.nB };
}

self.onmessage = ({ data: { buf, id } }) => {
  const m = build(parse(buf));
  self.postMessage({ id, ...m }, [m.pos.buffer, m.bld.buffer, m.idx.buffer, m.attr.buffer]);
};
