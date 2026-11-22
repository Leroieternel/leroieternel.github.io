import math
import bpy
from mathutils import Matrix, Vector

# Available floor pockets strictly outside the robot sweep zone
# (x in [-2.1, 1.45], y in [-1.8, 1.0]), walls (y=2.05, x=-3.55),
# back door/window (x in [0.0, 1.0]), and room shelving
# ((-1.76, 1.50) and (1.68, 1.53), halfwidth 0.59, depth 0.29).
_POCKET_LEFT = (-2.82, 0.54, 0.0)
_POCKET_RIGHT_MID = (2.70, 0.46, 0.0)
_POCKET_RIGHT_BACK = (2.78, 1.53, 0.0)

_MAX_POCKET_FOOTPRINT = 0.66  # Strictly <= 0.68 m with 2 cm clearance margin

_CANONICAL_CASES = (
    "warehouse",
    "clinic",
    "cafe",
    "lab",
    "parcel_sorting",
    "shaft_repair",
    "electronics_lab",
    "print_bindery",
    "library",
    "packing_bay",
)

# Each pocket entry:
# (pocket_xyz, base_key, target_height_m, yaw_rad, optional_top_prop)
# optional_top_prop: (key, min_max_dim_m, max_max_dim_m, req_radius_m, req_clearance_m, yaw_rad)
_SCENE_RECIPES = {
    "warehouse": (
        (_POCKET_LEFT, "shipping_crate", 0.56, 0.04, ("stock_box", 0.24, 0.34, 0.14, 0.30, -0.08)),
        (_POCKET_RIGHT_MID, "plastic_crate", 0.38, -0.05, None),
        (_POCKET_RIGHT_BACK, "steel_shelves", 1.48, 0.0, None),
    ),
    "clinic": (
        (_POCKET_LEFT, "cabinet", 0.92, 0.03, ("medicine", 0.12, 0.20, 0.08, 0.24, 0.10)),
        (_POCKET_RIGHT_MID, "tool_cart", 0.84, -0.04, ("soap", 0.14, 0.22, 0.08, 0.26, -0.12)),
        (_POCKET_RIGHT_BACK, "refrigerator", 1.52, 0.0, None),
    ),
    "cafe": (
        (_POCKET_LEFT, "cabinet", 0.88, 0.03, ("coffee_service", 0.20, 0.30, 0.13, 0.28, 0.08)),
        (_POCKET_RIGHT_MID, "chair", 0.84, -0.18, None),
        (_POCKET_RIGHT_BACK, "refrigerator", 1.46, 0.0, None),
    ),
    "lab": (
        (_POCKET_LEFT, "tool_cart", 0.84, 0.04, ("water", 0.18, 0.25, 0.08, 0.28, 0.06)),
        (_POCKET_RIGHT_MID, "shop_stool", 0.70, -0.12, None),
        (_POCKET_RIGHT_BACK, "refrigerator", 1.50, 0.0, None),
    ),
    "parcel_sorting": (
        (_POCKET_LEFT, "cabinet", 0.90, 0.03, ("folder", 0.24, 0.32, 0.14, 0.16, -0.10)),
        (_POCKET_RIGHT_MID, "bin", 0.50, -0.06, None),
        (_POCKET_RIGHT_BACK, "steel_shelves", 1.48, 0.0, None),
    ),
    "shaft_repair": (
        (_POCKET_LEFT, "tool_chest", 0.96, 0.03, ("oil_can", 0.16, 0.24, 0.09, 0.28, -0.14)),
        (_POCKET_RIGHT_MID, "bin", 0.46, -0.05, None),
        (_POCKET_RIGHT_BACK, "drill_press", 1.56, -0.08, None),
    ),
    "electronics_lab": (
        (_POCKET_LEFT, "tool_chest", 0.90, 0.04, ("laptop", 0.28, 0.36, 0.15, 0.28, 0.14)),
        (_POCKET_RIGHT_MID, "desk_chair", 0.92, -0.20, None),
        (_POCKET_RIGHT_BACK, "industrial_lamp", 1.60, -0.12, None),
    ),
    "print_bindery": (
        (_POCKET_LEFT, "tool_cart", 0.84, 0.04, ("photo_books", 0.22, 0.30, 0.13, 0.22, 0.08)),
        (_POCKET_RIGHT_MID, "stock_box", 0.44, -0.05, None),
        (_POCKET_RIGHT_BACK, "industrial_lamp", 1.56, -0.10, None),
    ),
    "library": (
        (_POCKET_LEFT, "cabinet", 0.92, 0.03, ("book", 0.18, 0.27, 0.12, 0.26, 0.10)),
        (_POCKET_RIGHT_MID, "chair", 0.84, -0.14, None),
        (_POCKET_RIGHT_BACK, "steel_shelves", 1.52, 0.0, None),
    ),
    "packing_bay": (
        (_POCKET_LEFT, "tool_cart", 0.84, 0.04, ("stapler", 0.12, 0.19, 0.08, 0.16, 0.12)),
        (_POCKET_RIGHT_MID, "carton", 0.48, -0.06, None),
        (_POCKET_RIGHT_BACK, "shipping_crate", 0.58, 0.02, None),
    ),
}


