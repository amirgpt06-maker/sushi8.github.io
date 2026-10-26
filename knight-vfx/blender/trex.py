"""Процедурный Ти-Рекс для Blender (bpy): голова + шея, нижняя челюсть, зубы, глаза, язык, риг с IK шеи.

build_trex(L) -> dict(arm=арматура, ctrl=контроллер головы, jaw=имя кости челюсти, root=корень)
Локальные оси модели: X вперёд (к морде), Y влево, Z вверх. L — длина черепа в метрах.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from materials import mat_eye, mat_mouth, mat_skin, mat_teeth


def lerp_table(tab, x):
    xs = [t[0] for t in tab]
    if x >= xs[0]:
        return tab[0][1:]
    if x <= xs[-1]:
        return tab[-1][1:]
    for a, b in zip(tab, tab[1:]):
        if a[0] >= x >= b[0]:
            k = (x - a[0]) / (b[0] - a[0])
            # сглаженная интерполяция (без «граней» между сечениями)
            k = k * k * (3 - 2 * k)
            return [u + (v - u) * k for u, v in zip(a[1:], b[1:])]


# Профиль черепа (в долях длины): x, верх, линия зубов, полуширина, «щёки» (доп. ширина внизу)
SKULL = [
    (1.03, 0.040, -0.050, 0.055, 0.00),
    (1.00, 0.115, -0.072, 0.082, 0.00),
    (0.95, 0.165, -0.088, 0.108, 0.00),
    (0.86, 0.212, -0.098, 0.130, 0.00),
    (0.74, 0.245, -0.102, 0.148, 0.01),
    (0.60, 0.270, -0.102, 0.165, 0.02),
    (0.47, 0.292, -0.099, 0.200, 0.03),
    (0.36, 0.318, -0.093, 0.235, 0.05),
    (0.25, 0.338, -0.085, 0.290, 0.09),
    (0.14, 0.345, -0.072, 0.335, 0.17),
    (0.04, 0.322, -0.045, 0.335, 0.16),
    (-0.05, 0.285, -0.030, 0.290, 0.05),
    (-0.12, 0.265, -0.030, 0.275, 0.03),
]
# Нижняя челюсть: x, верх (кромка), низ, полуширина
JAW = [
    (1.00, -0.065, -0.115, 0.070),
    (0.94, -0.080, -0.150, 0.105),
    (0.82, -0.090, -0.170, 0.125),
    (0.66, -0.095, -0.185, 0.140),
    (0.50, -0.097, -0.200, 0.158),
    (0.34, -0.094, -0.222, 0.192),
    (0.20, -0.086, -0.240, 0.240),
    (0.08, -0.060, -0.235, 0.275),
    (-0.02, -0.025, -0.170, 0.270),
]
NR = 64  # точек в сечении
SX = 0.86  # укорочение морды по длине


def section_upper(x, L):
    top, bot, hw, cheek = lerp_table(SKULL, x)
    pts = []
    zc, hh = (top + bot) / 2, (top - bot) / 2
    for k in range(NR):
        a = 2 * math.pi * k / NR          # 0 = сбоку справа (−Y), против часовой
        c, s = math.cos(a), math.sin(a)
        up = s >= 0
        ex = 3.0 if up else 5.0            # верх угловатый, низ плоский (нёбо)
        y = -hw * math.copysign(abs(c) ** (2 / ex), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / ex), s)
        if not up:
            y *= 1 + cheek * 4 * abs(s)
        # надбровные гребни и рога над глазами
        bx = math.exp(-((x - 0.36) / 0.06) ** 2)
        side = abs(c)
        if up:
            z += 0.075 * bx * math.exp(-((side - 0.62) / 0.13) ** 2)
            z += 0.04 * math.exp(-((x - 0.20) / 0.07) ** 2) * math.exp(-((side - 0.80) / 0.13) ** 2)
            z += 0.012 * math.exp(-((side - 0.30) / 0.12) ** 2) * (0.5 + 0.5 * math.sin(x * 70)) * (x > 0.45)
        # глазница
        ex_ = math.exp(-((x - 0.31) / 0.045) ** 2) * math.exp(-((s - 0.35) / 0.18) ** 2) * (side > 0.6)
        y *= 1 - 0.10 * ex_
        # ноздри
        nx = math.exp(-((x - 0.93) / 0.025) ** 2) * math.exp(-((s - 0.55) / 0.15) ** 2)
        y *= 1 - 0.18 * nx
        # предглазничное окно — лёгкая впадина сбоку
        fx = math.exp(-((x - 0.62) / 0.09) ** 2) * math.exp(-((s - 0.05) / 0.25) ** 2)
        y *= 1 - 0.05 * fx
        pts.append(Vector((x * L * SX, y * L, z * L)))
    return pts


def section_jaw(x, L):
    top, bot, hw = lerp_table(JAW, x)
    zc, hh = (top + bot) / 2, (top - bot) / 2
    pts = []
    for k in range(NR):
        a = 2 * math.pi * k / NR
        c, s = math.cos(a), math.sin(a)
        ex = 5.0 if s >= 0 else 2.6        # верх (дно рта) плоский, низ округлый
        y = -hw * math.copysign(abs(c) ** (2 / ex), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / ex), s)
        pts.append(Vector((x * L * SX, y * L, z * L)))
    return pts


def loft(name, rings, mouth_test=None, cap_start=True, cap_end=True):
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vr, vr[1:]):
        for k in range(NR):
            bm.faces.new((a[k], a[(k + 1) % NR], b[(k + 1) % NR], b[k]))
    if cap_start:
        bm.faces.new(list(reversed(vr[0])))
    if cap_end:
        bm.faces.new(vr[-1])
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    if mouth_test:
        for p in me.polygons:
            p.material_index = 1 if mouth_test(p.center, p.normal) else 0
    return ob


def neck_rings(L, spine, radii):
    """Шея вдоль ломаной spine (точки), сечения-эллипсы (ширина, высота, смещение вниз)."""
    rings = []
    for i, c in enumerate(spine):
        t = (spine[min(i + 1, len(spine) - 1)] - spine[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        rw, rh, dz = radii[i]
        ring = []
        for k in range(NR):
            a = 2 * math.pi * k / NR
            c, s = math.cos(a), math.sin(a)
            ex = 2.2
            y = rw * math.copysign(abs(c) ** (2 / ex), c)
            z = rh * math.copysign(abs(s) ** (2 / ex), s) - dz
            ring.append(spine[i] + side * (-y) + up * z)
        rings.append(ring)
    return rings


def add_teeth(L, parent_arm, bone, upper, mat):
    tab = SKULL if upper else JAW
    xs = [0.95 - i * 0.092 for i in range(9 if upper else 8)]
    obs = []
    for side in (-1, 1):
        for i, x in enumerate(xs):
            if upper:
                top, bot, hw, cheek = lerp_table(SKULL, x)
                z, y = bot, hw * 0.80
            else:
                top, bot, hw = lerp_table(JAW, x)
                z, y = top, hw * 0.66
            size = (0.034 + 0.045 * math.sin(math.pi * min(1, (0.99 - x) / 0.70))) * (1.0 if upper else 0.62)
            size *= 0.55 + 0.7 * ((i * 37 + (side + 1) * 11) % 7) / 7
            if (i * 13 + side * 5) % 9 == 4:
                continue
            bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=size * 0.40 * L, radius2=0.0, depth=size * L,
                                            location=(0, 0, 0))
            t = bpy.context.active_object
            t.name = f"tooth_{'u' if upper else 'l'}{i}{side}"
            # кривой зуб: изгиб назад, кончик вниз (верхние) / вверх (нижние)
            bm = bmesh.new()
            bm.from_mesh(t.data)
            for v in bm.verts:
                h = (v.co.z / (size * L) + 0.5)
                v.co.x -= 0.25 * size * L * h * h
                v.co.y *= 0.75
            bm.to_mesh(t.data)
            bm.free()
            sign = -1 if upper else 1
            t.rotation_euler = (0.12 * ((i * 7) % 5 - 2) / 2, (math.pi if upper else 0) + 0.10 * ((i * 11) % 5 - 2) / 2, 0)
            t.location = (x * L * SX, side * y * L, (z + sign * 0.22 * size) * L)
            t.data.materials.append(mat)
            for p in t.data.polygons:
                p.use_smooth = True
            obs.append(t)
    bpy.ops.object.select_all(action="DESELECT")
    for t in obs:
        t.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    teeth = bpy.context.active_object
    teeth.name = "teeth_upper" if upper else "teeth_lower"
    return teeth


def parent_to_bone(ob, arm, bone):
    mw = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


def build_trex(L=1.1):
    mouth, teeth_m, eye_m = mat_mouth(), mat_teeth(), mat_eye()

    # --- голова + шея одной сеткой: череп (от морды к затылку), затем шея назад-вниз к туловищу ---
    xs = [1.03 - i * 0.01 for i in range(116)]                    # 1.03 .. -0.12
    rings = [section_upper(x, L) for x in xs]
    # шея: из затылка (-0.08) назад, вниз и чуть в сторону; затем к груди
    spine = [Vector((-0.12 * L * SX - i * 0.07, 0, 0.12 * L + 0.46 * (i / 16) ** 0.85 - 0.10 * (i / 16) ** 3)) for i in range(1, 17)]
    radii = []
    for i in range(1, 17):
        k = i / 16
        rw = (0.25 + 0.28 * k ** 1.2) * L
        rh = (0.17 + 0.40 * k ** 1.1) * L
        radii.append((rw, rh, (0.0 + 0.16 * k) * L))
    rings += neck_rings(L, spine, radii)
    head = loft("trex_head", rings,
                mouth_test=lambda c, n: (c.x > 0.04 * L * SX) and (c.x < 0.99 * L * SX) and n.z < -0.6 and abs(c.y) < 0.75 * lerp_table(SKULL, c.x / (L * SX))[2] * L,
                cap_start=True, cap_end=True)
    head.data.materials.append(mat_skin(tuple(head.dimensions)))
    head.data.materials.append(mouth)
    head_len = len(xs)

    jaw = loft("trex_jaw", [section_jaw(1.00 - i * 0.01, L) for i in range(103)],
               mouth_test=lambda c, n: n.z > 0.6 and c.x > 0.02 * L * SX)
    jaw.data.materials.append(mat_skin(tuple(jaw.dimensions)))
    jaw.data.materials.append(mouth)

    # язык
    tongue = loft("trex_tongue", [[Vector((x * L * SX, -0.09 * L * math.cos(2 * math.pi * k / NR) * (1 - (x - 0.2) * 0.9),
                                            (-0.085 + 0.018 * math.sin(2 * math.pi * k / NR)) * L)) for k in range(NR)]
                                  for x in [0.75 - i * 0.05 for i in range(12)]])
    tongue.data.materials.append(mouth)

    # глаза
    eyes = []
    for side in (-1, 1):
        x, z = 0.31, 0.245
        hw = lerp_table(SKULL, x)[2]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.024 * L,
                                             location=(x * L * SX, side * hw * 0.70 * L, z * L))
        e = bpy.context.active_object
        e.name = f"trex_eye{side}"
        e.rotation_euler = (0, 0, math.radians(90 * side) + math.radians(-15 * side))
        e.data.materials.append(eye_m)
        bpy.ops.object.shade_smooth()
        eyes.append(e)

    # --- арматура: root -> neck1..neck4 -> head -> jaw ---
    arm_data = bpy.data.armatures.new("trex_rig")
    arm = bpy.data.objects.new("trex_rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    pts = [spine[-1], spine[12], spine[8], spine[4], spine[0], Vector((-0.06 * L * SX, 0, 0.14 * L))]
    names = ["neck1", "neck2", "neck3", "neck4", "neck5"]
    prev = None
    for n, (a, b) in zip(names, zip(pts, pts[1:])):
        bn = eb.new(n)
        bn.head, bn.tail = a, b
        bn.roll = 0
        if prev:
            bn.parent = prev
            bn.use_connect = True
        prev = bn
    hb = eb.new("head")
    hb.head, hb.tail = pts[-1], Vector((0.6 * L * SX, 0, 0.14 * L))
    hb.parent = prev
    hb.use_connect = True
    jb = eb.new("jaw")
    jb.head, jb.tail = Vector((0.02 * L * SX, 0, -0.03 * L)), Vector((0.5 * L * SX, 0, -0.06 * L))
    jb.parent = hb
    bpy.ops.object.mode_set(mode="OBJECT")

    # веса головы/шеи по номеру сечения
    head.parent = arm
    mod = head.modifiers.new("arm", "ARMATURE")
    mod.object = arm
    groups = {n: head.vertex_groups.new(name=n) for n in names + ["head"]}
    bone_s = [(n, b.head_local, b.tail_local) for n, b in ((n, arm_data.bones[n]) for n in names + ["head"])]
    for v in head.data.vertices:
        ring = v.index // NR
        if ring < head_len - 6:
            groups["head"].add([v.index], 1.0, "REPLACE")
            continue
        # расстояние до каждой кости шеи -> плавные веса
        ws = []
        for n, a, b in bone_s:
            ab = b - a
            t = max(0, min(1, (v.co - a).dot(ab) / ab.length_squared))
            d = (v.co - (a + ab * t)).length
            ws.append((n, math.exp(-(d / (0.35 * L)) ** 2 * 3)))
        # учитываем только продольное положение
        tot = sum(w for _, w in ws) or 1
        for n, w in ws:
            if w / tot > 0.02:
                groups[n].add([v.index], w / tot, "REPLACE")
    for ob in [jaw, tongue]:
        parent_to_bone(ob, arm, "jaw")
    for ob in eyes:
        parent_to_bone(ob, arm, "head")
    tu = add_teeth(L, arm, "head", True, teeth_m)
    parent_to_bone(tu, arm, "head")
    tl = add_teeth(L, arm, "jaw", False, teeth_m)
    parent_to_bone(tl, arm, "jaw")

    # субдивизия + крупные морщины/бугры геометрией
    for ob in (head, jaw):
        sd = ob.modifiers.new("subd", "SUBSURF")
        sd.levels, sd.render_levels = 1, 2
        tex = bpy.data.textures.new(ob.name + "_bumps", "VORONOI")
        tex.noise_scale = 0.06
        tex.distance_metric = "DISTANCE"
        dm = ob.modifiers.new("bumps", "DISPLACE")
        dm.texture = tex
        dm.texture_coords = "LOCAL"
        dm.strength = 0.006
        dm.mid_level = 0.5
        ob.modifiers.move(ob.modifiers.find("bumps"), len(ob.modifiers) - 1)
        tx2 = bpy.data.textures.new(ob.name + "_lumps", "CLOUDS")
        tx2.noise_scale = 0.05 * L
        tx2.noise_depth = 4
        d2 = ob.modifiers.new("lumps", "DISPLACE")
        d2.texture = tx2
        d2.texture_coords = "LOCAL"
        d2.strength = 0.018 * L
        d2.mid_level = 0.5
    # порядок у головы: арматура -> subd -> bumps
    head.modifiers.move(head.modifiers.find("arm"), 0)

    # контроллер головы: rest = ориентация кости head; IK шеи тянет затылок к контроллеру
    rest = bpy.data.objects.new("trex_head_rest", None)
    bpy.context.scene.collection.objects.link(rest)
    rest.parent = arm
    rest.matrix_parent_inverse = Matrix.Identity(4)
    rest.matrix_basis = arm_data.bones["head"].matrix_local.copy()
    ctrl = bpy.data.objects.new("trex_head_ctrl", None)
    bpy.context.scene.collection.objects.link(ctrl)
    ctrl.parent = rest
    ctrl.empty_display_size = 0.2
    pb = arm.pose.bones
    ik = pb["neck5"].constraints.new("IK")
    ik.target = ctrl
    ik.chain_count = 5
    ik.use_tail = True
    for n in names:
        pb[n].ik_stretch = 0.02
    cr = pb["head"].constraints.new("COPY_ROTATION")
    cr.target = ctrl
    return {"arm": arm, "ctrl": ctrl, "rest": rest, "head": head, "jaw_bone": "jaw", "L": L}
