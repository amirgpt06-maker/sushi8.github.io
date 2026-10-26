"""Процедурные латы и копьё. Каждая деталь строится в локальной системе своей «кости» (Y вдоль кости)
и потом каждый кадр получает матрицу кости (см. rig.py).

Оси: торс — X влево от человека, Y вверх, Z вперёд; конечности — Y от сустава к суставу, X — влево торса;
голова — X влево, Y вверх, Z вперёд (к носу).
"""
import math

import bmesh
import bpy
from mathutils import Vector

from materials import mat_blood, mat_leather, mat_steel, mat_wood

NS = 48


def tube(name, sections, mat, closed_top=False, closed_bot=False, thick=0.004, sub=2):
    """sections: [(y, a, b, cx, cz, ridge)] — эллипс с полуосями a (по X) и b (по Z), центр (cx, cz),
    ridge — гребень спереди (+Z)."""
    bm = bmesh.new()
    rings = []
    for y, a, b, cx, cz, ridge in sections:
        r = []
        for k in range(NS):
            t = 2 * math.pi * k / NS
            x, z = a * math.cos(t), b * math.sin(t)
            z += ridge * math.exp(-(math.cos(t) / 0.22) ** 2) * (math.sin(t) > 0)
            r.append(bm.verts.new((cx + x, y, cz + z)))
        rings.append(r)
    for r1, r2 in zip(rings, rings[1:]):
        for k in range(NS):
            bm.faces.new((r1[k], r1[(k + 1) % NS], r2[(k + 1) % NS], r2[k]))
    if closed_top:
        bm.faces.new(rings[0])
    if closed_bot:
        bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    if thick:
        so = ob.modifiers.new("solid", "SOLIDIFY")
        so.thickness = thick
        so.offset = 1
        so.use_even_offset = True
    sd = ob.modifiers.new("subd", "SUBSURF")
    sd.levels, sd.render_levels = 1, sub
    return ob


def dome(name, R, y0, ystop, mat, ax=1.0, cx=0.0, lames=()):
    """Купол (наплечник/налокотник): сфера радиуса R, центр по Y в y0, обращена к −Y; снизу — пластины-ламы."""
    secs = []
    n = 14
    for i in range(n + 1):
        ang = math.pi / 2 * i / n                    # от вершины (−Y) к экватору
        y = y0 - R * math.cos(ang)
        rr = max(R * math.sin(ang), 0.003)
        secs.append((y, rr * ax, rr, cx, 0.0, 0.0))
    secs.append((ystop, R * 0.97 * ax, R * 0.97, cx, 0, 0))
    obs = [tube(name, secs, mat, thick=0.004)]
    for j, (ya, yb, ra, rb) in enumerate(lames):
        obs.append(tube(f"{name}_lame{j}", [(ya, ra * ax, ra, cx, 0, 0), (yb, rb * ax, rb, cx, 0, 0)], mat, thick=0.003))
    return obs