def _resolve_case(k):
    if isinstance(k, int):
        return _CANONICAL_CASES[k % len(_CANONICAL_CASES)]
    s = str(k).strip().lower()
    for sep in ("-", " ", "/", "."):
        s = s.replace(sep, "_")
    while "__" in s:
        s = s.replace("__", "_")
    if s in _SCENE_RECIPES:
        return s
    # Match more specific keywords before generic ones (e.g. electronics_lab before lab).
    keyword_map = (
        ("electronics", "electronics_lab"),
        ("circuit", "electronics_lab"),
        ("pcb", "electronics_lab"),
        ("warehouse", "warehouse"),
        ("depot", "warehouse"),
        ("clinic", "clinic"),
        ("medical", "clinic"),
        ("pharmacy", "clinic"),
        ("cafe", "cafe"),
        ("coffee", "cafe"),
        ("bistro", "cafe"),
        ("parcel", "parcel_sorting"),
        ("sort", "parcel_sorting"),
        ("mail", "parcel_sorting"),
        ("shaft", "shaft_repair"),
        ("repair", "shaft_repair"),
        ("machin", "shaft_repair"),
        ("cnc", "shaft_repair"),
        ("print", "print_bindery"),
        ("bindery", "print_bindery"),
        ("press", "print_bindery"),
        ("library", "library"),
        ("archive", "library"),
        ("packing", "packing_bay"),
        ("pack", "packing_bay"),
        ("shipping", "packing_bay"),
        ("lab", "lab"),
    )
    for token, target in keyword_map:
        if token in s:
            return target
    idx = sum(ord(ch) for ch in s) % len(_CANONICAL_CASES)
    return _CANONICAL_CASES[idx]


def _get_native_size_m(inst):
    col = getattr(inst, "instance_collection", None)
    if col is None:
        return None
    raw = None
    try:
        raw = col["size_m"]
    except Exception:
        return None
    if raw is None or len(raw) != 3:
        return None
    sx, sy, sz = float(raw[0]), float(raw[1]), float(raw[2])
    if sx <= 1e-6 or sy <= 1e-6 or sz <= 1e-6:
        return None
    return (sx, sy, sz)


def _scaled_dims(inst, size_arg):
    native = _get_native_size_m(inst)
    if native is None:
        return None
    sx, sy, sz = native
    if size_arg is not None and float(size_arg) > 1e-6:
        scale_factor = float(size_arg) / sz
    else:
        sc = getattr(inst, "scale", (1.0, 1.0, 1.0))
        scale_factor = abs(float(sc[2])) if abs(float(sc[2])) > 1e-6 else 1.0
    return (sx * scale_factor, sy * scale_factor, sz * scale_factor)


