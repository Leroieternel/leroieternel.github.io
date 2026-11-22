import numpy as np

_PRESENT = (
    (0.018, -0.012, 0.022, 0.09, "trim item +0.09 rad yaw for upright clearance"),
    (-0.016, 0.014, 0.018, -0.10, "trim item -0.10 rad yaw for balanced carry"),
    (0.012, 0.010, 0.026, 0.08, "present item +0.08 rad yaw at elevated carry"),
    (-0.020, -0.010, 0.020, -0.11, "present item -0.11 rad yaw clear of aisle side"),
    (0.015, 0.012, 0.016, 0.10, "present item +0.10 rad yaw for level settle"),
)

_ROOMS = (
    (-0.10, 2.6, 0.095, (1.00, 0.96, 0.90), 280.0, (0.87, 0.93, 1.00), 40.0, (1.00, 0.86, 0.70), 0.26, (0.84, 0.91, 1.00)),
    (-0.15, 2.2, 0.125, (0.99, 0.98, 0.95), 320.0, (0.90, 0.95, 1.00), 35.0, (1.00, 0.88, 0.74), 0.30, (0.88, 0.93, 1.00)),
    (-0.05, 2.8, 0.085, (1.00, 0.97, 0.92), 260.0, (0.86, 0.93, 1.00), 42.0, (1.00, 0.87, 0.72), 0.25, (0.85, 0.91, 0.99)),
    (-0.12, 2.4, 0.110, (1.00, 0.95, 0.88), 300.0, (0.88, 0.93, 1.00), 45.0, (1.00, 0.85, 0.69), 0.28, (0.86, 0.91, 0.98)),
    (-0.08, 2.5, 0.105, (1.00, 0.94, 0.86), 270.0, (0.89, 0.93, 1.00), 48.0, (1.00, 0.85, 0.68), 0.24, (0.86, 0.90, 0.97)),
)


def _carry_times(dock):
    if dock >= 17.2:
        return 11.8, 13.4, 15.0, 16.6
    if dock >= 14.8:
        dt = (dock - 11.4) / 3.0
        return 11.1, 11.1 + dt, 11.1 + 2.0 * dt, 11.1 + 3.0 * dt
    return None


def _build_drive(k):
    from world import ROUTES, CHECKPOINTS, PICK_X, DEST_X
    from missions import X0, XE

    route = [(0.0, (X0, 0.0)), (0.4, (X0, 0.0)), (4.8, (PICK_X, 0.0)), (11.0, (PICK_X, 0.0))]
    path = [(PICK_X, 0.0), *ROUTES[k], (DEST_X, 0.0)]
    cp = np.asarray(CHECKPOINTS[k][1:], dtype=float)
    segs = list(zip(path, path[1:]))
    last = len(segs) - 1
    aux_wp = next(
        (i - 1 for i, p in enumerate(path[1:-1], 1)
         if np.linalg.norm(np.subtract(p, cp)) >= 0.001
         and np.linalg.norm(np.subtract(p, (PICK_X, 0.0))) > 0.25
         and np.linalg.norm(np.subtract(p, (DEST_X, 0.0))) > 0.25),
        None,
    )
    split_seg = None if aux_wp is not None else int(np.argmax([
        float(np.linalg.norm(np.subtract(b, a))) * (0.70 if i == last else 1.0)
        for i, (a, b) in enumerate(segs)
    ]))
    arrival = aux_t = aux_pt = None
    sq_dur = 1.6
    for i, (a, b) in enumerate(segs):
        pa, pb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        dist = float(np.linalg.norm(pb - pa))
        sq_len = min(0.36, 0.30 * dist) if (i == last and dist > 0.05) else 0.0
        end_c = pb - (pb - pa) * (sq_len / dist) if sq_len > 0.0 else pb
        end_pt = (float(end_c[0]), float(end_c[1])) if sq_len > 0.0 else b
        if i == last:
            sq_dur = max(1.6, (sq_len if sq_len > 0.0 else dist) * 5.2)
        if i == last and sq_len == 0.0:
            route.append((route[-1][0] + sq_dur, b))
        elif i == split_seg and float(np.linalg.norm(end_c - pa)) > 0.05:
            mid = 0.5 * (pa + end_c)
            aux_pt = (float(mid[0]), float(mid[1]))
            route.append((route[-1][0] + float(np.linalg.norm(mid - pa)) * 2.77, aux_pt))
            aux_t = route[-1][0]
            route.append((aux_t + 0.55, aux_pt))
            d2 = float(np.linalg.norm(end_c - mid))
            if d2 > 1e-6:
                route.append((route[-1][0] + d2 * 2.77, end_pt))
            if sq_len > 0.0:
                route.append((route[-1][0] + sq_dur, b))
        else:
            dc = float(np.linalg.norm(end_c - pa))
            if dc > 1e-6:
                route.append((route[-1][0] + dc * 2.77, end_pt))
            if sq_len > 0.0:
                route.append((route[-1][0] + sq_dur, b))
        if i < last:
            if np.linalg.norm(np.subtract(b, cp)) < 0.001:
                arrival = route[-1][0]
                route.append((arrival + 0.68, b))
            elif i == aux_wp:
                aux_t, aux_pt = route[-1][0], (float(pb[0]), float(pb[1]))
                route.append((aux_t + 0.55, b))
    dock = route[-1][0]
    depart = dock + 9.0
    route.extend([(depart, (DEST_X, 0.0)), (depart + 3.7, (XE, 0.0)), (depart + 4.6, (XE, 0.0))])
    return route, dock, arrival, aux_t, aux_pt, sq_dur