def join(obs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    # модификаторы должны остаться на каждой детали: применяем перед объединением
    for o in obs:
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def build_armor(sw, tl, head_w, ua=0.28, fa=0.25, th=0.40, sh=0.40):
    """sw — ширина плеч (м), tl — длина торса (плечи→таз), head_w — расстояние между ушами."""
    steel = mat_steel("steel", (0.46, 0.46, 0.47), 0.27)
    dark = mat_steel("steel_dark", (0.16, 0.16, 0.17), 0.45)
    leather = mat_leather()
    P = {}

    # --- кираса (нагрудник + спина) с набедренными пластинами (фолд) ---
    a0 = sw * 0.50
    secs = []
    for i in range(23):
        k = i / 22
        y = 0.04 - k * tl * 0.92
        a = a0 * (1.0 - 0.18 * math.sin(math.pi * min(k / 0.85, 1)) - 0.08 * k) + 0.012 * math.exp(-((k - 0.25) / 0.2) ** 2)
        b = 0.100 + 0.030 * math.exp(-((k - 0.30) / 0.25) ** 2) - 0.02 * k
        cz = 0.012 + 0.03 * math.exp(-((k - 0.32) / 0.22) ** 2)
        if k < 0.08:  # горловина уже
            a *= 0.80 + 2.5 * k
            b *= 0.85 + 1.8 * k
        secs.append((y, a, b, 0, cz, 0.010 * (1 - k)))
    cuir = tube("cuirass", secs, steel, thick=0.004)
    fauld = []
    for j in range(3):
        y1 = 0.05 - tl * (0.96 + 0.075 * j)
        y2 = y1 - tl * 0.095
        a1 = a0 * (0.78 + 0.045 * j)
        fauld.append(tube(f"fauld{j}", [(y1, a1, 0.112 + 0.008 * j, 0, 0.01, 0), (y2, a1 * 1.06, 0.122 + 0.008 * j, 0, 0.012, 0)],
                          steel, thick=0.003))
    gorget = tube("gorget", [(0.06, 0.064, 0.060, 0, 0.0, 0), (0.04, 0.074, 0.068, 0, 0.004, 0),
                             (0.02, sw * 0.30, 0.095, 0, 0.008, 0)], steel, thick=0.003)
    belt = tube("belt", [(0.05 - tl * 0.80, a0 * 0.86, 0.118, 0, 0.012, 0), (0.05 - tl * 0.86, a0 * 0.86, 0.118, 0, 0.012, 0)],
                leather, thick=0.006)
    P["torso"] = [cuir, gorget, belt] + fauld

    # --- руки ---
    for s, sgn in (("L", 1), ("R", -1)):
        P[f"uarm_{s}"] = dome(f"pauldron_{s}", 0.105, 0.03, 0.06, steel, ax=1.12, cx=0.035 * sgn,
                              lames=[(0.05, 0.085, 0.10, 0.092), (0.08, 0.115, 0.092, 0.084)]) + [
            tube(f"rerebrace_{s}", [(0.12, 0.054, 0.052, 0, 0, 0), (ua * 0.86, 0.050, 0.048, 0, 0, 0)], steel, thick=0.003)]
        P[f"farm_{s}"] = dome(f"couter_{s}", 0.058, 0.02, 0.03, steel, ax=1.0) + [
            tube(f"vambrace_{s}", [(0.05, 0.049, 0.045, 0, 0, 0), (fa * 0.76, 0.045, 0.040, 0, 0, 0)], steel, thick=0.003),
            tube(f"cuff_{s}", [(fa * 0.78, 0.046, 0.042, 0, 0, 0), (fa * 1.0, 0.060, 0.055, 0, 0, 0)], steel, thick=0.003)]
        P[f"thigh_{s}"] = [tube(f"cuisse_{s}", [(0.05, 0.088, 0.085, 0, -0.005, 0), (th * 0.86, 0.074, 0.070, 0, -0.005, 0)],
                                steel, thick=0.003)]
        P[f"shin_{s}"] = dome(f"poleyn_{s}", 0.062, 0.03, 0.04, steel) + [
            tube(f"greave_{s}", [(0.06, 0.060, 0.058, 0, 0, 0), (sh * 0.92, 0.045, 0.043, 0, 0, 0)], steel, thick=0.003)]

    # --- шлем: открытый бацинет с наносником + кольчужная бармица ---
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    hel = bpy.context.active_object
    hel.name = "helmet"
    ra, rb, rc = head_w * 0.55 + 0.03, 0.128, 0.128
    bm = bmesh.new()
    bm.from_mesh(hel.data)
    dead = []
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((x * ra, y * rb + 0.045 + 0.012 * max(0, y) ** 8, z * rc - 0.012))  # слегка заострённая макушка
        X, Yv, Z = v.co
        if (Z > 0.035 and Yv < 0.075) or Yv < -0.115 or (Z > -0.02 and Yv < -0.02):
            dead.append(v)
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    bm.to_mesh(hel.data)
    bm.free()
    hel.data.materials.append(steel)
    bpy.ops.object.shade_smooth()
    so = hel.modifiers.new("solid", "SOLIDIFY")
    so.thickness, so.offset = 0.004, 1
    sd = hel.modifiers.new("subd", "SUBSURF")
    sd.levels, sd.render_levels = 1, 2
    nasal = tube("nasal", [(0.085, 0.012, 0.004, 0, rc - 0.005, 0), (-0.02, 0.010, 0.004, 0, rc + 0.012, 0)], steel, thick=0.003)
    mail = tube("aventail", [(-0.07, ra * 0.97, rc * 0.97, 0, -0.012, 0), (-0.13, ra * 1.08, rc * 1.02, 0, -0.01, 0),
                             (-0.19, ra * 1.30, rc * 1.15, 0, 0.0, 0)], dark, thick=0.005)
    # «дырка» для лица: невидимый объект-holdout, вырезает изнанку шлема, лицо из видео остаётся видно
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
    face = bpy.context.active_object
    face.name = "face_holdout"
    face.scale = (0.060, 0.085, 0.05)
    face.location = (0, -0.005, rc - 0.055)
    bpy.ops.object.transform_apply(location=True, scale=True)
    hm = bpy.data.materials.new("holdout")
    hm.use_nodes = True
    hm.node_tree.nodes.clear()
    o = hm.node_tree.nodes.new("ShaderNodeOutputMaterial")
    hn = hm.node_tree.nodes.new("ShaderNodeHoldout")
    hm.node_tree.links.new(hn.outputs[0], o.inputs["Surface"])
    face.data.materials.append(hm)
    P["head"] = [hel, nasal, mail, face]
    return P


def build_spear(length=2.3):
    wood, steel, leather, blood = mat_wood(), mat_steel("spear_steel", (0.7, 0.7, 0.72), 0.2), mat_leather((0.06, 0.035, 0.02)), mat_blood()
    shaft = tube("spear_shaft", [(0.0, 0.016, 0.016, 0, 0, 0), (length - 0.33, 0.017, 0.017, 0, 0, 0)], wood, closed_top=True,
                 thick=0, sub=1)
    wrap = tube("spear_wrap", [(length * 0.42, 0.0185, 0.0185, 0, 0, 0), (length * 0.62, 0.0185, 0.0185, 0, 0, 0)], leather,
                thick=0, sub=1)
    sock = tube("spear_socket", [(length - 0.36, 0.019, 0.019, 0, 0, 0), (length - 0.24, 0.013, 0.013, 0, 0, 0)], steel, thick=0, sub=1)
    # листовидный наконечник: ромбическое сечение, ширина по длине
    secs = []
    for i in range(16):
        k = i / 15
        y = length - 0.25 + k * 0.25
        w = 0.042 * math.sin(math.pi * min(1, k / 0.92) ** 0.8) * (1 - k ** 3) + 0.0015
        secs.append((y, w, 0.006 * (1 - k) + 0.0012, 0, 0, 0))
    blade = tube("spear_blade", secs, steel, closed_bot=True, thick=0, sub=2)
    blade.data.materials.append(blood)
    P = [shaft, wrap, sock, blade]
    return P, blade
