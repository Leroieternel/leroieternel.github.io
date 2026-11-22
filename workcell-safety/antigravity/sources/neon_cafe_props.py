import bpy

PI = 3.141592653589793
TAU = 6.283185307179586

def _sin(x):
    x = (x + PI) % TAU - PI
    if x > 1.5707963267948966: x = PI - x
    elif x < -1.5707963267948966: x = -PI - x
    x2 = x * x
    return x * (1.0 - x2 / 6.0 * (1.0 - x2 / 20.0 * (1.0 - x2 / 42.0 * (1.0 - x2 / 72.0))))

def _cos(x): return _sin(x + 1.5707963267948966)

def _atan(z):
    if z > 1.0: return 1.5707963267948966 - _atan(1.0 / z)
    if z < -1.0: return -1.5707963267948966 - _atan(1.0 / z)
    return z / (1.0 + 0.28125 * z * z)

def _atan2(y, x):
    if x > 0.0: return _atan(y / x)
    if x < 0.0: return _atan(y / x) + (PI if y >= 0.0 else -PI)
    return 1.5707963267948966 if y > 0.0 else (-1.5707963267948966 if y < 0.0 else 0.0)

def _mat_pt(m, p):
    x, y, z = p
    return (m[0][0]*x + m[0][1]*y + m[0][2]*z + m[0][3],
            m[1][0]*x + m[1][1]*y + m[1][2]*z + m[1][3],
            m[2][0]*x + m[2][1]*y + m[2][2]*z + m[2][3])

def _rel_mat(dst, src):
    try: return dst.matrix_world.inverted() @ src.matrix_world
    except Exception: return None

def _resolve(view):
    obs, raw = {}, (getattr(view, "obs", None) if view is not None else None)
    if isinstance(raw, dict):
        for k, v in raw.items():
            o = v.get("obj") if isinstance(v, dict) else v
            if isinstance(o, bpy.types.Object): obs[str(k)] = o
    elif isinstance(raw, (list, tuple)):
        for it in raw:
            if isinstance(it, bpy.types.Object): obs[it.name] = it
            elif isinstance(it, dict) and isinstance(it.get("obj"), bpy.types.Object):
                obs[str(it.get("name", it["obj"].name))] = it["obj"]
            elif isinstance(it, (list, tuple)) and len(it) >= 2:
                a, b = it[0], it[1]
                if isinstance(a, dict) and isinstance(b, bpy.types.Object): obs[str(a.get("name", b.name))] = b
                elif isinstance(b, dict) and isinstance(a, bpy.types.Object): obs[str(b.get("name", a.name))] = a
    for o in bpy.data.objects: obs.setdefault(o.name, o)
    return obs

def _bounds(o):
    if not o or o.type != 'MESH' or not o.data or not o.data.vertices: return None
    vs = [v.co for v in o.data.vertices]
    zs = [v.z for v in vs]
    z0, z1 = min(zs), max(zs)
    h = max(z1 - z0, 1e-6)
    rt = max(((v.x*v.x + v.y*v.y) ** 0.5 for v in vs if v.z >= z0 + 0.7 * h), default=0.0)
    rb = max(((v.x*v.x + v.y*v.y) ** 0.5 for v in vs if v.z <= z0 + 0.3 * h), default=rt)
    rm = max((v.x*v.x + v.y*v.y) ** 0.5 for v in vs)
    cap = any(v.z > z1 - 0.003 and (v.x*v.x + v.y*v.y) ** 0.5 < 0.5 * max(rt, rm) for v in vs)
    return {"z0": z0, "z1": z1, "h": h, "rt": rt or rm, "rb": rb or rm, "rm": rm, "capped": cap}

def _signed_vol(verts, faces):
    vol = 0.0
    for f in faces:
        a = verts[f[0]]
        for i in range(1, len(f) - 1):
            b, c = verts[f[i]], verts[f[i + 1]]
            vol += a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0])
    return vol / 6.0