def _rotated_footprint(w, d, yaw):
    c = abs(math.cos(yaw))
    s = abs(math.sin(yaw))
    return (w * c + d * s, w * s + d * c)


def _rescale_in_place(inst, anchor_xyz, factor):
    if abs(factor - 1.0) <= 1e-6:
        return
    ax, ay, az = float(anchor_xyz[0]), float(anchor_xyz[1]), float(anchor_xyz[2])
    sx, sy, sz = inst.scale
    inst.scale = (sx * factor, sy * factor, sz * factor)
    lx, ly, lz = inst.location
    inst.location = (
        ax + factor * (lx - ax),
        ay + factor * (ly - ay),
        az + factor * (lz - az),
    )


def _instance_world_matrix(inst):
    if getattr(inst, "rotation_mode", "XYZ") == "QUATERNION":
        rot_q = inst.rotation_quaternion.copy()
    else:
        rot_q = inst.rotation_euler.to_quaternion()
    return Matrix.LocRotScale(Vector(inst.location), rot_q, Vector(inst.scale))


def _obj_matrix_in_collection(obj):
    chain = []
    cur = obj
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chain.append(cur)
        cur = cur.parent
    mat = Matrix.Identity(4)
    for node in reversed(chain):
        if node.parent is not None:
            mat = mat @ node.matrix_parent_inverse @ node.matrix_basis
        else:
            mat = mat @ node.matrix_basis
    return mat


def _point_in_tri_2d(px, py, a, b, c, eps=1e-3):
    ax, ay = a
    bx, by = b
    cx, cy = c
    v0x, v0y = cx - ax, cy - ay
    v1x, v1y = bx - ax, by - ay
    v2x, v2y = px - ax, py - ay
    denom = v0x * v1y - v1x * v0y
    if abs(denom) < 1e-10:
        return False
    inv = 1.0 / denom
    u = (v2x * v1y - v1x * v2y) * inv
    v = (v0x * v2y - v2x * v0y) * inv
    return u >= -eps and v >= -eps and (u + v) <= 1.0 + eps


