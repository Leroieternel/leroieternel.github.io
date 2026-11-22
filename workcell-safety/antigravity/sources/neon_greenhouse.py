from math import atan2, cos, hypot, pi, radians, sin
import random
import bmesh
import bpy
from mathutils import Matrix, Vector

_X0, _X1, _YW, _ZW = -4.0, 4.0, 2.15, 0.74


def _box(bm, x0, x1, y0, y1, z0, z1, rx=0.0):
    c = ((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5)
    m = Matrix.Translation(c) @ Matrix.Rotation(rx, 4, "X") @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def _cyl(bm, p0, p1, r, segs=12):
    v0, v1 = Vector(p0), Vector(p1)
    d = v1 - v0
    if d.length < 1e-5:
        return
    q = Vector((0.0, 0.0, 1.0)).rotation_difference(d.normalized())
    m = Matrix.Translation((v0 + v1) * 0.5) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=d.length, matrix=m)


def _to_obj(name, bm, col, mat, uv_scale=0.5, smooth=False, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        f.smooth = smooth
        nx, ny, nz = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        for lp in f.loops:
            v = lp.vert.co
            lp[uv].uv = ((v.x * uv_scale, v.y * uv_scale) if nz >= nx and nz >= ny else
                         (v.x * uv_scale, v.z * uv_scale) if ny >= nx else (v.y * uv_scale, v.z * uv_scale))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def _mk_mat(name, base, rough=0.5, metal=0.0, bump=0.04, scale=18.0, coat=0.0, trans=0.0, sss=0.0, wave=False, vcol=False):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out, bsdf = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Transmission Weight"].default_value = trans
    bsdf.inputs["Subsurface Weight"].default_value = sss
    bsdf.inputs["Subsurface Scale"].default_value = 0.015
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if vcol:
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    if wave:
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type, wv.bands_direction = "BANDS", "X"
        wv.inputs["Scale"].default_value = 62.0
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["IOR"].default_value = 1.49
        if hasattr(mat, "use_raytrace_refraction"):
            mat.use_raytrace_refraction = True
    elif bump > 0.0:
        ns = nt.nodes.new("ShaderNodeTexNoise")
        ns.inputs["Scale"].default_value, ns.inputs["Detail"].default_value = scale, 6.0
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = max(0.05, rough - 0.14), min(0.98, rough + 0.14)
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(tc.outputs["Object"], ns.inputs["Vector"])
        nt.links.new(ns.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
        nt.links.new(ns.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _add_leaf(bm, col_layer, base, az, length, width, arch, droop, rgba):
    fwd, side = Vector((cos(az), sin(az), 0.0)), Vector((-sin(az), cos(az), 0.0))
    p1 = base + fwd * (length * 0.22) + Vector((0.0, 0.0, arch * 0.52))
    p1.y = max(0.77, p1.y)
    _cyl(bm, base, p1, 0.0024, segs=5)
    blade_l = length * 0.84
    v0 = bm.verts.new(p1)
    rows = []
    for k, t in enumerate((0.26, 0.56, 0.82)):
        hw = width * sin(pi * (t ** 0.82))
        pc = p1 + fwd * (blade_l * t) + Vector((0.0, 0.0, arch * sin(0.68 * pi * t) - droop * t * t))
        row = []
        for u in (-1.0, -0.45, 0.0, 0.45, 1.0):
            vz = 0.0055 * abs(u) - (0.0028 if u == 0.0 else 0.0) + 0.0014 * sin(k * 2.2) * abs(u)
            pt = pc + side * (hw * u) + Vector((0.0, 0.0, vz))
            pt.y = max(0.76, pt.y)
            row.append(bm.verts.new(pt))
        rows.append(row)
    tip = p1 + fwd * blade_l + Vector((0.0, 0.0, arch * sin(0.68 * pi) - droop))
    tip.y = max(0.76, tip.y)
    vt = bm.verts.new(tip)
    faces = [bm.faces.new((v0, rows[0][i], rows[0][i + 1])) for i in range(4)]
    for r0, r1 in ((rows[0], rows[1]), (rows[1], rows[2])):
        faces += [bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1])) for i in range(4)]
    faces += [bm.faces.new((rows[2][i], vt, rows[2][i + 1])) for i in range(4)]
    for f in faces:
        f.smooth = True
        for lp in f.loops:
            lp[col_layer] = rgba