def _make_mesh(name, verts, faces, mat=None, vcols=None):
    vol = _signed_vol(verts, faces)
    if vol < 0.0:
        faces = [f[::-1] for f in faces]
        vol = -vol
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if vcols:
        ca = me.color_attributes.new(name=vcols[0], type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set("color", [c for rgba in vcols[1] for c in rgba])
    if mat: me.materials.append(mat)
    me.update()
    return me, vol

def _lathe(name, prof, mat, segs=48):
    verts, rings, faces = [], [], []
    for r, z in prof:
        if r <= 1e-6:
            rings.append((len(verts), True))
            verts.append((0.0, 0.0, z))
        else:
            rings.append((len(verts), False))
            for j in range(segs):
                a = TAU * j / segs
                verts.append((r * _cos(a), r * _sin(a), z))
    for k in range(len(rings) - 1):
        i0, p0 = rings[k]
        i1, p1 = rings[k + 1]
        if p0 and not p1:
            for j in range(segs): faces.append((i0, i1 + (j + 1) % segs, i1 + j))
        elif not p0 and p1:
            for j in range(segs): faces.append((i0 + j, i0 + (j + 1) % segs, i1))
        elif not p0 and not p1:
            for j in range(segs):
                jn = (j + 1) % segs
                faces.append((i0 + j, i0 + jn, i1 + jn, i1 + j))
    return _make_mesh(name, verts, faces, mat)

def _set_in(n, k, v):
    if k in n.inputs: n.inputs[k].default_value = v

def _new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bsdf, out

def _croissant_mat():
    m, nt, bsdf, _ = _new_mat("Mat_Croissant_Artisan")
    tc = nt.nodes.new('ShaderNodeTexCoord')
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = "BakeMask"
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(at.outputs['Color'], sp.inputs['Color'])
    n0 = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n0, 'Scale', 38.0); _set_in(n0, 'Detail', 5.0); _set_in(n0, 'Roughness', 0.6)
    n1 = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n1, 'Scale', 260.0); _set_in(n1, 'Detail', 8.0); _set_in(n1, 'Roughness', 0.72); _set_in(n1, 'Distortion', 0.35)
    n2 = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n2, 'Scale', 2400.0); _set_in(n2, 'Detail', 10.0); _set_in(n2, 'Roughness', 0.78)
    for n in (n0, n1, n2): nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY_ADD'; m1.inputs[1].default_value = 0.62
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'; m2.inputs[1].default_value = 0.34; m2.use_clamp = True
    nt.links.new(sp.outputs['Red'], m1.inputs[0]); nt.links.new(sp.outputs['Green'], m1.inputs[2])
    nt.links.new(n0.outputs['Fac'], m2.inputs[0]); nt.links.new(m1.outputs['Value'], m2.inputs[2])
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'B_SPLINE'
    es = cr.color_ramp.elements
    es[0].position, es[0].color = 0.10, (0.82, 0.56, 0.24, 1.0)
    es[1].position, es[1].color = 0.94, (0.16, 0.052, 0.013, 1.0)
    e1 = es.new(0.40); e1.color = (0.60, 0.29, 0.085, 1.0)
    e2 = es.new(0.70); e2.color = (0.34, 0.13, 0.032, 1.0)
    nt.links.new(m2.outputs['Value'], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'; mr.inputs[1].default_value = 0.34; mr.inputs[2].default_value = 0.38
    nt.links.new(n1.outputs['Fac'], mr.inputs[0]); nt.links.new(mr.outputs['Value'], bsdf.inputs['Roughness'])
    b2 = nt.nodes.new('ShaderNodeBump'); _set_in(b2, 'Strength', 0.22); _set_in(b2, 'Distance', 0.00035)
    b1 = nt.nodes.new('ShaderNodeBump'); _set_in(b1, 'Strength', 0.34); _set_in(b1, 'Distance', 0.0012)
    nt.links.new(n2.outputs['Fac'], b2.inputs['Height']); nt.links.new(b2.outputs['Normal'], b1.inputs['Normal'])
    nt.links.new(n1.outputs['Fac'], b1.inputs['Height']); nt.links.new(b1.outputs['Normal'], bsdf.inputs['Normal'])
    _set_in(bsdf, 'Specular IOR Level', 0.42); _set_in(bsdf, 'Coat Weight', 0.12); _set_in(bsdf, 'Coat Roughness', 0.36)
    _set_in(bsdf, 'Subsurface Weight', 0.06); _set_in(bsdf, 'Subsurface Scale', 0.003)
    return m

def _ceramic_mat(name, col=(0.89, 0.86, 0.81, 1.0), rough=0.08):
    m, nt, bsdf, _ = _new_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n, 'Scale', 95.0); _set_in(n, 'Detail', 4.0)
    b = nt.nodes.new('ShaderNodeBump'); _set_in(b, 'Strength', 0.025); _set_in(b, 'Distance', 0.00015)
    nt.links.new(tc.outputs['Object'], n.inputs['Vector']); nt.links.new(n.outputs['Fac'], b.inputs['Height'])
    nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    _set_in(bsdf, 'Base Color', col); _set_in(bsdf, 'Roughness', rough); _set_in(bsdf, 'IOR', 1.52)
    _set_in(bsdf, 'Coat Weight', 0.85); _set_in(bsdf, 'Coat Roughness', 0.035)
    return m