def _find_verified_top_surface(base_inst, base_xyz, base_h, req_radius, req_clearance):
    """Inspect real mesh polygons inside base_inst.instance_collection to find a
    verified, flat, solid, unobstructed horizontal support surface.
    Never treats a bounding-box upper tip as a support surface.
    Returns (px, py, z_surf, safe_radius) or None.
    """
    col = getattr(base_inst, "instance_collection", None)
    if col is None or base_h <= 1e-4:
        return None
    mesh_objs = [
        o for o in col.all_objects
        if o.type == "MESH" and o.data is not None and len(o.data.vertices) >= 3
    ]
    if not mesh_objs:
        return None

    offset = Vector(getattr(col, "instance_offset", (0.0, 0.0, 0.0)))
    base_to_world = _instance_world_matrix(base_inst) @ Matrix.Translation(-offset)

    mesh_z_min = float("inf")
    all_tri_bounds = []
    up_tris = []
    min_support_z = float(base_xyz[2]) + 0.58 * float(base_h)

    for obj in mesh_objs:
        mesh = obj.data
        m_world = base_to_world @ _obj_matrix_in_collection(obj)
        det_sign = -1.0 if m_world.determinant() < 0.0 else 1.0
        verts = [m_world @ v.co for v in mesh.vertices]
        if not verts:
            continue
        for v in verts:
            if v.z < mesh_z_min:
                mesh_z_min = v.z

        tri_indices = []
        try:
            mesh.calc_loop_triangles()
            if mesh.loop_triangles:
                tri_indices = [tuple(lt.vertices) for lt in mesh.loop_triangles]
        except Exception:
            tri_indices = []
        if not tri_indices:
            for poly in mesh.polygons:
                pv = poly.vertices
                for i in range(1, len(pv) - 1):
                    tri_indices.append((pv[0], pv[i], pv[i + 1]))

        for i0, i1, i2 in tri_indices:
            p0, p1, p2 = verts[i0], verts[i1], verts[i2]
            tz_min = min(p0.z, p1.z, p2.z)
            tz_max = max(p0.z, p1.z, p2.z)
            tx_min = min(p0.x, p1.x, p2.x)
            tx_max = max(p0.x, p1.x, p2.x)
            ty_min = min(p0.y, p1.y, p2.y)
            ty_max = max(p0.y, p1.y, p2.y)
            all_tri_bounds.append((tz_min, tz_max, tx_min, tx_max, ty_min, ty_max))

            normal = (p1 - p0).cross(p2 - p0) * det_sign
            double_area = normal.length
            if double_area <= 1e-8:
                continue
            if (normal.z / double_area) < 0.992:
                continue
            if (tz_max - tz_min) > 0.008:
                continue
            tz_avg = (p0.z + p1.z + p2.z) / 3.0
            if tz_avg < min_support_z:
                continue
            up_tris.append((
                tz_avg,
                0.5 * double_area,
                (p0.x, p0.y),
                (p1.x, p1.y),
                (p2.x, p2.y),
            ))

    # Fail safe if mesh world Z does not match the expected grounded base Z.
    if not math.isfinite(mesh_z_min) or abs(mesh_z_min - float(base_xyz[2])) > 0.045:
        return None
    if not up_tris:
        return None

    # Group upward-facing flat triangles into height clusters (highest first).
    up_tris.sort(key=lambda item: item[0], reverse=True)
    used = [False] * len(up_tris)
    clusters = []
    for i, tri in enumerate(up_tris):
        if used[i]:
            continue
        z0 = tri[0]
        group = []
        for j in range(i, len(up_tris)):
            if not used[j] and abs(up_tris[j][0] - z0) <= 0.006:
                used[j] = True
                group.append(up_tris[j])
        clusters.append(group)

    min_area = max(0.045, math.pi * req_radius * req_radius * 1.4)
    bx, by = float(base_xyz[0]), float(base_xyz[1])
    pocket_half = 0.5 * _MAX_POCKET_FOOTPRINT

    for group in clusters:
        total_area = sum(t[1] for t in group)
        if total_area < min_area:
            continue
        z_surf = sum(t[0] * t[1] for t in group) / total_area
        cx = sum(((t[2][0] + t[3][0] + t[4][0]) / 3.0) * t[1] for t in group) / total_area
        cy = sum(((t[2][1] + t[3][1] + t[4][1]) / 3.0) * t[1] for t in group) / total_area

        xs = [pt[0] for t in group for pt in (t[2], t[3], t[4])]
        ys = [pt[1] for t in group for pt in (t[2], t[3], t[4])]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = req_radius + 0.02
        if (max_x - min_x) < 2.0 * margin or (max_y - min_y) < 2.0 * margin:
            continue

        lo_x, hi_x = min_x + margin, max_x - margin
        lo_y, hi_y = min_y + margin, max_y - margin
        candidates = []
        if lo_x <= cx <= hi_x and lo_y <= cy <= hi_y:
            candidates.append((cx, cy))
        steps = 5
        for ix in range(steps):
            fx = ix / (steps - 1) if steps > 1 else 0.5
            px = lo_x + fx * (hi_x - lo_x)
            for iy in range(steps):
                fy = iy / (steps - 1) if steps > 1 else 0.5
                py = lo_y + fy * (hi_y - lo_y)
                candidates.append((px, py))
        candidates.sort(key=lambda pt: (pt[0] - cx) ** 2 + (pt[1] - cy) ** 2)

        probe_r = 0.85 * req_radius
        clear_r = req_radius + 0.02
        z_clear_lo = z_surf + 0.012
        z_clear_hi = z_surf + req_clearance

        for px, py in candidates:
            # Keep the tabletop prop strictly within the pocket footprint bounds.
            if abs(px - bx) + req_radius > pocket_half or abs(py - by) + req_radius > pocket_half:
                continue

            # Require solid flat polygon support under center and all 4 base corners.
            probes = (
                (px, py),
                (px - probe_r, py - probe_r),
                (px - probe_r, py + probe_r),
                (px + probe_r, py - probe_r),
                (px + probe_r, py + probe_r),
            )
            supported = True
            for qx, qy in probes:
                if not any(_point_in_tri_2d(qx, qy, t[2], t[3], t[4]) for t in group):
                    supported = False
                    break
            if not supported:
                continue

            # Reject if any part of base_inst protrudes above z_surf in the prop volume.
            obstructed = False
            for tz_min, tz_max, tx_min, tx_max, ty_min, ty_max in all_tri_bounds:
                if tz_max <= z_clear_lo or tz_min >= z_clear_hi:
                    continue
                if tx_max >= px - clear_r and tx_min <= px + clear_r and ty_max >= py - clear_r and ty_min <= py + clear_r:
                    obstructed = True
                    break
            if obstructed:
                continue

            edge_margin = min(px - min_x, max_x - px, py - min_y, max_y - py) - 0.015
            pocket_margin = min(pocket_half - abs(px - bx), pocket_half - abs(py - by))
            safe_r = max(req_radius, min(edge_margin, pocket_margin))
            return (px, py, z_surf, safe_r)

    return None