def build(scene, library=None):
    col = bpy.data.collections.get("HorticulturalYard") or bpy.data.collections.new("HorticulturalYard")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    m_wall = _mk_mat("wall_mat", (0.77, 0.75, 0.70), rough=0.78, bump=0.06, scale=14.0)
    m_conc = _mk_mat("gh_concrete", (0.58, 0.57, 0.54), rough=0.84, bump=0.08, scale=22.0)
    m_steel = _mk_mat("gh_galv_steel", (0.66, 0.69, 0.71), rough=0.35, metal=0.88, bump=0.025, scale=42.0)
    m_poly = _mk_mat("gh_polymer", (0.11, 0.15, 0.12), rough=0.50, bump=0.03, scale=35.0, coat=0.15)
    m_glaze = _mk_mat("gh_glazing", (0.84, 0.90, 0.86), rough=0.24, bump=0.045, coat=0.70, trans=0.55, wave=True)
    m_soil = _mk_mat("gh_damp_soil", (0.09, 0.065, 0.045), rough=0.62, bump=0.18, scale=48.0)
    m_leaf = _mk_mat("gh_foliage", (0.16, 0.30, 0.11), rough=0.44, bump=0.035, scale=55.0, sss=0.22, vcol=True)
    props = []

    # Knee wall (Genie wall retexturing target), confirmed footing, and pitched top sill
    bm = bmesh.new(); _box(bm, _X0, _X1, _YW, 2.43, 0.0, _ZW)
    wall = _to_obj("gh_knee_wall", bm, col, m_wall, uv_scale=0.5)
    bm = bmesh.new(); _box(bm, _X0 - 0.02, _X1 + 0.02, 2.11, 2.46, 0.0, 0.06)
    props.append(_to_obj("gh_footing", bm, col, m_conc))
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for x in (_X0 - 0.04, _X1 + 0.04)
          for (y, z) in ((2.10, _ZW), (2.46, _ZW), (2.46, _ZW + 0.055), (2.10, _ZW + 0.038))]
    for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)):
        bm.faces.new([vs[i] for i in q])
    props.append(_to_obj("gh_sill", bm, col, m_steel))

    # Glazing frame, concealed-fastener caps, interior rafters, and combined translucent glazing
    bm_f, bm_g, bm_v = bmesh.new(), bmesh.new(), bmesh.new()
    pitch, rlen = atan2(0.84, 2.28), hypot(2.28, 0.84)
    for x in range(-4, 5):
        _box(bm_f, x - 0.026, x + 0.026, 2.19, 2.275, _ZW + 0.035, 2.68)
        _box(bm_f, x - 0.021, x + 0.021, 2.165, 2.19, _ZW + 0.035, 2.68)
        _box(bm_f, x - 0.024, x + 0.024, 3.36 - rlen * 0.5, 3.36 + rlen * 0.5, 3.06, 3.12, rx=pitch)
    for z0, z1 in ((_ZW + 0.035, _ZW + 0.09), (1.72, 1.77), (2.62, 2.70)):
        _box(bm_f, _X0 - 0.02, _X1 + 0.02, 2.175, 2.28, z0, z1)
    vent_bays = (-1, 1)
    for bx in range(-4, 4):
        _box(bm_g, bx + 0.025, bx + 0.975, 2.21, 2.238, _ZW + 0.088, 1.722)
        _box(bm_g, bx + 0.025, bx + 0.975, 3.36 - rlen * 0.5, 3.36 + rlen * 0.5, 3.115, 3.14, rx=pitch)
        if bx in vent_bays:
            for (xa, xb, za, zb) in ((bx + 0.026, bx + 0.056, 1.77, 2.62), (bx + 0.944, bx + 0.974, 1.77, 2.62),
                                     (bx + 0.026, bx + 0.974, 1.77, 1.80), (bx + 0.026, bx + 0.974, 2.59, 2.62)):
                _box(bm_v, xa, xb, 2.175, 2.265, za, zb)
            for k in range(8):
                zc = 1.855 + k * 0.095
                _box(bm_v, bx + 0.055, bx + 0.945, 2.185, 2.255, zc - 0.003, zc + 0.003, rx=radians(28.0))
            _box(bm_v, bx + 0.492, bx + 0.508, 2.25, 2.265, 1.80, 2.59)
            _cyl(bm_v, (bx + 0.93, 2.25, 2.02), (bx + 0.84, 2.20, 2.16), 0.007, segs=8)
        else:
            _box(bm_g, bx + 0.025, bx + 0.975, 2.21, 2.238, 1.768, 2.622)
    props += [_to_obj("gh_glazing_frame", bm_f, col, m_steel),
              _to_obj("gh_glazing_panels", bm_g, col, m_glaze),
              _to_obj("gh_high_vents", bm_v, col, m_steel)]

    # Eaves gutter, clip hangers, and grounded downpipe
    bm_gt = bmesh.new()
    _box(bm_gt, _X0 - 0.06, _X1 + 0.06, 2.05, 2.18, 2.56, 2.572)
    _box(bm_gt, _X0 - 0.06, _X1 + 0.06, 2.05, 2.062, 2.56, 2.665)
    _box(bm_gt, _X0 - 0.06, _X1 + 0.06, 2.168, 2.18, 2.56, 2.665)
    for xe in (_X0 - 0.06, _X1 + 0.05):
        _box(bm_gt, xe, xe + 0.012, 2.05, 2.18, 2.56, 2.665)
    for x in range(-4, 5):
        _box(bm_gt, x - 0.014, x + 0.014, 2.045, 2.19, 2.548, 2.565)
    _cyl(bm_gt, (2.96, 2.11, 2.56), (2.96, 2.09, 2.42), 0.036)
    _cyl(bm_gt, (2.96, 2.09, 2.42), (2.96, 2.09, 0.10), 0.035)
    _cyl(bm_gt, (2.96, 2.09, 0.11), (2.96, 1.98, 0.055), 0.036)
    for zs in (0.52, 1.45, 2.25):
        _box(bm_gt, 2.91, 3.01, 2.05, 2.16, zs - 0.012, zs + 0.012)
    props.append(_to_obj("gh_gutter_downpipe", bm_gt, col, m_steel, smooth=True))

    # Wall-mounted hose reel on bracket + rear-bed drip irrigation line
    bm_hr, bm_ir = bmesh.new(), bmesh.new()
    _box(bm_hr, -2.56, -2.34, 2.12, 2.15, 0.44, 0.64)
    for sx in (-2.54, -2.36):
        _box(bm_hr, sx - 0.012, sx + 0.012, 1.96, 2.13, 0.52, 0.56)
    _cyl(bm_hr, (-2.55, 1.99, 0.54), (-2.35, 1.99, 0.54), 0.125, segs=18)
    for rx in (-2.55, -2.35):
        _cyl(bm_hr, (rx - 0.006, 1.99, 0.54), (rx + 0.006, 1.99, 0.54), 0.145, segs=18)
    _cyl(bm_ir, (-2.98, 1.66, 0.196), (2.98, 1.66, 0.196), 0.013, segs=10)
    for ix in (-2.7, -1.8, -0.9, 0.0, 0.9, 1.8, 2.7):
        _cyl(bm_ir, (ix, 1.66, 0.175), (ix, 1.66, 0.24), 0.007, segs=8)
    props += [_to_obj("gh_hose_reel", bm_hr, col, m_poly, smooth=True),
              _to_obj("gh_irrigation_line", bm_ir, col, m_poly, smooth=True)]

    # Grounded damp soil mounds, plant support rods, and combined veined arced herb leaves
    rng = random.Random(4207)
    bm_s, bm_r, bm_l = bmesh.new(), bmesh.new(), bmesh.new()
    col_layer = bm_l.loops.layers.color.new("Col")
    for idx in range(30):
        cx = -2.85 + (idx % 15) * 0.405 + rng.uniform(-0.07, 0.07)
        cy = (1.02 if idx < 15 else 1.44) + rng.uniform(-0.08, 0.08)
        m = Matrix.Translation((cx, cy, 0.18)) @ Matrix.Diagonal((rng.uniform(0.08, 0.12), rng.uniform(0.08, 0.11), 0.022, 1.0))
        bmesh.ops.create_icosphere(bm_s, subdivisions=2, radius=1.0, matrix=m)
        strap = (idx % 3 == 0)
        for j in range(9 if strap else 8):
            az = j * (2.0 * pi / (9 if strap else 8)) + rng.uniform(-0.28, 0.28)
            ln = rng.uniform(0.20, 0.30) if strap else rng.uniform(0.11, 0.18)
            wd = rng.uniform(0.014, 0.022) if strap else rng.uniform(0.028, 0.048)
            rgba = (rng.uniform(0.11, 0.20), rng.uniform(0.24, 0.37), rng.uniform(0.08, 0.14), 1.0)
            _add_leaf(bm_l, col_layer, Vector((cx + rng.uniform(-0.02, 0.02), cy + rng.uniform(-0.02, 0.02), 0.178)),
                      az, ln, wd, rng.uniform(0.09, 0.16), rng.uniform(0.03, 0.08), rgba)
    for sx in (-2.6, -1.75, -0.9, -0.05, 0.85, 1.7, 2.55):
        for sy, sh in ((1.14, 0.46), (1.50, 0.56)):
            _cyl(bm_r, (sx, sy, 0.16), (sx, sy, 0.18 + sh), 0.0055, segs=8)
    _cyl(bm_r, (-2.6, 1.50, 0.56), (2.55, 1.50, 0.56), 0.0025, segs=6)
    props += [_to_obj("gh_soil_mounds", bm_s, col, m_soil, smooth=True),
              _to_obj("gh_plant_rods", bm_r, col, m_steel, smooth=True),
              _to_obj("gh_herb_foliage", bm_l, col, m_leaf, smooth=True, recalc=False)]
    return {"walls": [wall], "props": props}