def _espresso_mat():
    m, nt, bsdf, _ = _new_mat("Mat_Espresso_Crema")
    tc = nt.nodes.new('ShaderNodeTexCoord')
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = "CremaMask"
    sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(at.outputs['Color'], sp.inputs['Color'])
    n0 = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n0, 'Scale', 85.0); _set_in(n0, 'Detail', 6.0); _set_in(n0, 'Distortion', 1.5)
    n1 = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n1, 'Scale', 680.0); _set_in(n1, 'Detail', 8.0); _set_in(n1, 'Roughness', 0.72)
    for n in (n0, n1): nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY_ADD'; m1.inputs[1].default_value = 0.55
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'; m2.inputs[1].default_value = 0.25; m2.use_clamp = True
    nt.links.new(n0.outputs['Fac'], m1.inputs[0]); nt.links.new(sp.outputs['Red'], m1.inputs[2])
    nt.links.new(n1.outputs['Fac'], m2.inputs[0]); nt.links.new(m1.outputs['Value'], m2.inputs[2])
    cr = nt.nodes.new('ShaderNodeValToRGB'); es = cr.color_ramp.elements
    es[0].position, es[0].color = 0.26, (0.012, 0.004, 0.0015, 1.0)
    es[1].position, es[1].color = 0.90, (0.46, 0.23, 0.075, 1.0)
    e1 = es.new(0.58); e1.color = (0.24, 0.095, 0.025, 1.0)
    nt.links.new(m2.outputs['Value'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'; mr.inputs[1].default_value = 0.30; mr.inputs[2].default_value = 0.06
    nt.links.new(m2.outputs['Value'], mr.inputs[0]); nt.links.new(mr.outputs['Value'], bsdf.inputs['Roughness'])
    b = nt.nodes.new('ShaderNodeBump'); _set_in(b, 'Strength', 0.08); _set_in(b, 'Distance', 0.0002)
    nt.links.new(n1.outputs['Fac'], b.inputs['Height']); nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    _set_in(bsdf, 'Coat Weight', 0.48); _set_in(bsdf, 'Coat Roughness', 0.05); _set_in(bsdf, 'IOR', 1.35)
    return m

def _glass_mat(name, col, ior, rough, shadow_col, vol_dens=0.0):
    m, nt, bsdf, out = _new_mat(name)
    _set_in(bsdf, 'Base Color', col); _set_in(bsdf, 'Roughness', rough); _set_in(bsdf, 'IOR', ior)
    _set_in(bsdf, 'Transmission Weight', 1.0); _set_in(bsdf, 'Coat Weight', 0.25); _set_in(bsdf, 'Coat Roughness', 0.015)
    if vol_dens > 0.0:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        n = nt.nodes.new('ShaderNodeTexNoise'); _set_in(n, 'Scale', 120.0); _set_in(n, 'Detail', 3.0)
        b = nt.nodes.new('ShaderNodeBump'); _set_in(b, 'Strength', 0.015); _set_in(b, 'Distance', 0.0001)
        nt.links.new(tc.outputs['Object'], n.inputs['Vector']); nt.links.new(n.outputs['Fac'], b.inputs['Height'])
        nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
        va = nt.nodes.new('ShaderNodeVolumeAbsorption'); _set_in(va, 'Color', col); _set_in(va, 'Density', vol_dens)
        nt.links.new(va.outputs['Volume'], out.inputs['Volume'])
    lp = nt.nodes.new('ShaderNodeLightPath')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); _set_in(tr, 'Color', shadow_col)
    ms = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Shadow Ray'], ms.inputs[0])
    nt.links.new(bsdf.outputs['BSDF'], ms.inputs[1]); nt.links.new(tr.outputs['BSDF'], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs['Surface'])
    if hasattr(m, "use_raytrace_refraction"): m.use_raytrace_refraction = True
    if hasattr(m, "surface_render_method"): m.surface_render_method = 'DITHERED'
    return m

def _croissant_mesh(mat):
    nu, nv = 64, 36
    raw, vcols, faces = [], [], []
    def spine(u):
        a = u * 1.15
        return 0.058 * _sin(a), 0.032 * (_cos(a) - 0.58)
    s0, s1 = spine(-1.0), spine(1.0)
    raw.append((s0[0], s0[1], 0.0)); vcols.append([0.92, 0.35, 0.5, 1.0])
    for i in range(1, nu):
        u = -1.0 + 2.0 * i / nu; au = abs(u); a = u * 1.15
        sx, sy = spine(u)
        tx, ty = 0.058 * 1.15 * _cos(a), -0.032 * 1.15 * _sin(a)
        tl = (tx*tx + ty*ty) ** 0.5
        nx, ny = -ty / tl, tx / tl
        t = (1.0 - u * u) ** 0.58
        w, h = 0.0235 * (0.12 + 0.88 * t), 0.0195 * (0.12 + 0.88 * t)
        for j in range(nv):
            th = TAU * j / nv; cs, sn = _cos(th), _sin(th)
            sc = max(0.0, au - 0.02) * 4.6 + 0.13 * sn * (au / (au + 0.12))
            ph = sc - int(sc)
            cr = (4.0 * ph * (1.0 - ph)) ** 0.34
            sh = (1.0 - ph) ** 0.55
            lam = 0.84 + (0.15 * cr + 0.11 * sh) * (0.4 + 0.6 * (1.0 - 0.4 * au))
            pf = 1.0 + 0.03 * _sin(5.0 * th + 8.0 * u) + 0.018 * _cos(9.0 * th - 13.0 * u)
            tip = max(0.0, 1.0 - (u / 0.17) ** 2) * max(0.0, sn - 0.3)
            snf = sn * (0.50 + 0.18 * (1.0 + sn)) if sn < 0.0 else sn
            rl = w * lam * pf * cs
            zo = h * lam * pf * snf + 0.0026 * tip + 0.0025 * (1.0 - u * u)
            raw.append((sx + nx * rl, sy + ny * rl, zo))
            vcols.append([min(1.0, 0.55 * cr * (0.45 + 0.55 * sh) + 0.38 * (au ** 1.4) + 0.25 * tip), 0.0, 0.0, 1.0])
    end = len(raw)
    raw.append((s1[0], s1[1], 0.0)); vcols.append([0.92, 0.35, 0.5, 1.0])
    xs, ys, zs = [p[0] for p in raw], [p[1] for p in raw], [p[2] for p in raw]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    verts = []
    for k, (x, y, z) in enumerate(raw):
        nz = (z - z0) / max(z1 - z0, 1e-6)
        verts.append(((x - cx) * 0.120 / (x1 - x0), (y - cy) * 0.067 / (y1 - y0), nz * 0.038))
        vcols[k][1] = nz ** 0.72
    for j in range(nv): faces.append((0, 1 + (j + 1) % nv, 1 + j))
    for k in range(nu - 2):
        b0, b1 = 1 + k * nv, 1 + (k + 1) * nv
        for j in range(nv):
            jn = (j + 1) % nv
            faces.append((b0 + j, b0 + jn, b1 + jn, b1 + j))
    bl = 1 + (nu - 2) * nv
    for j in range(nv): faces.append((bl + j, bl + (j + 1) % nv, end))
    return _make_mesh("Croissant_Artisan_Mesh", verts, faces, mat, ("BakeMask", vcols))

def _liquid_mesh(name, rt, rb, z0, z1, men, mat, mrel=None, segs=48, rings=10):
    verts, vcols, faces = [(0.0, 0.0, z1)], [(0.0, 1.0, 0.0, 1.0)], []
    for i in range(1, rings + 1):
        f = i / rings; r = rt * f; dz = men * (f ** 5)
        for j in range(segs):
            a = TAU * j / segs
            verts.append((r * _cos(a), r * _sin(a), z1 + dz + 0.00012 * _sin(3.0 * a + 7.0 * f)))
            vcols.append((f, 1.0, 0.0, 1.0))
    bi = len(verts)
    for j in range(segs):
        a = TAU * j / segs
        verts.append((rb * _cos(a), rb * _sin(a), z0)); vcols.append((1.0, 0.0, 0.0, 1.0))
    bc = len(verts); verts.append((0.0, 0.0, z0)); vcols.append((0.0, 0.0, 0.0, 1.0))
    if mrel is not None: verts = [_mat_pt(mrel, p) for p in verts]
    for j in range(segs): faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 1):
        r0, r1 = 1 + i * segs, 1 + (i + 1) * segs
        for j in range(segs):
            jn = (j + 1) % segs; faces.append((r0 + j, r1 + j, r1 + jn, r0 + jn))
    rl = 1 + (rings - 1) * segs
    for j in range(segs):
        jn = (j + 1) % segs
        faces.append((rl + j, bi + j, bi + jn, rl + jn))
        faces.append((bi + j, bc, bi + jn))
    return _make_mesh(name, verts, faces, mat, ("CremaMask", vcols))

