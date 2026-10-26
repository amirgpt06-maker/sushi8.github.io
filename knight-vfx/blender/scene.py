"""Сцена Blender: Ти-Рекс + латы + копьё + кровь + ловцы теней; рендер слоёв в multilayer EXR.

Запуск: python scene.py work_dir out_dir [первый_кадр последний_кадр шаг процент_разрешения сэмплы]
Слои: trex (динозавр + тени на стене/полу), front (латы, копьё, брызги; динозавр — маска-holdout).
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
from armor import build_armor, build_spear, tube  # noqa: E402
from materials import mat_blood  # noqa: E402
from trex import build_trex  # noqa: E402

W, OUT = sys.argv[1], sys.argv[2]
F0, F1, STEP, PCT, SPP = (list(map(int, sys.argv[3:8])) + [0, 285, 1, 67, 24][len(sys.argv[3:8]):])
S = json.load(open(f"{W}/solve.json"))
G = json.load(open(f"{W}/rig.json"))
N = G["N"]
sc = bpy.context.scene
C = Matrix(((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))   # камера (y вниз, z вперёд) -> Blender
UNIT = G["shoulder_w"] / 0.36                                            # масштаб скелета MediaPipe к реальному

# --- камера, рендер ---
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.sensor_fit = "HORIZONTAL"
cam.data.sensor_width = 36
cam.data.lens = S["f"] / S["size"][0] * 36
cam.data.clip_start = 0.05
sc.render.resolution_x, sc.render.resolution_y = S["size"]
sc.render.resolution_percentage = PCT
sc.render.fps = 30
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPP
sc.cycles.adaptive_threshold = 0.05
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 4
sc.render.film_transparent = True
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.5
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
sc.render.image_settings.color_depth = "16"
sc.render.use_single_layer = False
sc.frame_start, sc.frame_end = 0, N - 1

# --- освещение комнаты: мягкий свет потолка/окон + процедурное окружение для отражений в стали ---
world = bpy.data.worlds.new("room")
sc.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord")
env_map = nt.nodes.new("ShaderNodeMapping")
env_map.vector_type = "VECTOR"
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(f"{W}/env.hdr")
nt.links.new(tc.outputs["Generated"], env_map.inputs["Vector"])
nt.links.new(env_map.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0


def light(name, loc, target, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = energy, size
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


# (координаты Blender: x вправо, y вверх, z к камере). Свет комнаты — сверху спереди и слева (окна).
light("ceiling", (0.3, 1.9, -1.2), (0.5, -0.5, -2.6), 90, 2.0)
light("window", (-2.5, 0.9, -1.0), (0.8, -0.2, -2.6), 220, 1.5)
light("rim", (2.6, 1.6, -4.6), (1.2, 0.2, -2.4), 90, 1.0)

# --- матрицы движения камеры: мир (кадр 0) -> текущая камера ---
Wm = []
for i in range(N):
    R = Matrix(S["cam_R"][i])
    t = Vector(S["cam_t"][i])
    M = Matrix.Identity(4)
    M.col[0][:3] = R.col[0]
    M.col[1][:3] = R.col[1]
    M.col[2][:3] = R.col[2]
    M.translation = t
    Wm.append(C @ M @ C)
P0 = lambda x, y, z: Vector((x, -y, -z))
RX90 = Matrix.Rotation(math.radians(90), 3, "X")
for i in range(N):
    env_map.inputs["Rotation"].default_value = (RX90 @ Wm[i].to_3x3().transposed()).to_euler("XYZ")
    env_map.inputs["Rotation"].keyframe_insert("default_value", frame=i)                                # точка «камеры кадра 0» -> Blender-мир


def key_matrix(ob, i, M):
    ob.matrix_world = M
    ob.keyframe_insert("location", frame=i)
    ob.keyframe_insert("rotation_quaternion", frame=i)
    ob.keyframe_insert("scale", frame=i)


def coll(name):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    return c


def move_to(ob, c):
    for u in list(ob.users_collection):
        u.objects.unlink(ob)
    c.objects.link(ob)
    for ch in ob.children:
        move_to(ch, c)


C_TREX, C_FRONT, C_SHADOW = coll("TREX"), coll("FRONT"), coll("SHADOW")

# ================= Ти-Рекс =================
L = 1.2 * UNIT
T = build_trex(L)
arm, ctrl, rest = T["arm"], T["ctrl"], T["rest"]
for ob in list(bpy.data.objects):
    if ob.name.startswith(("trex", "teeth")):
        move_to(ob, C_TREX)
# ориентация модели: морда (X модели) -> влево (−X Blender), верх (Z модели) -> +Y, бок (Y модели) -> +Z (к камере)
Q0 = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).to_quaternion()
hb = arm.data.bones["head"]
pivot_m = hb.head_local.copy()
throat_m = Vector((0.05 * L * 0.86, 0, -0.25 * L))
snout_m = Vector((1.03 * L * 0.86, 0, -0.01 * L))
ANCHOR = P0(2.45, -0.95, 1.95)          # основание шеи — за правым верхним краем кадра
rest.parent = None
ctrl.parent = None
for ob in (arm, ctrl):
    ob.rotation_mode = "QUATERNION"




def head_quat(yaw, pitch, roll):
    """yaw>0 — морда к камере, pitch>0 — морда вниз, roll — наклон."""
    qy = Quaternion(Vector((0, 1, 0)), math.radians(yaw))       # вокруг вертикали мира (Blender +Y)
    qp = Quaternion(Vector((0, 1, 0)), math.radians(pitch))     # вокруг бока модели (её +Y): морда вниз
    qr = Quaternion(Vector((1, 0, 0)), math.radians(roll))      # вокруг продольной оси модели
    return qy @ Q0 @ qp @ qr


# ключевые позы в координатах КАДРА: кадр: (центр головы u, v в пикселях 1920x1080, глубина), рыск, тангаж, крен, челюсть°
IKEYS = {
    0: ((2350, 380, 2.5), 10, 5, 0, 3), 14: ((2280, 380, 2.5), 10, 5, 0, 4),
    46: ((1660, 290, 2.50), 18, 8, -4, 9), 58: ((1670, 300, 2.50), 16, 6, 2, 6),
    66: ((1600, 250, 2.50), 14, -14, 6, 40), 74: ((1580, 260, 2.47), 16, -8, -7, 44),
    82: ((1590, 265, 2.47), 14, -6, 6, 40), 90: ((1620, 330, 2.50), 14, 5, 0, 10),
    102: ((1720, 330, 2.60), 15, 0, 0, 16), 108: ((1650, 340, 2.50), 16, 4, 0, 32),
    114: ((1270, 390, 2.40), 12, 10, 0, 4), 124: ((1550, 340, 2.50), 18, 2, 8, 10),
    136: ((1520, 360, 2.45), 18, 4, -3, 22), 142: ((1500, 360, 2.45), 18, 2, 0, 24),
    146: ((1640, 250, 2.50), 26, -16, 6, 26), 152: ((1700, 240, 2.55), 22, -8, 10, 18),
    166: ((1600, 220, 2.50), 18, -5, 0, 30), 184: ((1620, 190, 2.55), 18, -12, -3, 16),
    198: ((1300, 330, 2.36), 16, 24, 0, 36), 203: ((1260, 340, 2.35), 16, 26, 0, 36),
    207: ((1450, 290, 2.46), 36, 4, 22, 14), 214: ((1650, 300, 2.60), 22, -4, 6, 28),
    226: ((1580, 180, 2.55), 16, -24, -5, 40), 236: ((1600, 160, 2.58), 14, -30, 4, 46),
    244: ((1610, 160, 2.60), 15, -28, -4, 45), 250: ((1600, 180, 2.45), 18, 5, 0, 25),
    256: ((1520, 220, 2.25), 20, 24, 0, 38),
    268: ((1640, 210, 2.30), 20, -22, 16, 52), 276: ((1700, 200, 2.50), 18, -28, 18, 38),
    285: ((1800, 240, 2.70), 14, -10, 8, 20),
}
mid_m = (pivot_m + snout_m) / 2


def img_to_world(i, u, v, depth):
    cur = np.array([(u - 960) / S["f"] * depth, (v - 540) / S["f"] * depth, depth])
    return np.array(S["cam_R"][i]).T @ (cur - np.array(S["cam_t"][i]))


KEYS = {}
for fk, ((u, v, dep), yw, pt, rl, jw) in IKEYS.items():
    cw = img_to_world(fk, u, v, dep)
    pb_ = P0(*cw) - head_quat(yw, pt, rl) @ (mid_m - pivot_m)
    KEYS[fk] = ((pb_.x, -pb_.y, -pb_.z), yw, pt, rl, jw)
STRIKE = 261
# удар: горло (под задней частью челюсти) встречает копьё в кадре STRIKE
Rw = np.array(S["cam_R"][STRIKE])
tw = np.array(S["cam_t"][STRIKE])
sp = np.array(G["spear"][STRIKE])
d_cur = sp[:3, 1]
front_tip = np.array(G["spear_tip"][STRIKE])
entry_cur = front_tip - d_cur * 0.33
entry0 = Rw.T @ (entry_cur - tw)
d0 = Rw.T @ d_cur
S_YAW, S_PITCH, S_ROLL = -8, 40, 0
qs = head_quat(S_YAW, S_PITCH, S_ROLL)
piv_b = P0(*entry0) - qs @ (throat_m - pivot_m)
piv_c = (piv_b.x, -piv_b.y, -piv_b.z)
KEYS[STRIKE] = (piv_c, S_YAW, S_PITCH, S_ROLL, 40)
push = tuple(piv_c[k] + 0.04 * d0[k] for k in range(3))
KEYS[STRIKE + 3] = (push, S_YAW, S_PITCH + 2, 4, 44)
print("удар: вход копья (мир)", np.round(entry0, 2), "затылок", np.round(piv_c, 2))

fr = sorted(KEYS)


def interp(i):
    """Плавная интерполяция ключей (кубическая Эрмита / Catmull-Rom)."""
    if i <= fr[0]:
        return KEYS[fr[0]]
    if i >= fr[-1]:
        return KEYS[fr[-1]]
    k = max(j for j in range(len(fr)) if fr[j] <= i)
    a, b = fr[k], fr[k + 1]
    t = (i - a) / (b - a)
    pa, pb = fr[max(k - 1, 0)], fr[min(k + 2, len(fr) - 1)]

    def cr(v0, v1, v2, v3):
        t2, t3 = t * t, t * t * t
        return 0.5 * (2 * v1 + (-v0 + v2) * t + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2 + (-v0 + 3 * v1 - 3 * v2 + v3) * t3)

    K = [KEYS[x] for x in (pa, a, b, pb)]
    pos = tuple(cr(*(K[j][0][c] for j in range(4))) for c in range(3))
    rest_ = [cr(*(K[j][n] for j in range(4))) for n in range(1, 5)]
    return (pos, *rest_)


rnd = random.Random(7)
ROARS = [(64, 88, 1.0), (144, 156, 0.6), (206, 220, 0.8), (224, 250, 1.0), (262, 285, 1.2)]
for i in range(N):
    (x, y, z), yaw, pitch, roll, jaw = interp(i)
    # дыхание и мелкая тряска головы во время рёва
    br = math.sin(i / 30 * 2 * math.pi * 0.7)
    y += 0.006 * br
    for a, b, amp in ROARS:
        if a <= i <= b:
            env = math.sin(math.pi * (i - a) / (b - a))
            roll += amp * env * 5 * math.sin(i * 1.9)
            yaw += amp * env * 3 * math.sin(i * 2.7 + 1)
            jaw += amp * env * 3 * math.sin(i * 3.3)
    q = head_quat(yaw, pitch, roll)
    Mh = Matrix.Translation(P0(x, y, z)) @ q.to_matrix().to_4x4() @ hb.matrix_local.to_3x3().to_4x4()
    key_matrix(ctrl, i, Wm[i] @ Mh)
    # корень (основание шеи) немного «дышит» и следует за головой
    anc = ANCHOR + Vector((0.12 * (x - 2.0), 0.08 * -(y + 0.6), -0.10 * (z - 2.45)))
    Ma = Matrix.Translation(anc - Q0 @ arm.data.bones["neck1"].head_local) @ Q0.to_matrix().to_4x4()
    key_matrix(arm, i, Wm[i] @ Ma)
    pb = arm.pose.bones["jaw"]
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion(Vector((1, 0, 0)), -math.radians(max(0, jaw)))
    pb.keyframe_insert("rotation_quaternion", frame=i)

# ================= латы (по желанию) и копьё =================
s = UNIT
ARMOR = os.environ.get("ARMOR", "0") == "1"
C_BODY = coll("BODY")
if ARMOR:
    P = build_armor(G["shoulder_w"] / s, G["torso_ref"] / s, G["head_w"] / s,
                    G["uarm_ref"] / s, G["farm_ref"] / s, G["thigh_ref"] / s, G["shin_ref"] / s)
else:
    # без лат: невидимые «тела-маски» по скелету — прячут части копья, проходящие за человеком
    hold = bpy.data.materials.new("body_holdout")
    hold.use_nodes = True
    hold.node_tree.nodes.clear()
    _o = hold.node_tree.nodes.new("ShaderNodeOutputMaterial")
    _h = hold.node_tree.nodes.new("ShaderNodeHoldout")
    hold.node_tree.links.new(_h.outputs[0], _o.inputs["Surface"])
    tl_r, ua, fa, th = G["torso_ref"] / s, G["uarm_ref"] / s, G["farm_ref"] / s, G["thigh_ref"] / s
    P = {"torso": [tube("proxy_torso", [(0.03, 0.15, 0.09, 0, 0, 0), (-0.25 * tl_r, 0.17, 0.11, 0, 0.01, 0),
                                        (-tl_r * 1.05, 0.16, 0.10, 0, 0, 0)], hold, closed_top=True, closed_bot=True, thick=0, sub=1)]}
    for sd_ in ("L", "R"):
        P[f"uarm_{sd_}"] = [tube(f"proxy_uarm_{sd_}", [(0.0, 0.045, 0.045, 0, 0, 0), (ua, 0.04, 0.04, 0, 0, 0)], hold, True, True, 0, 1)]
        P[f"farm_{sd_}"] = [tube(f"proxy_farm_{sd_}", [(0.0, 0.038, 0.038, 0, 0, 0), (fa * 0.95, 0.03, 0.03, 0, 0, 0)], hold, True, True, 0, 1)]
        P[f"thigh_{sd_}"] = [tube(f"proxy_thigh_{sd_}", [(0.0, 0.07, 0.07, 0, 0, 0), (th, 0.055, 0.055, 0, 0, 0)], hold, True, True, 0, 1)]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
    hp_ = bpy.context.active_object
    hp_.name = "proxy_head"
    hp_.scale = (0.075, 0.105, 0.095)
    hp_.location = (0, 0.03, 0)
    bpy.ops.object.transform_apply(location=True, scale=True)
    hp_.data.materials.append(hold)
    P["head"] = [hp_]
spear, blade = build_spear(2.3 / s)
bl = blade.copy()
bl.data = blade.data.copy()
bl.name = "blade_blood"
bpy.context.scene.collection.objects.link(bl)
bl.data.materials.clear()
bl.data.materials.append(mat_blood())
so = bl.modifiers.new("solid", "SOLIDIFY")
so.thickness, so.offset = 0.0015, 1
spear.append(bl)
pieces = []
for bone, obs in P.items():
    for ob in obs:
        pieces.append((bone, ob))
for ob in spear:
    pieces.append(("spear", ob))
for bone, ob in pieces:
    ob.rotation_mode = "QUATERNION"
    move_to(ob, C_FRONT if (ARMOR or bone == "spear") else C_BODY)
    for i in range(N):
        M = Matrix(G[bone][i]) @ Matrix.Diagonal((s, s, s, 1))
        key_matrix(ob, i, C @ M)

# кровь на наконечнике после удара
bl.hide_render = True
bl.keyframe_insert("hide_render", frame=STRIKE - 1)
bl.hide_render = False
bl.keyframe_insert("hide_render", frame=STRIKE + 1)

# ================= брызги крови =================
blood = mat_blood()
drops = []
rng = np.random.default_rng(3)
g0 = np.array([0, 9.8 * 0.73, 0])          # гравитация (камера кадра 0: y вниз), в «единицах» сцены
for k in range(70):
    t0 = STRIKE + 1 + rng.integers(0, 9)
    v = (-d0 * rng.uniform(0.3, 1.3) + rng.normal(0, 0.7, 3) + np.array([0, -0.4, 0])) * UNIT
    r = rng.uniform(0.004, 0.012) * UNIT
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=r)
    o = bpy.context.active_object
    o.name = f"drop{k}"
    o.data.materials.append(blood)
    o.rotation_mode = "QUATERNION"
    move_to(o, C_FRONT)
    for i in [0] + list(range(STRIKE - 1, N)):
        tt = (i - t0) / 30
        if tt < 0:
            p, scl = entry0, 0.0
        else:
            p = entry0 + v * tt + 0.5 * g0 * tt * tt
            scl = 1.0 if p[1] < 1.1 else 0.0
        stretch = 1.0 + 1.5 * min(1.0, max(0.0, 1 - tt * 4)) if tt >= 0 else 1.0
        M = Matrix.Translation(P0(*p)) @ Matrix.Diagonal((scl * stretch, scl, scl, 1))
        key_matrix(o, i, Wm[i] @ M)
    drops.append(o)

# рана: тёмное блестящее пятно в точке входа, привязано к кости головы
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.05 * UNIT)
wound = bpy.context.active_object
wound.name = "trex_wound"
wound.scale = (1.0, 0.35, 1.0)
wound.data.materials.append(blood)
move_to(wound, C_TREX)

# ================= ловцы теней: стена позади и пол =================
for name, loc, rot, size in (("wall", P0(1.2, -0.2, 3.4), (0, 0, 0), (7, 4)), ("floor", P0(1.2, 1.12, 2.4), (-math.pi / 2, 0, 0), (7, 5))):
    bpy.ops.mesh.primitive_plane_add(size=1)
    pl = bpy.context.active_object
    pl.name = name
    pl.scale = (*size, 1)
    pl.is_shadow_catcher = True
    pl.rotation_mode = "QUATERNION"
    move_to(pl, C_SHADOW)
    Mp = Matrix.Translation(loc) @ Matrix.Rotation(rot[0], 4, "X") @ Matrix.Diagonal((*size, 1, 1))
    for i in range(N):
        key_matrix(pl, i, Wm[i] @ Mp)

# рана: позиция по кости головы — считаем по кадрам после решения IK
inv_head_at_strike = None
for i in range(N):
    sc.frame_set(i)
    hm = arm.matrix_world @ arm.pose.bones["head"].matrix
    if i == STRIKE:
        # точка входа в системе кости головы
        local_entry = hm.inverted() @ (Wm[i] @ P0(*entry0).to_4d()).to_3d()
        break
for i in range(N):
    sc.frame_set(i)
    hm = arm.matrix_world @ arm.pose.bones["head"].matrix
    scl = 0.0 if i < STRIKE else min(1.0, (i - STRIKE + 1) / 4)
    M = Matrix.Translation(hm @ local_entry) @ hm.to_quaternion().to_matrix().to_4x4() @ Matrix.Diagonal((scl, scl * 0.35, scl, 1))
    wound.rotation_mode = "QUATERNION"
    key_matrix(wound, i, M)

# ================= слои =================
vl_t = sc.view_layers[0]
vl_t.name = "trex"
vl_f = sc.view_layers.new("front")
vl_s = sc.view_layers.new("spear_full")
for vl in (vl_t, vl_f, vl_s):
    vl.cycles.use_pass_shadow_catcher = True
lc = {c.name: c for c in vl_t.layer_collection.children}
lc["FRONT"].exclude = True
lc["BODY"].exclude = True
lc = {c.name: c for c in vl_f.layer_collection.children}
lc["TREX"].holdout = True
lc["BODY"].holdout = True
lc["SHADOW"].exclude = True
# копьё целиком (без масок тела): в композитинге части «за телом» вне силуэта человека берутся отсюда
lc = {c.name: c for c in vl_s.layer_collection.children}
lc["TREX"].holdout = True
lc["BODY"].exclude = True
lc["SHADOW"].exclude = True

bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/scene.blend")
os.makedirs(f"{OUT}/exr", exist_ok=True)
for i in range(F0, F1 + 1, STEP):
    sc.frame_set(i)
    sc.render.filepath = f"{OUT}/exr/{i:04d}.exr"
    bpy.ops.render.render(write_still=True)
    print("рендер", i, flush=True)