def base_plan(k):
    route, dock, arrival, _, _, _ = _build_drive(k)
    return route, dock, arrival


def arm_plan(k, safe, m, arm, t, dock):
    from world import Y, HZ, TOP, PICK_TOP

    yaw0, carry = np.pi / 2, [-0.05, 0.319, 1.17]
    source = [0.0, Y, PICK_TOP + HZ[k] + 0.001 - (0.0025 if k == 4 else 0.0)]
    xs = ([-0.105, -0.080, 0.0, 0.115, -0.075][k] if not safe else [0.0, 0.0, 0.0, 0.115, 0.012][k])
    height = TOP + HZ[k] + 0.007 + (xs * 0.13 if k == 4 else 0.0)
    p, over = [xs, Y, height], [xs, Y, 1.15]
    knots = [
        (0.0, carry, yaw0), (4.8, carry, yaw0), (5.7, [0.0, Y, 1.14], yaw0),
        (6.70, source, yaw0), (7.54, source, yaw0), (8.70, [0.0, Y, 1.16], yaw0), (10.50, carry, yaw0),
    ]
    ct = _carry_times(dock)
    if ct is not None:
        t0, t1, t2, t3 = ct
        dx, dy, dz, dyaw, _ = _PRESENT[k]
        pose = [carry[0] + dx, carry[1] + dy, carry[2] + dz]
        knots.extend([(t0, carry, yaw0), (t1, pose, yaw0 + dyaw), (t2, pose, yaw0 + dyaw), (t3, carry, yaw0)])
    knots.append((dock + 0.23, carry, yaw0))
    if k == 3 and not safe:
        knots.extend([
            (dock + 1.5, [-0.126, Y, 1.15], yaw0), (dock + 2.6, [-0.126, Y, height + 0.020], yaw0),
            (dock + 4.5, [p[0], p[1], height + 0.020], yaw0), (dock + 5.0, p, yaw0),
        ])
    else:
        knots.extend([(dock + 1.8, over, yaw0), (dock + 3.40, p, yaw0)])
    release = dock + (3.55 if (k == 2 and not safe) else 5.16)
    knots.extend([(release + 0.40, p, yaw0), (dock + 6.90, over, yaw0), (dock + 8.7, carry, yaw0), (t[-1], carry, yaw0)])
    return arm.trajectory(knots, t), release, xs


def extra_steps(k, dock, arrival):
    _, _, _, aux_t, aux_pt, sq_dur = _build_drive(k)
    steps = []
    ct = _carry_times(dock)
    if ct is not None:
        t0, t1, t2, t3 = ct
        _, _, _, dyaw, desc = _PRESENT[k]
        steps.extend([
            (float(t0), f"Begin free-space carry presentation: {desc}"),
            (float(t1), f"Hold presented orientation ({dyaw:+.2f} rad yaw) for {t2 - t1:.2f} s settle"),
            (float(t3), "Return arm to neutral carry posture before docking"),
        ])
    if aux_t is not None and aux_pt is not None:
        steps.append((float(aux_t), f"Dwell 0.55 s at intermediate drive checkpoint ({aux_pt[0]:.2f}, {aux_pt[1]:.2f})"))
    steps.append((float(dock - sq_dur), f"Begin slow square-up approach to destination dock ({sq_dur:.2f} s)"))
    steps.sort(key=lambda item: item[0])
    return steps