def _place_floor_asset(place, key, xyz, target_h, yaw):
    inst = place(key, xyz, size=target_h, yaw=yaw)
    if inst is None:
        return None, None
    dims = _scaled_dims(inst, target_h)
    if dims is None:
        return inst, (0.0, 0.0, float(target_h))
    w, d, h = dims
    rot_x, rot_y = _rotated_footprint(w, d, yaw)
    max_foot = max(rot_x, rot_y)
    if max_foot > _MAX_POCKET_FOOTPRINT:
        factor = _MAX_POCKET_FOOTPRINT / max_foot
        _rescale_in_place(inst, xyz, factor)
        w, d, h = w * factor, d * factor, h * factor
    return inst, (w, d, h)


def _place_verified_top_prop(place, base_inst, base_xyz, base_h, prop_spec):
    prop_key, min_dim, max_dim, req_radius, req_clearance, yaw = prop_spec
    surface = _find_verified_top_surface(
        base_inst, base_xyz, base_h, req_radius, req_clearance
    )
    if surface is None:
        return None
    px, py, pz, safe_r = surface
    anchor = (px, py, pz)
    inst = place(prop_key, anchor, size=None, yaw=yaw)
    if inst is None:
        return None

    dims = _scaled_dims(inst, None)
    if dims is not None:
        w, d, h = dims
        cur_max = max(w, d, h)
        factor = 1.0
        if cur_max > max_dim:
            factor = max_dim / cur_max
        elif cur_max < min_dim and cur_max > 1e-6:
            factor = min_dim / cur_max

        rot_x, rot_y = _rotated_footprint(w * factor, d * factor, yaw)
        max_span = max(rot_x, rot_y)
        allowed_span = max(0.06, 2.0 * safe_r)
        if max_span > allowed_span:
            factor *= allowed_span / max_span

        _rescale_in_place(inst, anchor, factor)
    return inst


def dress(k, place):
    case_key = _resolve_case(k)
    recipe = _SCENE_RECIPES[case_key]
    placed = []

    for pocket_xyz, base_key, target_h, yaw, top_prop in recipe:
        base_inst, dims = _place_floor_asset(place, base_key, pocket_xyz, target_h, yaw)
        if base_inst is None:
            continue
        placed.append(base_inst)
        if top_prop is not None and dims is not None:
            prop_inst = _place_verified_top_prop(
                place, base_inst, pocket_xyz, dims[2], top_prop
            )
            if prop_inst is not None:
                placed.append(prop_inst)

    return placed
