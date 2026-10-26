"""Материалы Cycles: кожа рептилии, рот, зубы, глаз, сталь доспехов, дерево древка, кожа (оплётка), кровь."""
import bpy


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bs


def _n(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        if k.startswith("in_"):
            n.inputs[k[3:].replace("_", " ")].default_value = v
        else:
            setattr(n, k, v)
    return n


def _ramp(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) > 2:
        els.remove(els[-1])
    for i, (pos, col) in enumerate(stops):
        e = els[i] if i < 2 else els.new(pos)
        e.position = pos
        e.color = (*col, 1) if len(col) == 3 else col
    return r


def coords_meters(nt, dims=(1, 1, 1)):
    """Координаты недеформированной сетки (Generated) в метрах: текстура «прилипает» к коже при сгибании шеи."""
    tc = _n(nt, "ShaderNodeTexCoord")
    mp = _n(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = dims
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    return mp.outputs["Vector"], tc


def mat_skin(dims=(3.0, 0.8, 1.0)):
    m, nt, bs = _new("trex_skin")
    co, tc = coords_meters(nt, dims)
    L = nt.links.new
    # мелкая чешуя: расстояние до края ячеек Вороного
    warp = _n(nt, "ShaderNodeTexNoise", in_Scale=30.0, in_Detail=2.0)
    L(co, warp.inputs["Vector"])
    wco = _n(nt, "ShaderNodeMix", data_type="VECTOR", in_Factor=0.012)
    L(co, wco.inputs[4])
    L(warp.outputs["Color"], wco.inputs[5])
    v1 = _n(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE", in_Scale=150.0, in_Randomness=1.0)
    L(wco.outputs[1], v1.inputs["Vector"])
    # крупные щитки/бугры
    v2 = _n(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE", in_Scale=22.0, in_Randomness=1.0)
    L(co, v2.inputs["Vector"])
    # складки/морщины
    nz = _n(nt, "ShaderNodeTexNoise", in_Scale=6.0, in_Detail=10.0, in_Roughness=0.62)
    L(co, nz.inputs["Vector"])
    wr = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X", in_Scale=9.0, in_Distortion=7.0,
            in_Detail=4.0)
    L(co, wr.inputs["Vector"])
    sc1 = _ramp(nt, [(0.0, (0, 0, 0)), (0.10, (1, 1, 1))])
    L(v1.outputs["Distance"], sc1.inputs["Fac"])
    sc2 = _ramp(nt, [(0.0, (0.55, 0.55, 0.55)), (0.06, (1, 1, 1))])
    L(v2.outputs["Distance"], sc2.inputs["Fac"])
    h = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
    L(sc1.outputs["Color"], h.inputs[0])
    L(sc2.outputs["Color"], h.inputs[1])
    h2 = _n(nt, "ShaderNodeMath", operation="MULTIPLY_ADD", in_Value=0.0)
    L(h.outputs[0], h2.inputs[0])
    h2.inputs[1].default_value = 0.22
    L(wr.outputs["Fac"], h2.inputs[2])
    h3 = _n(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L(nz.outputs["Fac"], h3.inputs[0])
    h3.inputs[1].default_value = 0.2
    L(h2.outputs[0], h3.inputs[2])
    bump = _n(nt, "ShaderNodeBump", in_Strength=0.8, in_Distance=0.005)
    L(h3.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], bs.inputs["Normal"])

    # цвет: тёмная спина, светлое брюхо (по нормали в мировых), пятна и полосы
    geo = _n(nt, "ShaderNodeNewGeometry")
    sep = _n(nt, "ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], sep.inputs["Vector"])
    belly = _ramp(nt, [(0.0, (0.20, 0.15, 0.085)), (0.40, (0.080, 0.058, 0.030)), (0.72, (0.033, 0.025, 0.014))])
    mr = _n(nt, "ShaderNodeMapRange", in_From_Min=-1.0, in_From_Max=1.0)
    L(sep.outputs["Z"], mr.inputs["Value"])
    L(mr.outputs["Result"], belly.inputs["Fac"])
    spots = _n(nt, "ShaderNodeTexNoise", in_Scale=2.2, in_Detail=6.0, in_Roughness=0.6)
    L(co, spots.inputs["Vector"])
    sr = _ramp(nt, [(0.42, (1, 1, 1)), (0.62, (0.55, 0.50, 0.45))])
    L(spots.outputs["Fac"], sr.inputs["Fac"])
    stripes = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X", in_Scale=2.6, in_Distortion=9.0,
                 in_Detail=3.0)
    L(co, stripes.inputs["Vector"])
    st = _ramp(nt, [(0.3, (0.62, 0.58, 0.55)), (0.55, (1, 1, 1))])
    L(stripes.outputs["Fac"], st.inputs["Fac"])
    c1 = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", in_Factor=1.0)
    L(belly.outputs["Color"], c1.inputs[6])
    L(sr.outputs["Color"], c1.inputs[7])
    c2 = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", in_Factor=0.35)
    L(c1.outputs[2], c2.inputs[6])
    L(st.outputs["Color"], c2.inputs[7])
    # грязь в складках чешуи (тёмные швы) и пыльные выступы
    seams = _ramp(nt, [(0.0, (0.72, 0.70, 0.66)), (0.10, (1, 1, 1))])
    L(v1.outputs["Distance"], seams.inputs["Fac"])
    c3 = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", in_Factor=1.0)
    L(c2.outputs[2], c3.inputs[6])
    L(seams.outputs["Color"], c3.inputs[7])
    ao = _n(nt, "ShaderNodeAmbientOcclusion", samples=8, in_Distance=0.08)
    aor = _ramp(nt, [(0.2, (0.35, 0.35, 0.35)), (1.0, (1, 1, 1))])
    L(ao.outputs["AO"], aor.inputs["Fac"])
    c4 = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", in_Factor=1.0)
    L(c3.outputs[2], c4.inputs[6])
    L(aor.outputs["Color"], c4.inputs[7])
    L(c4.outputs[2], bs.inputs["Base Color"])

    rg = _ramp(nt, [(0.0, (0.9, 0.9, 0.9)), (0.15, (0.62, 0.62, 0.62))])
    L(v1.outputs["Distance"], rg.inputs["Fac"])
    L(rg.outputs["Color"], bs.inputs["Roughness"])
    bs.inputs["Specular IOR Level"].default_value = 0.5
    return m


def mat_mouth():
    m, nt, bs = _new("trex_mouth")
    co, _ = coords_meters(nt, (1.2, 0.6, 0.5))
    nz = _n(nt, "ShaderNodeTexNoise", in_Scale=18.0, in_Detail=8.0)
    nt.links.new(co, nz.inputs["Vector"])
    r = _ramp(nt, [(0.3, (0.030, 0.006, 0.005)), (0.7, (0.090, 0.018, 0.014))])
    nt.links.new(nz.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], bs.inputs["Base Color"])
    b = _n(nt, "ShaderNodeBump", in_Strength=0.3, in_Distance=0.003)
    nt.links.new(nz.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bs.inputs["Normal"])
    bs.inputs["Roughness"].default_value = 0.35
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.15)
    bs.inputs["Subsurface Scale"].default_value = 0.02
    return m


def mat_teeth():
    m, nt, bs = _new("trex_teeth")
    tc = _n(nt, "ShaderNodeTexCoord")
    sep = _n(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    r = _ramp(nt, [(0.0, (0.48, 0.40, 0.26)), (1.0, (0.24, 0.17, 0.09))])
    nz = _n(nt, "ShaderNodeTexNoise", in_Scale=40.0, in_Detail=6.0)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.35
    return m


def mat_eye():
    m, nt, bs = _new("trex_eye")
    bs.inputs["Base Color"].default_value = (0.07, 0.028, 0.004, 1)
    bs.inputs["Roughness"].default_value = 0.25
    bs.inputs["Coat Weight"].default_value = 1.0
    bs.inputs["Coat Roughness"].default_value = 0.02
    return m


def mat_steel(name="steel", tint=(0.62, 0.62, 0.64), rough=0.28):
    m, nt, bs = _new(name)
    tc = _n(nt, "ShaderNodeTexCoord")
    L = nt.links.new
    # полировка с царапинами: вытянутый шум + мелкий шум, грязь в углублениях
    scr = _n(nt, "ShaderNodeTexNoise", in_Scale=260.0, in_Detail=3.0, in_Distortion=0.0)
    mp = _n(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 1.0, 1.0)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], scr.inputs["Vector"])
    blot = _n(nt, "ShaderNodeTexNoise", in_Scale=7.0, in_Detail=8.0)
    L(tc.outputs["Object"], blot.inputs["Vector"])
    rr = _ramp(nt, [(0.35, (rough * 0.85,) * 3), (0.7, (rough * 1.25,) * 3)])
    L(blot.outputs["Fac"], rr.inputs["Fac"])
    sr = _ramp(nt, [(0.48, (0, 0, 0)), (0.55, (0.05, 0.05, 0.05))])
    L(scr.outputs["Fac"], sr.inputs["Fac"])
    add = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type="ADD", in_Factor=1.0)
    L(rr.outputs["Color"], add.inputs[6])
    L(sr.outputs["Color"], add.inputs[7])
    L(add.outputs[2], bs.inputs["Roughness"])
    ao = _n(nt, "ShaderNodeAmbientOcclusion", samples=8, in_Distance=0.03)
    dirt = _ramp(nt, [(0.3, (0.18, 0.15, 0.12)), (0.9, tint)])
    L(ao.outputs["AO"], dirt.inputs["Fac"])
    L(dirt.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Metallic"].default_value = 1.0
    b = _n(nt, "ShaderNodeBump", in_Strength=0.012, in_Distance=0.001)
    L(scr.outputs["Fac"], b.inputs["Height"])
    L(b.outputs["Normal"], bs.inputs["Normal"])
    return m


def mat_wood():
    m, nt, bs = _new("ash_wood")
    tc = _n(nt, "ShaderNodeTexCoord")
    mp = _n(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 0.02)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = _n(nt, "ShaderNodeTexWave", wave_type="RINGS", in_Scale=60.0, in_Distortion=4.0, in_Detail=6.0)
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    r = _ramp(nt, [(0.2, (0.20, 0.12, 0.06)), (0.8, (0.42, 0.28, 0.15))])
    nt.links.new(wv.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.55
    b = _n(nt, "ShaderNodeBump", in_Strength=0.15, in_Distance=0.001)
    nt.links.new(wv.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bs.inputs["Normal"])
    return m


def mat_leather(col=(0.09, 0.05, 0.03)):
    m, nt, bs = _new("leather")
    nz = _n(nt, "ShaderNodeTexNoise", in_Scale=300.0, in_Detail=4.0)
    b = _n(nt, "ShaderNodeBump", in_Strength=0.2, in_Distance=0.0005)
    nt.links.new(nz.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bs.inputs["Normal"])
    bs.inputs["Base Color"].default_value = (*col, 1)
    bs.inputs["Roughness"].default_value = 0.6
    return m


def mat_blood():
    m, nt, bs = _new("blood")
    bs.inputs["Base Color"].default_value = (0.12, 0.004, 0.004, 1)
    bs.inputs["Roughness"].default_value = 0.08
    bs.inputs["Subsurface Weight"].default_value = 0.4
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.1, 0.05)
    bs.inputs["Subsurface Scale"].default_value = 0.01
    bs.inputs["Coat Weight"].default_value = 0.6
    return m