def camera(k, x, phase, base, receiver_y=0.65):
    sign = 1.0 if k in (2, 4) else -1.0
    if phase == "wide":
        pos = ((-3.3, -8.1, 3.15), (2.5, -7.9, 2.85), (-2.9, -8.0, 2.7), (2.8, -8.1, 3.15), (-2.4, -8.0, 2.8))[k - 1]
        return pos, (0.0, 0.9, 1.18), 26
    if phase == "eyelevel":
        return (sign * 3.55, -3.45, 1.52), (-sign * 0.20, 0.45, 1.04), 28
    if phase == "pick":
        return (-3.90, -1.08, 1.80), (-2.66, 0.40, 0.89), 39
    if phase == "follow":
        return (sign * 0.85, -4.55, 1.38), (0.0, 0.15, 0.95), 28
    if phase == "approach":
        return (4.16, -2.55, 1.82), (2.43, 0.37, 0.89), 34
    if phase == "action":
        return (3.68, -0.23, 1.66), (2.60, receiver_y, 0.85), 43
    if phase == "detail":
        return (3.39, -0.01, 1.39), (2.60, receiver_y, 0.84), 46
    raise ValueError(phase)


def lighting(scene, k):
    exp, sun_e, sun_a, sun_c, win_e, win_c, prac_e, prac_c, bg_s, bg_c = _ROOMS[k - 1]
    vs = getattr(scene, "view_settings", None)
    if vs is not None:
        vs.exposure = exp
        if hasattr(vs, "gamma"):
            vs.gamma = 1.0
        for attr, val in (("view_transform", "AgX"), ("look", "None")):
            if hasattr(vs, attr):
                try:
                    setattr(vs, attr, val)
                except (TypeError, ValueError):
                    pass
    cyc = getattr(scene, "cycles", None)
    if cyc is not None:
        if hasattr(cyc, "use_animated_seed"):
            cyc.use_animated_seed = False
        if hasattr(cyc, "seed"):
            cyc.seed = 0
    nt = getattr(getattr(scene, "world", None), "node_tree", None)
    if nt is not None:
        for node in nt.nodes:
            if getattr(node, "type", None) == "BACKGROUND":
                c_in, s_in = node.inputs.get("Color"), node.inputs.get("Strength")
                if c_in is not None and not c_in.is_linked:
                    c_in.default_value = (*bg_c, 1.0)
                if s_in is not None and not s_in.is_linked:
                    s_in.default_value = bg_s
    lights = [o for o in getattr(scene, "objects", ()) if getattr(o, "type", None) == "LIGHT" and getattr(o, "data", None) is not None]
    is_win = lambda o: getattr(o.data, "type", None) == "AREA" and (any(w in getattr(o, "name", "").lower() for w in ("win", "day", "sky", "portal")) or max(getattr(o.data, "size", 0.0), getattr(o.data, "size_y", 0.0)) >= 0.8)
    n_sun = max(1, sum(1 for o in lights if getattr(o.data, "type", None) == "SUN"))
    n_win = max(1, sum(1 for o in lights if is_win(o)))
    for obj in lights:
        ld, lt = obj.data, getattr(obj.data, "type", "")
        if hasattr(ld, "use_temperature"):
            ld.use_temperature = False
        if lt == "SUN":
            ld.color, ld.energy = sun_c, sun_e / n_sun
            if hasattr(ld, "angle"):
                ld.angle = sun_a
        elif is_win(obj):
            ld.color, ld.energy = win_c, win_e / n_win
            if hasattr(ld, "spread"):
                ld.spread = 1.80
        elif lt == "AREA":
            ld.color, ld.energy = prac_c, prac_e * 0.85
            if hasattr(ld, "spread"):
                ld.spread = 2.15
        elif lt in ("POINT", "SPOT"):
            ld.color, ld.energy = prac_c, prac_e * (1.5 if lt == "SPOT" else 1.0)
            if hasattr(ld, "shadow_soft_size"):
                ld.shadow_soft_size = max(getattr(ld, "shadow_soft_size", 0.0), 0.18)
            if lt == "SPOT" and hasattr(ld, "spot_blend"):
                ld.spot_blend = max(getattr(ld, "spot_blend", 0.0), 0.45)
