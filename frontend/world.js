/* New Haven's dependency-free living diorama. Geometry is decorative; all
 * residents, workplaces, conditions and weather come from the simulation. */
(() => {
  "use strict";
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const hash = (x, y, n = 0) => {
    const v = Math.sin(x * 127.1 + y * 311.7 + n * 53.9) * 43758.5453;
    return v - Math.floor(v);
  };
  const mix = (a, b, t) => a + (b - a) * t;
  const tint = (hex, factor) =>
    "#" +
    hex
      .replace("#", "")
      .match(/../g)
      .map((x) =>
        Math.round(clamp(parseInt(x, 16) * factor, 0, 255))
          .toString(16)
          .padStart(2, "0"),
      )
      .join("");
  const PALETTE = {
    grass: ["#6a9f49", "#73a752", "#80ae58", "#679744"],
    stone: "#acb3a7",
    wood: "#71513a",
    water: "#369cb3",
  };
  class NewHavenWorld {
    constructor(canvas, { onSelect = () => {} } = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.onSelect = onSelect;
      this.state = { citizens: [], buildings: [], terrain: [] };
      this.selected = null;
      this.hits = [];
      this.scale = 1;
      this.pan = { x: 0, y: 0 };
      this.positions = new Map();
      this.start = performance.now();
      this.width = 900;
      this.height = 650;
      this.drag = null;
      this.time = 0;
      this.motion = !matchMedia("(prefers-reduced-motion: reduce)").matches;
      this.listeners = [];
      const listen = (name, fn, opts) => {
        canvas.addEventListener(name, fn, opts);
        this.listeners.push([name, fn, opts]);
      };
      canvas.style.touchAction = "none";
      listen("pointerdown", (e) => {
        this.drag = {
          x: e.clientX,
          y: e.clientY,
          ox: this.pan.x,
          oy: this.pan.y,
          moved: false,
        };
        canvas.setPointerCapture(e.pointerId);
      });
      listen("pointermove", (e) => {
        if (this.drag) {
          const dx = e.clientX - this.drag.x,
            dy = e.clientY - this.drag.y;
          if (Math.hypot(dx, dy) > 5) this.drag.moved = true;
          this.pan = { x: this.drag.ox + dx, y: this.drag.oy + dy };
        } else {
          const h = this.hit(e);
          canvas.style.cursor = h ? "pointer" : "grab";
          canvas.title =
            h?.name ||
            "Drag to explore. Scroll to zoom. Select a resident or building.";
        }
      });
      listen("pointerup", (e) => {
        if (this.drag && !this.drag.moved) {
          const h = this.hit(e);
          this.selected = h ? { type: h.type, id: h.id } : null;
          this.onSelect(this.selected);
        }
        this.drag = null;
      });
      listen("pointercancel", () => (this.drag = null));
      listen(
        "wheel",
        (e) => {
          e.preventDefault();
          this.zoom(Math.exp(-e.deltaY * 0.001));
        },
        { passive: false },
      );
      listen("keydown", (e) => {
        const steps = {
          ArrowLeft: [30, 0],
          ArrowRight: [-30, 0],
          ArrowUp: [0, 30],
          ArrowDown: [0, -30],
        };
        if (steps[e.key]) {
          e.preventDefault();
          this.pan.x += steps[e.key][0];
          this.pan.y += steps[e.key][1];
        }
        if (e.key === "+" || e.key === "=") this.zoom(1.15);
        if (e.key === "-") this.zoom(1 / 1.15);
        if (e.key === "Home") this.recenter();
      });
      this.observer = new ResizeObserver(() => this.resize());
      this.observer.observe(canvas);
      this.resize();
      // Limit the diorama to 30fps (10fps with reduced motion). Simulation speed
      // is owned by the host and never depends on the graphics frame rate.
      let lastFrame = 0;
      const loop = (now) => {
        if (this.destroyed) return;
        if (now - lastFrame >= (this.motion ? 32 : 100)) {
          this.draw(now);
          lastFrame = now;
        }
        this.raf = requestAnimationFrame(loop);
      };
      this.raf = requestAnimationFrame(loop);
    }
    setState(state) {
      const now = performance.now(),
        previous = this.state;
      this.positions = new Map(
        (previous.citizens || []).map((c) => [
          String(c.id),
          this.position(c, now),
        ]),
      );
      if (state.day < previous.day || state.seed !== previous.seed)
        this.positions.clear();
      this.state = state;
      this.start = now;
      this.occupied = new Set(
        (state.buildings || []).flatMap((b) => {
          const a = [];
          for (let x = -1; x <= 1; x++)
            for (let y = -1; y <= 1; y++) a.push(`${b.x + x},${b.y + y}`);
          return a;
        }),
      );
    }
    setSelected(s) {
      this.selected = s;
    }
    resize() {
      const r = this.canvas.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return;
      this.width = r.width;
      this.height = r.height;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      this.canvas.width = Math.round(r.width * dpr);
      this.canvas.height = Math.round(r.height * dpr);
      this.dpr = dpr;
      this.draw(performance.now());
    }
    zoom(f) {
      this.scale = clamp(this.scale * f, 0.55, 2.6);
    }
    recenter() {
      this.scale = 1;
      this.pan = { x: 0, y: 0 };
    }
    destroy() {
      this.destroyed = true;
      cancelAnimationFrame(this.raf);
      this.observer.disconnect();
      this.listeners.forEach(([n, f, o]) =>
        this.canvas.removeEventListener(n, f, o),
      );
    }
    hit(e) {
      const r = this.canvas.getBoundingClientRect(),
        x = e.clientX - r.left,
        y = e.clientY - r.top;
      return [...this.hits]
        .reverse()
        .find((h) => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
    }
    elevation(x, y) {
      if (x === 19) return -0.35;
      if (x >= 0 && x < 24 && y >= 0 && y < 20) {
        if (x === 12 || y === 9) return 0.1;
        if (x > 20 && y < 7)
          return Math.floor((x - 20) * 0.45 + (7 - y) * 0.14);
        return 0.1;
      }
      // Broad rolling terraces, not one abrupt rectangular retaining wall.
      // The near valley stays low while the distant northern ridge rises.
      const hill = Math.max(
        0,
        Math.sin((x + 5) * 0.21) * 1.2 + Math.cos((y + 5) * 0.18) * 0.7,
      );
      const rise = Math.max(
        -y * 0.38,
        -x * 0.3,
        (x - 24) * 0.35,
        (y - 20) * 0.12,
        0,
      );
      return Math.floor(Math.min(4.5, rise + hill) * 2) / 2;
    }
    p(x, y, z = 0) {
      return {
        x: this.ox + (x - y) * this.tw,
        y: this.oy + (x + y) * this.th - z * this.unit,
      };
    }
    poly(points, color, stroke) {
      const c = this.ctx;
      c.beginPath();
      points.forEach((p, i) => (i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)));
      c.closePath();
      c.fillStyle = color;
      c.fill();
      if (stroke) {
        c.strokeStyle = stroke;
        c.lineWidth = 0.7 * this.scale;
        c.stroke();
      }
    }
    face(coords, color, stroke) {
      this.poly(
        coords.map((p) => this.p(...p)),
        color,
        stroke,
      );
    }
    box(x, y, z, w, d, h, color, top) {
      const a = this.p(x, y, z + h),
        b = this.p(x + w, y, z + h),
        c = this.p(x + w, y + d, z + h),
        e = this.p(x, y + d, z + h),
        f = this.p(x + w, y, z),
        g = this.p(x + w, y + d, z),
        i = this.p(x, y + d, z);
      this.poly([e, c, g, i], tint(color, 0.72));
      this.poly([b, c, g, f], tint(color, 0.88));
      this.poly([a, b, c, e], top || tint(color, 1.13));
    }
    line(coords, color, width = 1) {
      const c = this.ctx;
      c.beginPath();
      coords
        .map((p) => this.p(...p))
        .forEach((p, i) => (i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)));
      c.strokeStyle = color;
      c.lineWidth = width * this.scale;
      c.stroke();
    }
    shadow(x, y, size = 0.6) {
      const p = this.p(
          x,
          y,
          this.elevation(Math.floor(x), Math.floor(y)) + 0.04,
        ),
        c = this.ctx;
      c.fillStyle = "#243e332b";
      c.beginPath();
      c.ellipse(
        p.x,
        p.y,
        size * this.tw,
        size * this.th * 0.65,
        0,
        0,
        Math.PI * 2,
      );
      c.fill();
    }
    ground(x, y) {
      const z = this.elevation(x, y),
        water = x === 19,
        road = (x === 12 || y === 9) && x >= 0 && x < 24 && y >= 0 && y < 20;
      let color = water
        ? PALETTE.water
        : road
          ? "#c4bba0"
          : PALETTE.grass[Math.floor(hash(x, y) * 4)];
      if (this.state.season === "Winter")
        color = water
          ? "#679fae"
          : road
            ? "#bfc8bc"
            : ["#c5d5be", "#d1dbcc", "#adbea6"][Math.floor(hash(x, y) * 3)];
      if (this.state.season === "Autumn" && !water && !road)
        color = ["#939547", "#a3a051", "#829448"][Math.floor(hash(x, y) * 3)];
      // Close every raised tile side. Unclosed .14-height tiles previously
      // exposed the pale sky as distracting white seams across the valley.
      if (!water) {
        const base = z > 0.7 ? "#879789" : "#648047";
        this.box(x, y, -0.36, 1, 1, z + 0.36, base, color);
        if (z > 0.7) {
          for (let h = 0.25; h < z - 0.12; h += 0.55) {
            this.line(
              [
                [x + 1, y, h],
                [x + 1, y + 1, h],
                [x, y + 1, h],
              ],
              "#657f7166",
              0.8,
            );
            const a = hash(x, y, Math.round(h * 10));
            this.line(
              [
                [x + 1, y + a, h],
                [x + 1, y + a, Math.min(h + 0.5, z)],
              ],
              "#647b6d55",
              0.7,
            );
          }
        }
      }
      this.face(
        [
          [x, y, z],
          [x + 1, y, z],
          [x + 1, y + 1, z],
          [x, y + 1, z],
        ],
        color,
      );
      if (water) {
        const wave = this.motion ? Math.sin(this.time * 0.0014 + y) * 0.12 : 0;
        this.line(
          [
            [x + 0.15, y + 0.3 + wave, z + 0.025],
            [x + 0.72, y + 0.3 + wave, z + 0.025],
          ],
          "#a8e1d477",
          1.2,
        );
        this.line(
          [
            [x + 0.5, y + 0.75 - wave, z + 0.025],
            [x + 0.9, y + 0.75 - wave, z + 0.025],
          ],
          "#9de1e255",
          0.8,
        );
      } else if (road) {
        for (let k = 0; k < 3; k++) {
          const a = hash(x, y, k + 1) * 0.8,
            b = hash(y, x, k + 8) * 0.8;
          this.face(
            [
              [x + a, y + b, z + 0.01],
              [x + a + 0.16, y + b, z + 0.01],
              [x + a + 0.16, y + b + 0.11, z + 0.01],
              [x + a, y + b + 0.11, z + 0.01],
            ],
            "#e3dbc055",
          );
        }
      } else if (z < 1 && hash(x, y) > 0.68) {
        for (let k = 0; k < 3; k++) {
          const a = hash(x, y, k + 2),
            b = hash(x, y, k + 6);
          this.line(
            [
              [x + a, y + b, z],
              [x + a, y + b, z + 0.09],
            ],
            "#bfd17a",
            0.8,
          );
        }
      }
      if (this.flood && x >= 18 && x <= 20 && y !== 9) {
        this.face(
          [
            [x, y, z + 0.06],
            [x + 1, y, z + 0.06],
            [x + 1, y + 1, z + 0.06],
            [x, y + 1, z + 0.06],
          ],
          "#53aabc77",
        );
      }
    }
    tree(x, y, n, small = false) {
      const z = this.elevation(Math.floor(x), Math.floor(y)),
        h = (small ? 0.6 : 1) + hash(x, y) * 0.45;
      this.shadow(x, y, 0.46);
      this.box(x - 0.065, y - 0.065, z, 0.13, 0.13, h * 0.9, "#76543a");
      const autumn = this.state.season === "Autumn",
        winter = this.state.season === "Winter";
      const color = winter
        ? "#769684"
        : autumn
          ? ["#bd853c", "#b3a241", "#b7603e"][n % 3]
          : ["#398047", "#4b934b", "#2f7441", "#6ca64b"][n % 4];
      if (n % 4 === 0) {
        for (let i = 0; i < 3; i++) {
          const s = 0.78 - i * 0.18;
          this.box(
            x - s / 2,
            y - s / 2,
            z + h * 0.45 + i * 0.36,
            s,
            s,
            0.28,
            color,
          );
        }
      } else {
        this.box(x - 0.38, y - 0.34, z + h * 0.65, 0.76, 0.68, 0.55, color);
        this.box(
          x - 0.27,
          y - 0.25,
          z + h * 0.65 + 0.55,
          0.54,
          0.5,
          0.3,
          tint(color, 1.1),
        );
        this.box(
          x - 0.5,
          y - 0.18,
          z + h * 0.65 + 0.12,
          0.3,
          0.42,
          0.3,
          tint(color, 0.95),
        );
      }
      if (winter)
        this.box(
          x - 0.26,
          y - 0.23,
          z + h * 0.65 + 0.8,
          0.52,
          0.46,
          0.07,
          "#dbe6dc",
        );
    }
    roof(x, y, z, w, d, height, color) {
      this.face(
        [
          [x, y, z],
          [x + w / 2, y, z + height],
          [x + w, y, z],
        ],
        tint(color, 0.77),
      );
      this.face(
        [
          [x, y + d, z],
          [x + w / 2, y + d, z + height],
          [x + w, y + d, z],
        ],
        tint(color, 0.65),
      );
      this.face(
        [
          [x + w / 2, y, z + height],
          [x + w, y, z],
          [x + w, y + d, z],
          [x + w / 2, y + d, z + height],
        ],
        color,
      );
      this.face(
        [
          [x, y, z],
          [x + w / 2, y, z + height],
          [x + w / 2, y + d, z + height],
          [x, y + d, z],
        ],
        tint(color, 1.2),
      );
      for (let i = 1; i < 5; i++) {
        const t = i / 5;
        this.line(
          [
            [x + w / 2 + (w / 2) * t, y, z + height * (1 - t)],
            [x + w / 2 + (w / 2) * t, y + d, z + height * (1 - t)],
          ],
          tint(color, 0.79),
          0.7,
        );
      }
      for (let i = 1; i < 5; i++)
        this.line(
          [
            [x + w / 2, y + (d * i) / 5, z + height],
            [x + w, y + (d * i) / 5, z],
          ],
          tint(color, 0.92),
          0.6,
        );
    }
    window(x, y, z, side = true) {
      const glow = this.state.weather === "Storm";
      if (side) {
        this.face(
          [
            [x, y, z],
            [x + 0.21, y, z],
            [x + 0.21, y, z + 0.26],
            [x, y, z + 0.26],
          ],
          glow ? "#f4cb74" : "#38616a",
        );
        this.line(
          [
            [x + 0.105, y, z],
            [x + 0.105, y, z + 0.26],
          ],
          "#e6d6af",
          1,
        );
        this.line(
          [
            [x, y, z + 0.13],
            [x + 0.21, y, z + 0.13],
          ],
          "#e6d6af",
          1,
        );
      } else {
        this.face(
          [
            [x, y, z],
            [x, y + 0.21, z],
            [x, y + 0.21, z + 0.26],
            [x, y, z + 0.26],
          ],
          glow ? "#f4cb74" : "#38616a",
        );
        this.line(
          [
            [x, y + 0.105, z],
            [x, y + 0.105, z + 0.26],
          ],
          "#e6d6af",
          1,
        );
      }
    }
    house(b) {
      const x = b.x - 0.53,
        y = b.y - 0.5,
        z = this.elevation(b.x, b.y),
        special = b.kind === "council",
        w = special
          ? 1.5
          : b.kind === "school"
            ? 1.65
            : 1.08 + (b.id % 3) * 0.13,
        d = special ? 1.38 : 0.95 + (b.id % 2) * 0.19,
        h = special
          ? 1.7
          : b.kind === "school"
            ? 1.24
            : 0.82 + (b.id % 3) * 0.13;
      const roofColors = {
        home: "#8c613c",
        bakery: "#ab5942",
        school: "#537d88",
        clinic: "#6a8380",
        workshop: "#77665a",
        farm: "#997a42",
        forest: "#67714b",
      };
      const color =
        b.kind === "home"
          ? ["#946b43", "#a46a45", "#807a58", "#9a7748"][b.id % 4]
          : roofColors[b.kind] || "#ad644a";
      this.shadow(b.x, b.y, 1);
      this.box(x - 0.1, y - 0.1, z, w + 0.2, d + 0.2, 0.16, "#a0a294");
      this.box(x, y, z + 0.16, w, d, h, "#d5c9aa");
      for (const a of [0, w * 0.5, w - 0.07])
        this.box(x + a, y + d - 0.025, z + 0.16, 0.065, 0.05, h, "#735740");
      for (const a of [0, d - 0.07])
        this.box(x + w - 0.025, y + a, z + 0.16, 0.05, 0.065, h, "#735740");
      this.box(x, y + d - 0.03, z + 0.48, w, 0.06, 0.055, "#886245");
      this.roof(
        x - 0.13,
        y - 0.13,
        z + h + 0.16,
        w + 0.26,
        d + 0.26,
        0.63,
        color,
      );
      this.window(x + 0.1, y + d + 0.004, z + 0.61);
      this.window(x + 0.72, y + d + 0.004, z + 0.61);
      this.window(x + w + 0.004, y + 0.19, z + 0.57, false);
      this.face(
        [
          [x + w * 0.43, y + d + 0.009, z + 0.16],
          [x + w * 0.65, y + d + 0.009, z + 0.16],
          [x + w * 0.65, y + d + 0.009, z + 0.69],
          [x + w * 0.43, y + d + 0.009, z + 0.69],
        ],
        "#664b36",
      );
      this.box(x + w * 0.37, y + d, z + 0.03, 0.4, 0.24, 0.14, "#b9b3a2");
      this.box(x + 0.12, y + 0.2, z + h + 0.54, 0.2, 0.2, 0.58, "#a29a86");
      if (b.kind === "bakery" || b.kind === "home")
        this.smoke(x + 0.2, y + 0.28, z + h + 1.13, b.id);
      if (special) {
        this.box(
          x + w * 0.35,
          y + 0.27,
          z + h + 0.35,
          0.58,
          0.58,
          1.48,
          "#b8b5a0",
        );
        this.roof(
          x + w * 0.35 - 0.1,
          y + 0.17,
          z + h + 1.83,
          0.78,
          0.78,
          0.64,
          "#a95340",
        );
        this.line(
          [
            [x + w * 0.65, y + 0.5, z + h + 2.4],
            [x + w * 0.65, y + 0.5, z + h + 3],
          ],
          "#dacfa3",
          1.5,
        );
        this.face(
          [
            [x + w * 0.65, y + 0.5, z + h + 3],
            [x + w * 0.65 + 0.52, y + 0.5, z + h + 2.96],
            [x + w * 0.65 + 0.52, y + 0.5, z + h + 2.7],
            [x + w * 0.65, y + 0.5, z + h + 2.72],
          ],
          "#468dba",
        );
        const p = this.p(x + w * 0.65, y + 0.855, z + h + 1.22);
        this.ctx.fillStyle = "#e5dcc0";
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, 4 * this.scale, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = "#536767";
        this.ctx.fillRect(
          p.x,
          p.y - 3 * this.scale,
          this.scale,
          3 * this.scale,
        );
      }
      if (b.kind === "clinic") {
        this.box(
          x + w * 0.3,
          y + d + 0.015,
          z + 0.89,
          0.4,
          0.025,
          0.09,
          "#e9f0de",
        );
        this.box(
          x + w * 0.45,
          y + d + 0.02,
          z + 0.75,
          0.09,
          0.025,
          0.35,
          "#e9f0de",
        );
      }
      if (b.kind === "bakery") {
        this.box(
          x - 0.1,
          y + d + 0.03,
          z + 0.69,
          w + 0.2,
          0.6,
          0.035,
          "#c99b65",
        );
        for (let i = 0; i < 5; i++)
          this.box(
            x - 0.1 + (i * (w + 0.2)) / 5,
            y + d + 0.03,
            z + 0.73,
            (w + 0.2) / 10,
            0.6,
            0.025,
            "#f0dfb8",
          );
        this.box(x - 0.03, y + d + 0.51, z, 0.055, 0.055, 0.71, "#8a6a44");
        this.box(x + w + 0.02, y + d + 0.51, z, 0.055, 0.055, 0.71, "#8a6a44");
        this.box(x + 0.08, y + d + 0.08, z + 0.16, 0.29, 0.29, 0.21, "#ab834d");
      }
      if (b.kind === "school") {
        this.box(
          x + w * 0.5 - 0.15,
          y + 0.3,
          z + h + 0.57,
          0.3,
          0.3,
          0.49,
          "#d6c6a1",
        );
        this.roof(
          x + w * 0.5 - 0.23,
          y + 0.22,
          z + h + 1.06,
          0.46,
          0.46,
          0.25,
          "#4e7282",
        );
        this.face(
          [
            [x + w * 0.5 - 0.07, y + 0.61, z + h + 0.67],
            [x + w * 0.5 + 0.07, y + 0.61, z + h + 0.67],
            [x + w * 0.5 + 0.07, y + 0.61, z + h + 0.95],
            [x + w * 0.5 - 0.07, y + 0.61, z + h + 0.95],
          ],
          "#596759",
        );
      }
      if (b.kind === "home") {
        // Small lived-in yards: hedges, planted boxes and wood piles are
        // architectural detail, not invented simulation-owned buildings.
        for (let i = 0; i < 3; i++)
          this.box(
            x - 0.29,
            y + 0.15 + i * 0.22,
            z,
            0.17,
            0.2,
            0.23,
            "#709755",
          );
        this.box(
          x + 0.07,
          y + d + 0.015,
          z + 0.56,
          0.24,
          0.12,
          0.08,
          "#98734b",
        );
        for (let i = 0; i < 3; i++)
          this.box(
            x + 0.08 + i * 0.08,
            y + d + 0.035,
            z + 0.65,
            0.045,
            0.045,
            0.06,
            ["#d9ae71", "#b56c61", "#d7c379"][b.id % 3],
          );
        if (b.id % 2 === 0) {
          this.box(x + w + 0.02, y + 0.12, z, 0.38, 0.66, 0.52, "#c9b99a");
          this.roof(
            x + w - 0.04,
            y + 0.06,
            z + 0.52,
            0.51,
            0.78,
            0.25,
            "#827257",
          );
        }
      }
      if (b.kind === "workshop" || b.kind === "forest") {
        for (let i = 0; i < 4; i++)
          this.box(x + w + 0.1, y + i * 0.16, z, 0.45, 0.13, 0.12, "#a47a48");
      }
      const condition = Number.isFinite(b.condition) ? b.condition : 100;
      if (condition < 90) {
        this.line(
          [
            [x + 0.08, y + d + 0.015, z + 0.9],
            [x + 0.25, y + d + 0.015, z + 0.64],
            [x + 0.14, y + d + 0.015, z + 0.43],
          ],
          "#614e40",
          2,
        );
        for (let i = 0; i < Math.ceil((100 - condition) / 12); i++)
          this.box(
            x + 0.1 + i * 0.13,
            y + d + 0.28,
            z,
            0.17,
            0.15,
            0.08,
            ["#a48e70", "#7f7160", "#b5ae92"][i % 3],
          );
        if (condition < 65)
          this.face(
            [
              [x + w * 0.68, y + 0.2, z + h + 0.39],
              [x + w * 0.94, y + 0.2, z + h + 0.2],
              [x + w * 0.94, y + 0.59, z + h + 0.2],
              [x + w * 0.68, y + 0.59, z + h + 0.39],
            ],
            "#453a32",
          );
      }
      if (b.construction)
        this.scaffold(x - 0.18, y + d + 0.2, z, w);
      if ((b.level || 0) > 0)
        this.box(x - 0.43, y + 0.3, z, 0.27, 0.65, 0.45, "#ac9879");
      this.buildHit(b, w, d, h + (special ? 2 : 1));
    }
    scaffold(x, y, z, w) {
      for (let a = 0; a <= w; a += 0.5) {
        this.box(x + a, y, z, 0.055, 0.055, 1.9, "#b0915f");
      }
      for (let h = 0.5; h < 2; h += 0.55)
        this.box(x, y, z + h, w + 0.1, 0.17, 0.045, "#b0915f");
      this.line(
        [
          [x, y, z],
          [x + w, y, z + 1.6],
        ],
        "#d2b98c",
        1.5,
      );
    }
    smoke(x, y, z, id) {
      if (!this.motion) return;
      const c = this.ctx;
      for (let i = 0; i < 3; i++) {
        const phase = (this.time * 0.00012 + i * 0.32 + id * 0.11) % 1,
          p = this.p(x + phase * 0.3, y, z + phase * 0.9);
        c.fillStyle = `rgba(231,235,222,${0.28 * (1 - phase)})`;
        const s = (2 + phase * 5) * this.scale;
        c.fillRect(p.x - s / 2, p.y - s / 2, s, s);
      }
    }
    crops() {
      const production = this.state.ledger?.food_produced,
        food = this.state.food || 0;
      const lush =
        production == null
          ? 1
          : clamp(
              production / Math.max(1, this.state.population || 100),
              0.3,
              1.25,
            );
      for (let x = 2; x < 8; x++)
        for (let y = 12; y < 18; y++) {
          if (this.occupied?.has(`${x},${y}`)) continue;
          const z = this.elevation(x, y);
          this.face(
            [
              [x + 0.04, y + 0.04, z + 0.01],
              [x + 0.96, y + 0.04, z + 0.01],
              [x + 0.96, y + 0.96, z + 0.01],
              [x + 0.04, y + 0.96, z + 0.01],
            ],
            "#806541",
          );
          for (let r = 0; r < 3; r++)
            for (let s = 0; s < 3; s++) {
              const xx = x + 0.2 + r * 0.28,
                yy = y + 0.2 + s * 0.28,
                h = (0.13 + hash(x + r, y + s) * 0.17) * lush;
              this.line(
                [
                  [xx, yy, z + 0.02],
                  [xx, yy, z + h],
                ],
                "#ded16a",
                1.5,
              );
              this.box(
                xx - 0.035,
                yy - 0.035,
                z + h,
                0.07,
                0.07,
                0.09,
                this.state.season === "Winter"
                  ? "#8a9666"
                  : food < 100
                    ? "#aeaa50"
                    : "#dbbc51",
              );
            }
        }
      for (let x = 2; x <= 8; x += 0.5) {
        this.fence(x, 11.9);
        this.fence(x, 18.05);
      }
      for (let y = 12; y <= 18; y += 0.5) {
        this.fence(1.9, y, true);
        this.fence(8.05, y, true);
      }
    }
    fence(x, y, alongY = false) {
      const z = this.elevation(Math.floor(x), Math.floor(y));
      this.box(x, y, z, 0.065, 0.065, 0.3, "#a58d61");
      this.box(
        x,
        y,
        z + 0.2,
        alongY ? 0.055 : 0.52,
        alongY ? 0.52 : 0.055,
        0.055,
        "#b8a274",
      );
    }
    market(b) {
      const z = this.elevation(b.x, b.y);
      for (let i = 0; i < 3; i++) {
        const x = b.x - 1 + i * 0.8,
          y = b.y - 0.55 + (i % 2) * 0.4;
        for (let a = 0; a < 2; a++)
          for (let q = 0; q < 2; q++)
            this.box(
              x + a * 0.62,
              y + q * 0.52,
              z,
              0.045,
              0.045,
              0.76,
              "#866440",
            );
        this.box(x, y + 0.12, z, 0.67, 0.4, 0.32, "#ae8956");
        for (let stripe = 0; stripe < 4; stripe++)
          this.box(
            x - 0.06 + stripe * 0.2,
            y - 0.08,
            z + 0.76,
            0.2,
            0.78,
            0.04,
            stripe % 2 ? "#eee2b3" : ["#b65244", "#4e91a7", "#bc9550"][i],
          );
        for (let j = 0; j < 3; j++)
          this.box(
            x + 0.06 + j * 0.19,
            y + 0.23,
            z + 0.34,
            0.14,
            0.17,
            0.13,
            ["#dcaa48", "#819e47", "#c47746"][j],
          );
      }
      this.buildHit(b, 2.2, 1, 1);
    }
    mine(b) {
      const x = b.x,
        y = b.y,
        z = this.elevation(x, y);
      this.box(x - 0.8, y - 0.65, z, 1.6, 1.4, 1.55, "#7c8980");
      this.box(x - 0.55, y - 0.4, z + 1.5, 1.1, 0.9, 0.43, "#8e998d");
      this.face(
        [
          [x - 0.3, y + 0.76, z],
          [x + 0.36, y + 0.76, z],
          [x + 0.36, y + 0.76, z + 0.87],
          [x - 0.3, y + 0.76, z + 0.87],
        ],
        "#263c3b",
      );
      this.box(x - 0.4, y + 0.78, z, 0.09, 0.07, 1.05, "#96754e");
      this.box(x + 0.34, y + 0.78, z, 0.09, 0.07, 1.05, "#96754e");
      this.box(x - 0.4, y + 0.78, z + 0.95, 0.83, 0.08, 0.13, "#ae8552");
      for (let k = 0; k < 5; k++)
        this.box(x - 0.31, y + 0.9 + k * 0.22, z, 0.64, 0.05, 0.04, "#806751");
      this.line(
        [
          [x - 0.19, y + 0.85, z + 0.05],
          [x - 0.19, y + 2, z + 0.05],
        ],
        "#b5b7a5",
        1.5,
      );
      this.line(
        [
          [x + 0.2, y + 0.85, z + 0.05],
          [x + 0.2, y + 2, z + 0.05],
        ],
        "#b5b7a5",
        1.5,
      );
      this.box(x + 0.65, y + 0.82, z, 0.4, 0.5, 0.26, "#6f6856");
      this.buildHit(b, 1.8, 1.6, 2);
    }
    windmill() {
      const x = 7.9,
        y = 15.2,
        z = 0.1;
      this.box(x, y, z, 0.65, 0.65, 1.4, "#cac3a5");
      this.box(x + 0.08, y + 0.08, z + 1.4, 0.49, 0.49, 0.7, "#d2cab0");
      this.roof(x - 0.08, y - 0.08, z + 2.1, 0.81, 0.81, 0.48, "#8f7051");
      const p = this.p(x + 0.35, y + 0.72, z + 1.75),
        c = this.ctx,
        ang = this.motion ? this.time * 0.00025 : 0;
      c.save();
      c.translate(p.x, p.y);
      c.rotate(ang);
      for (let i = 0; i < 4; i++) {
        c.rotate(Math.PI / 2);
        c.fillStyle = "#806e4c";
        c.fillRect(
          -1 * this.scale,
          -2 * this.scale,
          2 * this.scale,
          25 * this.scale,
        );
        c.fillStyle = "#e4d7b4";
        c.fillRect(
          1 * this.scale,
          6 * this.scale,
          7 * this.scale,
          18 * this.scale,
        );
        c.strokeStyle = "#b5a782";
        c.lineWidth = 0.6 * this.scale;
        for (let q = 9; q < 24; q += 4) {
          c.beginPath();
          c.moveTo(this.scale, q * this.scale);
          c.lineTo(8 * this.scale, q * this.scale);
          c.stroke();
        }
      }
      c.restore();
    }
    square() {
      for (let x = 10; x <= 14; x++)
        for (let y = 7; y <= 9; y++) {
          const z = 0.23;
          this.face(
            [
              [x, y, z],
              [x + 1, y, z],
              [x + 1, y + 1, z],
              [x, y + 1, z],
            ],
            (x + y) % 2 ? "#b9b7a1" : "#c2beaa",
          );
        }
      this.box(10.5, 7.8, 0.27, 1.15, 1.15, 0.18, "#c4c6b5");
      this.box(10.64, 7.94, 0.45, 0.87, 0.87, 0.035, "#70b4bb");
      this.box(10.99, 8.29, 0.49, 0.18, 0.18, 0.67, "#d0d4bf");
      this.box(10.87, 8.17, 1.1, 0.42, 0.42, 0.11, "#dfe0cd");
      const phase = this.motion ? Math.sin(this.time * 0.003) * 0.1 : 0;
      this.line(
        [
          [11.08, 8.38, 1.33],
          [11.08, 8.38, 1.12],
        ],
        "#c4f3ef",
        1.6,
      );
      for (let i = 0; i < 3; i++)
        this.line(
          [
            [10.89 + i * 0.16, 8.53, 0.98 + phase],
            [10.89 + i * 0.16, 8.53, 0.51],
          ],
          "#c4f3ef99",
          0.8,
        );
      for (const [x, y] of [
        [10, 7.3],
        [14.4, 8],
        [9.9, 10.1],
        [13.2, 4.3],
      ]) {
        this.box(x, y, 0.1, 0.1, 0.1, 1.2, "#485b51");
        this.box(x - 0.08, y - 0.08, 1.3, 0.26, 0.26, 0.28, "#d1b66b");
        this.roof(x - 0.12, y - 0.12, 1.58, 0.34, 0.34, 0.15, "#4b5a4b");
      }
    }
    bridge() {
      this.box(18.2, 8.85, 0.16, 2.6, 1.08, 0.24, "#afa991");
      for (let i = 0; i < 7; i++) {
        this.box(18.2 + i * 0.37, 8.78, 0.3, 0.1, 0.1, 0.44, "#c6bda5");
        this.box(18.2 + i * 0.37, 9.95, 0.3, 0.1, 0.1, 0.44, "#c6bda5");
      }
      this.box(18.2, 8.79, 0.63, 2.6, 0.08, 0.1, "#c2bba3");
      this.box(18.2, 9.96, 0.63, 2.6, 0.08, 0.1, "#c2bba3");
    }
    waterfall() {
      const x = 19,
        y = -3,
        z = 3;
      this.box(x - 1, y - 1, -0.35, 3, 1, z + 0.35, "#7c9187");
      this.face(
        [
          [x, y, z],
          [x + 1, y, z],
          [x + 1, y, -0.3],
          [x, y, -0.3],
        ],
        "#71cbd0",
      );
      for (let k = 0; k < 5; k++) {
        const wave = this.motion ? (this.time * 0.0009 + k * 0.17) % 1 : 0.5;
        this.line(
          [
            [x + 0.1 + k * 0.18, y, z - wave * 2.8],
            [x + 0.1 + k * 0.18, y, z - wave * 2.8 - 0.3],
          ],
          "#d4f3e1",
          1.5,
        );
      }
      this.face(
        [
          [18.8, -2.5, -0.32],
          [20.2, -2.5, -0.32],
          [20.2, -1.4, -0.32],
          [18.8, -1.4, -0.32],
        ],
        "#85d2ca",
      );
    }
    position(c, now) {
      const old = this.positions.get(String(c.id));
      const t = this.motion ? clamp((now - this.start) / 1200, 0, 1) : 1;
      return {
        x: old ? mix(old.x, c.x, t) : c.x,
        y: old ? mix(old.y, c.y, t) : c.y,
      };
    }
    resident(c, now) {
      const a = this.position(c, now),
        j = ((c.id % 7) - 3) * 0.075,
        k = ((Math.floor(c.id / 7) % 7) - 3) * 0.07,
        x = a.x + j,
        y = a.y + k,
        z = this.elevation(Math.floor(a.x), Math.floor(a.y)) + 0.04;
      const colors = {
        Farmer: "#d2ae47",
        Baker: "#e5d5b4",
        Builder: "#bc7951",
        Teacher: "#688fa3",
        Medic: "#a8ccc0",
        Merchant: "#886c9d",
        Miner: "#718695",
        Forester: "#7d9b53",
      };
      const color = colors[c.job] || "#9c85a0";
      const moving =
        this.motion &&
        now - this.start < 1200 &&
        this.positions.has(String(c.id));
      const walk = moving ? Math.sin(now * 0.018 + c.id) * 0.035 : 0;
      this.shadow(x, y, 0.13);
      this.box(x - 0.075, y - 0.065, z + walk, 0.055, 0.1, 0.16, "#485359");
      this.box(x + 0.02, y - 0.065, z - walk, 0.055, 0.1, 0.16, "#485359");
      this.box(x - 0.09, y - 0.075, z + 0.15, 0.18, 0.15, 0.24, color);
      this.box(
        x - 0.07,
        y - 0.063,
        z + 0.4,
        0.14,
        0.13,
        0.14,
        ["#d9b790", "#c89372", "#987254"][c.id % 3],
      );
      this.box(
        x - 0.08,
        y - 0.065,
        z + 0.53,
        0.16,
        0.14,
        0.035,
        ["#5b463a", "#b28a50", "#7c5940"][c.id % 3],
      );
      if (c.activity?.includes("repair"))
        this.box(x + 0.09, y, z + 0.28, 0.17, 0.06, 0.065, "#a4a89c");
      const p = this.p(x, y, z + 0.6),
        foot = this.p(x, y, z);
      this.hits.push({
        type: "citizen",
        id: c.id,
        name: c.name,
        x: p.x - 8 * this.scale,
        y: p.y - 3 * this.scale,
        w: 16 * this.scale,
        h: Math.max(16 * this.scale, foot.y - p.y + 5 * this.scale),
      });
      if (
        this.selected?.type === "citizen" &&
        String(this.selected.id) === String(c.id)
      )
        this.label(c.name, x, y, z + 0.9, true);
    }
    buildHit(b, w, d, h) {
      const z = this.elevation(b.x, b.y),
        p = this.p(b.x, b.y, z),
        top = this.p(b.x, b.y, z + h);
      this.hits.push({
        type: "building",
        id: b.id,
        name: b.name || b.kind,
        x: p.x - (w + d) * this.tw * 0.55,
        y: top.y,
        w: (w + d) * this.tw * 1.1,
        h: p.y - top.y + d * this.th,
      });
    }
    label(text, x, y, z, selected = false) {
      const p = this.p(x, y, z),
        c = this.ctx;
      c.save();
      c.font = `${selected ? 600 : 500} ${Math.max(10, 11 * this.scale)}px system-ui,sans-serif`;
      const w = c.measureText(text).width + 16,
        h = 23;
      c.shadowColor = "#112c3544";
      c.shadowBlur = 9;
      c.fillStyle = selected ? "#e7bf6b" : "#173a3bed";
      c.beginPath();
      c.roundRect(p.x - w / 2, p.y - h, w, h, 4);
      c.fill();
      c.shadowBlur = 0;
      c.fillStyle = selected ? "#1e3636" : "#fffdf1";
      c.fillText(text, p.x - w / 2 + 8, p.y - 7);
      c.restore();
    }
    draw(now) {
      this.time = now;
      const c = this.ctx;
      if (!this.width || !this.height) return;
      c.setTransform(this.dpr || 1, 0, 0, this.dpr || 1, 0, 0);
      c.clearRect(0, 0, this.width, this.height);
      const sky = c.createLinearGradient(0, 0, 0, this.height);
      sky.addColorStop(0, "#b7d9d9");
      sky.addColorStop(0.55, "#d6e2c3");
      sky.addColorStop(1, "#a7bf8b");
      c.fillStyle = sky;
      c.fillRect(0, 0, this.width, this.height);
      this.unit = 25 * this.scale;
      this.tw = 25 * this.scale;
      this.th = 12.5 * this.scale;
      this.ox = this.width * 0.5 - this.tw * 1.5 + this.pan.x;
      this.oy = this.height * 0.5 - this.th * 20 + this.pan.y;
      this.flood = (this.state.active_effects || []).some(
        (e) => e.kind === "flood",
      );
      this.hits = [];
      for (let sum = -12; sum < 66; sum++)
        for (let x = -7; x < 33; x++) {
          const y = sum - x;
          if (y < -7 || y > 28) continue;
          this.ground(x, y);
        }
      this.waterfall();
      this.square();
      this.crops();
      this.bridge();
      const objects = [];
      for (let x = -6; x < 31; x++)
        for (let y = -6; y < 27; y++) {
          const edge = x < 0 || x > 23 || y < 0 || y > 19,
            forest = x < 6 && y < 7,
            riverbank = x > 20;
          if (
            x === 19 ||
            x === 12 ||
            y === 9 ||
            this.occupied?.has(`${x},${y}`) ||
            (x >= 1 && x <= 9 && y >= 11 && y <= 18) ||
            (x >= 9 && x <= 15 && y >= 4 && y <= 11)
          )
            continue;
          if (
            hash(x, y, 3) >
            (edge ? 0.35 : forest ? 0.3 : riverbank ? 0.72 : 0.91)
          )
            objects.push({
              depth: x + y,
              fn: () =>
                this.tree(
                  x + 0.5,
                  y + 0.5,
                  Math.floor(hash(x, y) * 100),
                  !edge && !forest,
                ),
            });
        }
      for (const b of this.state.buildings || [])
        objects.push({
          depth: b.x + b.y + 0.4,
          fn: () =>
            b.kind === "market"
              ? this.market(b)
              : b.kind === "mine"
                ? this.mine(b)
                : this.house(b),
        });
      objects.push({ depth: 23.7, fn: () => this.windmill() });
      for (const resident of this.state.citizens || []) {
        if (resident.alive === false) continue;
        const p = this.position(resident, now);
        objects.push({
          depth: p.x + p.y + 0.58,
          fn: () => this.resident(resident, now),
        });
      }
      objects.sort((a, b) => a.depth - b.depth).forEach((o) => o.fn());
      for (const b of this.state.buildings || []) {
        const selected =
          this.selected?.type === "building" &&
          String(this.selected.id) === String(b.id);
        if (
          selected ||
          (["council", "market", "farm", "mine"].includes(b.kind) &&
            this.scale > 0.7)
        ) {
          const title = selected
            ? b.name
            : {
                council: "Council square",
                market: "Marketplace",
                farm: "Sunfield farm",
                mine: "Copper Ridge",
              }[b.kind];
          this.label(
            title,
            b.x,
            b.y,
            this.elevation(b.x, b.y) +
              (b.kind === "council" ? 5 : b.kind === "mine" ? 2.5 : 2.3),
            selected,
          );
        }
      }
      if (
        this.flood ||
        String(this.state.weather).toLowerCase().includes("storm")
      ) {
        c.fillStyle = "#426c8928";
        c.fillRect(0, 0, this.width, this.height);
        c.strokeStyle = "#d5eef36b";
        c.lineWidth = 0.8;
        for (let i = 0; i < 65; i++) {
          const x = hash(i, 4) * this.width,
            y =
              (hash(i, 8) * this.height + (this.motion ? now * 0.22 : 0)) %
              this.height;
          c.beginPath();
          c.moveTo(x, y);
          c.lineTo(x - 5, y + 13);
          c.stroke();
        }
      }
      const v = c.createRadialGradient(
        this.width * 0.5,
        this.height * 0.45,
        this.height * 0.28,
        this.width * 0.5,
        this.height * 0.5,
        this.width * 0.8,
      );
      v.addColorStop(0, "#17392e00");
      v.addColorStop(1, "#17392e38");
      c.fillStyle = v;
      c.fillRect(0, 0, this.width, this.height);
      c.fillStyle = "#183c3dde";
      c.font = "500 10px system-ui,sans-serif";
      c.fillText(
        "LIVING DIORAMA  ·  Drag to explore  ·  Scroll to zoom",
        16,
        this.height - 15,
      );
    }
  }
  window.NewHavenWorld = NewHavenWorld;
})();