def daylight(scene, library=None):
    for ob in list(scene.objects):
        if ob.type == "LIGHT" and ob.name != "gh_daylight_sun":
            ob.data.energy = 0.0
            ob.hide_render = ob.hide_viewport = True
            if hasattr(ob, "visible_glossy"):
                ob.visible_glossy = False
    w = bpy.data.worlds.get("HorticulturalSky") or bpy.data.worlds.new("HorticulturalSky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc, sep = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.clamp, mr.interpolation_type = True, "SMOOTHSTEP"
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -0.04, 0.06
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type, sky.sun_disc = "NISHITA", False
    sky.sun_elevation, sky.sun_rotation = radians(38.0), radians(35.0)
    sky.air_density, sky.dust_density, sky.ozone_density, sky.altitude = 1.1, 1.2, 1.2, 120.0
    sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs[3].default_value = 0.14
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (0.26, 0.28, 0.23, 1.0)
    bg, wo = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeOutputWorld")
    for a, b in ((tc.outputs["Generated"], sep.inputs["Vector"]), (sep.outputs["Z"], mr.inputs["Value"]),
                 (sky.outputs["Color"], sc.inputs[0]), (mr.outputs["Result"], mx.inputs[0]),
                 (sc.outputs["Vector"], mx.inputs[7]), (mx.outputs[2], bg.inputs["Color"]),
                 (bg.outputs["Background"], wo.inputs["Surface"])):
        nt.links.new(a, b)
    sun = bpy.data.objects.get("gh_daylight_sun")
    if sun is None:
        ld = bpy.data.lights.new("gh_daylight_sun", type="SUN")
        sun = bpy.data.objects.new("gh_daylight_sun", ld)
        scene.collection.objects.link(sun)
    sun.data.energy, sun.data.color, sun.data.angle = 3.2, (1.0, 0.965, 0.91), radians(3.2)
    sun.location, sun.rotation_euler = (0.0, 0.0, 5.0), (radians(52.0), 0.0, radians(-35.0))
    vs = scene.view_settings
    try:
        vs.view_transform, vs.look = "AgX", "None"
    except Exception:
        pass
    vs.exposure, vs.gamma, vs.use_curve_mapping = 0.0, 1.0, False