def _cup_color(obj):
    if obj and obj.data and obj.data.materials:
        m = obj.data.materials[0]
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    c = tuple(n.inputs['Base Color'].default_value)
                    if max(abs(c[0]-0.8), abs(c[1]-0.8), abs(c[2]-0.8)) > 0.05: return c
    return (0.89, 0.86, 0.80, 1.0)

def _is_metallic(obj):
    if not obj or not obj.data: return False
    for m in obj.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED' and n.inputs['Metallic'].default_value > 0.3: return True
    return False

def refine(view=None):
    bpy.context.view_layer.update()
    obs = _resolve(view)
    audit = {"ok": True, "blender": list(bpy.app.version)}
    px = {o.name: o for k, o in obs.items() if (k == "pastry_mid" or k.startswith("pastry_") or o.name == "pastry_mid" or o.name.startswith("pastry_")) and o.name != "croissant_artisan"}
    for o in px.values(): o.hide_render = True; o.hide_viewport = True
    pts = [(o.matrix_world[0][3], o.matrix_world[1][3]) for o in px.values()]
    best, yaw = 0.0, 0.22
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
            d = (dx*dx + dy*dy) ** 0.5
            if d > best and d > 0.015: best, yaw = d, _atan2(dy, dx)
    cme, cvol = _croissant_mesh(_croissant_mat())
    cobj = bpy.data.objects.get("croissant_artisan")
    if cobj is None:
        cobj = bpy.data.objects.new("croissant_artisan", cme)
        col = next((o.users_collection[0] for o in px.values() if o.users_collection), bpy.context.scene.collection)
        col.objects.link(cobj)
    else: cobj.data = cme
    cobj.location, cobj.rotation_euler, cobj.scale = (-0.52, 0.78, 0.895), (0.0, 0.0, yaw), (1.0, 1.0, 1.0)
    audit["croissant"] = {"obj": cobj.name, "hidden": sorted(px), "dims": [round(v, 4) for v in cobj.dimensions], "vol": round(cvol, 7)}
    cup, cof = obs.get("cup_body"), obs.get("cup_coffee")
    if cup:
        b = _bounds(cup) or {"z0": -0.030, "z1": 0.030, "h": 0.060, "rm": 0.028}
        r, z0, z1, h = b["rm"], b["z0"], b["z1"], b["h"]
        ri, wt = r - 0.0030, 0.0030
        cmat = _ceramic_mat("Mat_Demitasse_Ceramic", _cup_color(cup))
        prof = [(0.0, z0+0.001), (r*0.60, z0+0.001), (r*0.68, z0), (r*0.76, z0), (r*0.88, z0+0.06*h),
                (r*0.96, z0+0.18*h), (r*0.995, z0+0.36*h), (r*1.005, z0+0.62*h), (r*1.02, z1-0.003),
                (r*1.01, z1-0.0005), (r-wt*0.35, z1), (ri+0.0005, z1-0.0006), (ri, z1-0.0025),
                (ri-0.0004, z0+0.55*h), (ri-0.0018, z0+0.28*h), (ri*0.72, z0+0.12*h), (0.0, z0+0.095*h)]
        cup.data, vcup = _lathe("Cup_Demitasse_Mesh", prof, cmat)
        kept = []
        for k, o in obs.items():
            if ("cup_handle" in k or "cup_handle" in o.name) and o.type == 'MESH':
                o.data.materials.clear(); o.data.materials.append(cmat); kept.append(o.name)
        if cof:
            cof.data, _ = _liquid_mesh("Cup_Espresso_Mesh", ri+0.0003, ri-0.0008, z1-0.011, z1-0.004, 0.0008, _espresso_mat(), _rel_mat(cof, cup))
        audit["cup"] = {"body": cup.name, "coffee": cof.name if cof else None, "handles": sorted(set(kept)), "vol": round(vcup, 7)}
    for k, o in obs.items():
        if o.type == 'MESH' and any(t in (k + o.name).lower() for t in ("plate", "saucer", "dish")) and not any(t in o.name.lower() for t in ("pastry", "croissant", "cup", "water")):
            b = _bounds(o)
            if b and abs(o.matrix_world[0][3] + 0.52) < 0.12 and abs(o.matrix_world[1][3] - 0.78) < 0.12:
                r, z0, z1 = b["rm"], b["z0"], b["z1"]; zf = z0 + 0.25 * b["h"]
                pp = [(0.0, z0+0.0006), (r*0.56, z0+0.0006), (r*0.60, z0), (r*0.64, z0), (r*0.82, zf),
                      (r*0.97, z1-0.002), (r, z1-0.0005), (r*0.99, z1), (r*0.72, z1-0.0004), (0.0, z1-0.0004)]
                o.data, _ = _lathe("Dessert_Plate_Mesh", pp, _ceramic_mat("Mat_Porcelain_Plate", (0.93, 0.91, 0.87, 1.0), 0.065), 64)
                audit["plate"] = {"obj": o.name, "r": round(r, 4), "h": round(b["h"], 4)}
                break
    wg, wf = obs.get("water_glass_t1"), obs.get("water_fill_t1")
    if wg:
        b = _bounds(wg)
        upgraded = bool(b and (b["capped"] or _is_metallic(wg)))
        if upgraded:
            rt, rb, z0, z1, h = b["rt"], b["rb"], b["z0"], b["z1"], b["h"]
            wt, bt = max(0.0022, min(0.0032, 0.08 * rt)), min(0.010, 0.14 * h)
            gp = [(0.0, z0+0.0008), (rb*0.84, z0+0.0008), (rb*0.94, z0), (rb, z0+0.002), (rt, z1-0.002),
                  (rt-wt*0.2, z1-0.0003), (rt-wt*0.5, z1), (rt-wt*0.85, z1-0.0004), (rt-wt, z1-0.002),
                  (rb-wt, z0+bt+0.003), (rb-wt*1.4, z0+bt), (0.0, z0+bt)]
            wg.data, _ = _lathe("Water_Glass_Mesh", gp, _glass_mat("Mat_Clear_Glass", (0.95, 0.99, 0.97, 1.0), 1.51, 0.02, (0.92, 0.96, 0.94, 1.0)))
        if wf:
            bf = _bounds(wf)
            wmat = _glass_mat("Mat_Water_Translucent", (0.86, 0.95, 0.98, 1.0), 1.333, 0.015, (0.88, 0.96, 0.99, 1.0), 6.0)
            if upgraded and bf:
                m_f2g, m_g2f = _rel_mat(wg, wf), _rel_mat(wf, wg)
                if m_f2g and m_g2f:
                    zg0 = max(b["z0"] + bt - 0.0002, _mat_pt(m_f2g, (0.0, 0.0, bf["z0"]))[2])
                    zg1 = min(b["z1"] - 0.003, _mat_pt(m_f2g, (0.0, 0.0, bf["z1"]))[2])
                    f0, f1 = (zg0 - b["z0"]) / h, (zg1 - b["z0"]) / h
                    r_lo = rb + (rt - rb) * f0 - wt + 0.0002
                    r_hi = rb + (rt - rb) * f1 - wt + 0.0002
                    wf.data, _ = _liquid_mesh("Water_Fill_Mesh", r_hi, r_lo, zg0, zg1, 0.0009, wmat, m_g2f)
            elif bf:
                wf.data, _ = _liquid_mesh("Water_Fill_Mesh", bf["rt"], bf["rb"], bf["z0"], bf["z1"], 0.0009, wmat)
        audit["water"] = {"glass": wg.name, "fill": wf.name if wf else None, "upgraded": upgraded}
    return audit
