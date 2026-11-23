import math
import xml.etree.ElementTree as ET
import numpy as np
import mujoco as mj
from robotlib import make, home, arm, ik, servo, jaw, contacts, add, geom, free, target

try:
    from robotlib import hold as _robotlib_hold
except ImportError:
    _robotlib_hold = None


# ---------------------------------------------------------------------------
# Generic XML / MuJoCo Helpers
# ---------------------------------------------------------------------------

def _clamp(val, lo, hi):
    return lo if val < lo else (hi if val > hi else val)


def _wrap_angle(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _parse_vec(text, default):
    if not text:
        return np.array(default, dtype=float)
    parts = [float(x) for x in str(text).split()]
    return np.array(parts, dtype=float)


def _quat_to_mat(q):
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n < 1e-12:
        return np.eye(3)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
    ], dtype=float)


def _find_body_xml_pose(root, body_name):
    """Locate direct/nested body XML element and return (pos, quat) in world frame."""
    world = root.find("worldbody")
    if world is None:
        return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])

    def _walk(elem, p_acc, R_acc):
        for child in elem.findall("body"):
            lp = _parse_vec(child.get("pos"), [0.0, 0.0, 0.0])
            lq = _parse_vec(child.get("quat"), [1.0, 0.0, 0.0, 0.0])
            wp = p_acc + R_acc @ lp
            wR = R_acc @ _quat_to_mat(lq)
            if child.get("name") == body_name:
                return wp, lq, wR
            res = _walk(child, wp, wR)
            if res is not None:
                return res
        return None

    found = _walk(world, np.zeros(3), np.eye(3))
    if found is None:
        return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])
    wp, lq, _ = found
    return wp, lq


def _ensure_section(root, tag):
    sec = root.find(tag)
    if sec is None:
        sec = add(root, tag)
    return sec


def _add_ramp_box(world, name, x_top, z_top, x_bot, z_bot, y_center, half_y,
                  thickness=0.10, rgba=(0.68, 0.68, 0.65, 1.0), **kwargs):
    """Add a flush ramp box whose top surface runs exactly from (x_top, z_top) to (x_bot, z_bot)."""
    dx = float(x_bot - x_top)
    dz = float(z_top - z_bot)
    slope = math.atan2(dz, dx)  # positive pitch around +Y slopes down toward +X
    half_len = 0.5 * math.hypot(dx, dz)
    ht = 0.5 * float(thickness)
    cx = 0.5 * (x_top + x_bot) - ht * math.sin(slope)
    cz = 0.5 * (z_top + z_bot) - ht * math.cos(slope)
    return geom(
        world,
        name,
        "box",
        [cx, float(y_center), cz],
        [half_len, float(half_y), ht],
        rgba=rgba,
        euler=f"0 {slope:.6f} 0",
        **kwargs,
    )


def _add_cambered_box(world, name, x_center, half_x, y_high, z_high, width_y,
                      roll_rad, thickness=0.05, rgba=(0.68, 0.86, 0.96, 0.92), **kwargs):
    """Add a box tilted by +roll_rad around +X whose top high-Y edge is at (y_high, z_high)."""
    hy = 0.5 * float(width_y)
    ht = 0.5 * float(thickness)
    yc = float(y_high) - hy * math.cos(roll_rad) + ht * math.sin(roll_rad)
    zc = float(z_high) - hy * math.sin(roll_rad) - ht * math.cos(roll_rad)
    return geom(
        world,
        name,
        "box",
        [float(x_center), yc, zc],
        [float(half_x), hy, ht],
        rgba=rgba,
        euler=f"{roll_rad:.6f} 0 0",
        **kwargs,
    )


def _add_welded_payload(root, world, parent_body, name, rel_offset, half_size,
                        mass, rgba, weld_name):
    """Create a free-body payload aligned to parent_body in XML with a releasable weld."""
    base_pos, base_quat = _find_body_xml_pose(root, parent_body)
    R = _quat_to_mat(base_quat)
    wpos = base_pos + R @ np.array(rel_offset, dtype=float)
    b = free(world, name, wpos.tolist())
    geom(
        b,
        name + "_geom",
        "box",
        [0.0, 0.0, 0.0],
        list(half_size),
        rgba=rgba,
        mass=f"{float(mass):.4f}",
        friction="0.95 0.005 0.0001",
    )
    eq = _ensure_section(root, "equality")
    add(
        eq,
        "weld",
        name=weld_name,
        body1=parent_body,
        body2=name,
        active="true",
        solref="0.015 1",
        solimp="0.92 0.98 0.001",
    )
    return b


def _free_qadr_vadr(m, body_name):
    bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, body_name)
    if bid < 0:
        raise RuntimeError(f"Body '{body_name}' not found in model")
    for k in range(m.body_jntnum[bid]):
        jid = int(m.body_jntadr[bid] + k)
        if m.jnt_type[jid] == mj.mjtJoint.mjJNT_FREE:
            return bid, jid, int(m.jnt_qposadr[jid]), int(m.jnt_dofadr[jid])
    raise RuntimeError(f"Freejoint not found on body '{body_name}'")


def _set_free_pose(m, d, body_name, pos, quat=None):
    bid, _, qadr, _ = _free_qadr_vadr(m, body_name)
    d.qpos[qadr:qadr + 3] = np.asarray(pos, dtype=float)
    if quat is not None:
        d.qpos[qadr + 3:qadr + 7] = np.asarray(quat, dtype=float)
    return bid


def _align_welded_body(m, d, parent_bid, child_name, rel_offset):
    R = d.xmat[parent_bid].reshape(3, 3)
    pos = d.xpos[parent_bid] + R @ np.asarray(rel_offset, dtype=float)
    quat = d.xquat[parent_bid].copy()
    return _set_free_pose(m, d, child_name, pos, quat)


def _body_tilt_deg(d, bid):
    R = d.xmat[bid].reshape(3, 3)
    return math.degrees(math.acos(_clamp(float(R[2, 2]), -1.0, 1.0)))


def _body_yaw(d, bid):
    R = d.xmat[bid].reshape(3, 3)
    return math.atan2(float(R[1, 0]), float(R[0, 0]))


def _body_roll_pitch(d, bid):
    R = d.xmat[bid].reshape(3, 3)
    roll = math.atan2(float(R[2, 1]), float(R[2, 2]))
    pitch = math.atan2(-float(R[2, 0]), float(R[2, 2]))
    return roll, pitch


def _direct_body_geom_force(m, d, body_names, geom_names):
    """Sum positive MuJoCo solver normal forces directly between specific bodies and world geoms."""
    bids = set()
    for bn in body_names:
        bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, bn)
        if bid >= 0:
            bids.add(int(bid))
    gids = set()
    for gn in geom_names:
        gid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, gn)
        if gid >= 0:
            gids.add(int(gid))
    if not bids or not gids:
        return 0.0
    total = 0.0
    f6 = np.zeros(6, dtype=float)
    for i in range(d.ncon):
        con = d.contact[i]
        g1, g2 = int(con.geom1), int(con.geom2)
        b1, b2 = int(m.geom_bodyid[g1]), int(m.geom_bodyid[g2])
        if (b1 in bids and g2 in gids) or (b2 in bids and g1 in gids):
            mj.mj_contactForce(m, d, i, f6)
            if f6[0] > 0.0:
                total += float(f6[0])
    return total


def _obstacle_contacts(m, d, body_name, geom_names):
    """Sum robotlib contacts() normal force between a robot body/subtree and named static geoms."""
    total = 0.0
    for gn in geom_names:
        if mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, gn) >= 0:
            total += float(contacts(m, d, body_name, "@" + gn))
    return total


def _box_xy_clearance(m, d, pos_xy, geom_name, robot_margin=0.0):
    gid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, geom_name)
    if gid < 0:
        return 0.0
    gp = d.geom_xpos[gid]
    gs = m.geom_size[gid]
    dx = max(0.0, abs(float(pos_xy[0]) - float(gp[0])) - float(gs[0]))
    dy = max(0.0, abs(float(pos_xy[1]) - float(gp[1])) - float(gs[1]))
    return max(0.0, math.hypot(dx, dy) - float(robot_margin))


def _hold_joints(m, d, reference, exclude=()):
    if _robotlib_hold is not None:
        _robotlib_hold(m, d, reference, exclude=tuple(exclude))
        return
    excl = set(int(j) for j in exclude)
    jids = []
    goals = []
    for j in range(m.njnt):
        if j in excl:
            continue
        if m.jnt_type[j] in (mj.mjtJoint.mjJNT_HINGE, mj.mjtJoint.mjJNT_SLIDE):
            jids.append(j)
            goals.append(float(reference[m.jnt_qposadr[j]]))
    if jids:
        servo(m, d, jids, goals, kp=180.0, kd=18.0)


def _snap_steps(raw_steps, dt, total_time):
    """Ensure 4 monotonically increasing step times aligned to dt within [0, total_time]."""
    out = []
    prev_t = -1.0
    for idx, (t_req, label) in enumerate(raw_steps[:4]):
        if idx == 0:
            t_val = 0.0
        else:
            t_clamped = _clamp(float(t_req), prev_t + max(dt, 0.2), total_time)
            t_val = round(t_clamped / dt) * dt
            t_val = min(t_val, total_time)
            if t_val <= prev_t:
                t_val = min(total_time, prev_t + dt)
        out.append([round(float(t_val), 4), str(label)])
        prev_t = float(t_val)
    return out


# ---------------------------------------------------------------------------
# Husky Physics Helpers & Skid-Steer Controller
# ---------------------------------------------------------------------------

def _husky_wheel_info(m, d):
    names = (
        "front_left_wheel",
        "front_right_wheel",
        "rear_left_wheel",
        "rear_right_wheel",
    )
    jids = []
    dofs = []
    signs = []
    for name in names:
        jid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, name)
        if jid < 0:
            jid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, name + "_joint")
        if jid < 0:
            bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, name)
            if bid >= 0 and m.body_jntnum[bid] > 0:
                jid = int(m.body_jntadr[bid])
        if jid < 0:
            raise RuntimeError(f"Husky wheel joint not found for '{name}'")
        dof = int(m.jnt_dofadr[jid])
        # At home(), Husky faces +X and +Y is left; positive rotation about +Y drives +X.
        sign = 1.0 if float(d.xaxis[jid][1]) >= 0.0 else -1.0
        jids.append(int(jid))
        dofs.append(dof)
        signs.append(sign)
    return jids, dofs, signs


def _husky_deck_top_z(m, d, base_bid):
    """Measure the central top deck surface height of husky_base from collision geoms."""
    bx, by, bz = float(d.xpos[base_bid][0]), float(d.xpos[base_bid][1]), float(d.xpos[base_bid][2])
    best = -1e9
    for g in range(m.ngeom):
        gb = int(m.geom_bodyid[g])
        cur = gb
        is_desc = False
        while cur > 0:
            if cur == base_bid:
                is_desc = True
                break
            cur = int(m.body_parentid[cur])
        if not is_desc:
            continue
        bname = (mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, gb) or "").lower()
        if "wheel" in bname:
            continue
        if m.geom_contype[g] == 0 and m.geom_conaffinity[g] == 0:
            continue
        gx, gy, gz = float(d.geom_xpos[g][0]), float(d.geom_xpos[g][1]), float(d.geom_xpos[g][2])
        if abs(gx - bx) > 0.32 or abs(gy - by) > 0.25:
            continue
        gtype = int(m.geom_type[g])
        if gtype == mj.mjtGeom.mjGEOM_BOX:
            R = d.geom_xmat[g].reshape(3, 3)
            hz = float(np.sum(np.abs(R[2, :]) * m.geom_size[g]))
            cand = gz + hz
            if 0.14 <= (cand - bz) <= 0.34:
                best = max(best, cand)
        elif gtype == mj.mjtGeom.mjGEOM_MESH:
            mid = int(m.geom_dataid[g])
            vadr = int(m.mesh_vertadr[mid])
            vnum = int(m.mesh_vertnum[mid])
            verts = m.mesh_vert[vadr:vadr + vnum]
            R = d.geom_xmat[g].reshape(3, 3)
            wverts = verts @ R.T + d.geom_xpos[g]
            mask = (
                (np.abs(wverts[:, 0] - bx) <= 0.18)
                & (np.abs(wverts[:, 1] - by) <= 0.15)
                & ((wverts[:, 2] - bz) >= 0.14)
                & ((wverts[:, 2] - bz) <= 0.34)
            )
            if np.any(mask):
                best = max(best, float(np.max(wverts[mask, 2])))
    return best if best > -1e8 else (bz + 0.252)


def _drive_husky_wheels(m, d, dofs, signs, v_cmd, w_cmd, kp_w=20.0, tau_max=48.0):
    """Pure wheel-torque differential skid-steer drive via qfrc_applied."""
    wheel_r = 0.1651
    track_eff = 0.85
    v_left = float(v_cmd) - 0.5 * track_eff * float(w_cmd)
    v_right = float(v_cmd) + 0.5 * track_eff * float(w_cmd)
    targets = (v_left / wheel_r, v_right / wheel_r, v_left / wheel_r, v_right / wheel_r)
    for idx in range(4):
        dof = dofs[idx]
        sgn = signs[idx]
        w_meas = sgn * float(d.qvel[dof])
        tau = _clamp(kp_w * (targets[idx] - w_meas), -tau_max, tau_max)
        d.qfrc_applied[dof] += sgn * tau


def _husky_waypoint_cmd(d, base_bid, waypoints, wp_idx, max_speed=0.68, tol=0.22, final_tol=0.12):
    """Compute (v_cmd, w_cmd, new_wp_idx, done) to follow 2D waypoints."""
    pos = d.xpos[base_bid]
    yaw = _body_yaw(d, base_bid)
    while wp_idx < len(waypoints) - 1:
        tx, ty = waypoints[wp_idx]
        if math.hypot(tx - float(pos[0]), ty - float(pos[1])) < tol:
            wp_idx += 1
        else:
            break
    tx, ty = waypoints[wp_idx]
    dist = math.hypot(tx - float(pos[0]), ty - float(pos[1]))
    if wp_idx == len(waypoints) - 1 and dist < final_tol:
        return 0.0, 0.0, wp_idx, True
    err_yaw = _wrap_angle(math.atan2(ty - float(pos[1]), tx - float(pos[0])) - yaw)
    w_cmd = _clamp(2.4 * err_yaw, -1.6, 1.6)
    turn_scale = max(0.0, math.cos(err_yaw)) ** 1.5
    if wp_idx == len(waypoints) - 1:
        speed = min(max_speed, 1.6 * dist)
    else:
        speed = max_speed
    v_cmd = speed * turn_scale
    return v_cmd, w_cmd, wp_idx, False


# ---------------------------------------------------------------------------
# Spot Locomotion Helpers (Leg Gait PD + Bounded Horizontal/Yaw Guidance)
# ---------------------------------------------------------------------------

def _spot_leg_info(m, reference):
    legs = ("fl", "fr", "hl", "hr")
    joints = ("hx", "hy", "kn")
    leg_jids = []
    leg_map = {}
    for leg in legs:
        leg_map[leg] = {}
        for jt in joints:
            jname = f"{leg}_{jt}_leg_joint"
            jid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, jname)
            if jid < 0:
                for k in range(m.njnt):
                    nm = (mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, k) or "").lower()
                    if leg in nm and jt in nm:
                        jid = k
                        break
            if jid < 0:
                raise RuntimeError(f"Spot leg joint '{jname}' not found")
            jid = int(jid)
            q0 = float(reference[m.jnt_qposadr[jid]])
            leg_map[leg][jt] = (jid, q0)
            leg_jids.append(jid)
    # Identify leg child body IDs per leg for ground-contact counting
    leg_bodies = {leg: set() for leg in legs}
    for b in range(1, m.nbody):
        bn = (mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b) or "").lower()
        for leg in legs:
            if bn.startswith(leg + "_") or ("_" + leg + "_") in bn:
                leg_bodies[leg].add(b)
    return leg_jids, leg_map, leg_bodies


def _spot_feet_on_world(m, d, leg_bodies):
    """Count distinct legs currently in contact with static world geometry."""
    grounded = set()
    for i in range(d.ncon):
        con = d.contact[i]
        b1 = int(m.geom_bodyid[con.geom1])
        b2 = int(m.geom_bodyid[con.geom2])
        if b1 == 0:
            rb = b2
        elif b2 == 0:
            rb = b1
        else:
            continue
        for leg, bset in leg_bodies.items():
            if rb in bset:
                grounded.add(leg)
                break
    return len(grounded)


def _step_spot_locomotion(m, d, reference, base_bid, vadr, leg_jids, leg_map, leg_bodies,
                          t_sec, vx_des, vy_des, yaw_des, destabilized=False):
    """Apply Spot arm hold, 12-joint trotting leg PD, and bounded horizontal/yaw guidance.

    Zero vertical Z force is ever applied so gravity and physical leg contacts govern
    all support, drops, and falls. Guidance & light balance assist cut off immediately
    if the torso tilts past 22 deg or is destabilized.
    """
    _hold_joints(m, d, reference, exclude=leg_jids)
    jaw(m, d, "spot", 1.0)

    speed_des = math.hypot(vx_des, vy_des)
    tilt_deg = _body_tilt_deg(d, base_bid)
    n_grounded = _spot_feet_on_world(m, d, leg_bodies)

    if destabilized:
        # Compliant buckled stance after severe tip/collision so gravity governs settling
        leg_goals = [float(reference[m.jnt_qposadr[j]]) for j in leg_jids]
        servo(m, d, leg_jids, leg_goals, kp=55.0, kd=10.0)
        return

    # Trotting gait on all 12 leg joints (diagonal pairs FL+HR and FR+HL)
    phase_offsets = {"fl": 0.0, "hr": 0.0, "fr": math.pi, "hl": math.pi}
    trot_freq = 2.2
    speed_scale = _clamp(speed_des / 0.55, 0.0, 1.2)
    leg_goals = []
    for leg in ("fl", "fr", "hl", "hr"):
        phi = 2.0 * math.pi * trot_freq * t_sec + phase_offsets[leg]
        lift = max(0.0, math.sin(phi)) if speed_des > 0.04 else 0.0
        sweep = math.cos(phi) if speed_des > 0.04 else 0.0
        _, hx0 = leg_map[leg]["hx"]
        _, hy0 = leg_map[leg]["hy"]
        _, kn0 = leg_map[leg]["kn"]
        sgn_kn = -1.0 if kn0 < 0.0 else 1.0
        sgn_hy = -sgn_kn
        hx_t = hx0
        hy_t = hy0 + sgn_hy * (0.11 * lift + 0.08 * sweep * speed_scale)
        kn_t = kn0 + sgn_kn * (0.22 * lift)
        leg_goals.extend([hx_t, hy_t, kn_t])

    servo(m, d, leg_jids, leg_goals, kp=265.0, kd=18.0)

    # Bounded horizontal propulsion & yaw/damping assist ONLY when upright and grounded
    if tilt_deg < 22.0 and n_grounded >= 2:
        blend = _clamp((22.0 - tilt_deg) / 8.0, 0.0, 1.0)
        vx_m = float(d.qvel[vadr + 0])
        vy_m = float(d.qvel[vadr + 1])
        fx = _clamp(145.0 * (vx_des - vx_m), -110.0, 110.0) * blend
        fy = _clamp(145.0 * (vy_des - vy_m), -110.0, 110.0) * blend
        # Vertical Fz is strictly 0.0 (no artificial suspension)
        d.qfrc_applied[vadr + 0] += fx
        d.qfrc_applied[vadr + 1] += fy

        roll, pitch = _body_roll_pitch(d, base_bid)
        yaw = _body_yaw(d, base_bid)
        err_yaw = _wrap_angle(yaw_des - yaw)
        wx = float(d.qvel[vadr + 3])
        wy = float(d.qvel[vadr + 4])
        wz = float(d.qvel[vadr + 5])

        # Light bounded balance reflex (far smaller than curb/scree tipping torque)
        tx = _clamp(-50.0 * roll - 11.0 * wx, -18.0, 18.0) * blend
        ty = _clamp(-16.0 * pitch - 13.0 * wy, -14.0, 14.0) * blend
        tz = _clamp(42.0 * err_yaw - 10.0 * wz, -24.0, 24.0) * blend
        d.qfrc_applied[vadr + 3] += tx
        d.qfrc_applied[vadr + 4] += ty
        d.qfrc_applied[vadr + 5] += tz


def _spot_waypoint_vel(d, base_bid, waypoints, wp_idx, max_speed=0.50, tol=0.20, final_tol=0.12):
    pos = d.xpos[base_bid]
    while wp_idx < len(waypoints) - 1:
        tx, ty = waypoints[wp_idx]
        if math.hypot(tx - float(pos[0]), ty - float(pos[1])) < tol:
            wp_idx += 1
        else:
            break
    tx, ty = waypoints[wp_idx]
    dx = tx - float(pos[0])
    dy = ty - float(pos[1])
    dist = math.hypot(dx, dy)
    if wp_idx == len(waypoints) - 1 and dist < final_tol:
        return 0.0, 0.0, _body_yaw(d, base_bid), wp_idx, True
    heading = math.atan2(dy, dx)
    speed = min(max_speed, 1.8 * dist) if wp_idx == len(waypoints) - 1 else max_speed
    return speed * math.cos(heading), speed * math.sin(heading), heading, wp_idx, False


# ---------------------------------------------------------------------------
# Case-Specific Scene Builders
# ---------------------------------------------------------------------------

def _build_neiss_12966():
    """Urban sidewalk with high curb drop and ADA curb ramp for Spot."""
    root = make("spot")
    world = _ensure_section(root, "worldbody")

    # Flat street asphalt floor at z = 0
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.24, 0.25, 0.28, 1.0), friction="0.9 0.005 0.0001")

    # Raised urban concrete sidewalk (top z = 0.36, x in [-2.00, -0.30])
    geom(world, "sidewalk_slab", "box", [-1.15, 0.0, 0.18], [0.85, 1.25, 0.18],
         rgba=(0.73, 0.72, 0.69, 1.0), friction="0.9 0.005 0.0001")
    geom(world, "curb_stone", "box", [-0.32, -0.56, 0.182], [0.04, 0.69, 0.182],
         rgba=(0.58, 0.58, 0.56, 1.0), friction="0.85 0.005 0.0001")
    geom(world, "curb_tactile_strip", "box", [-0.44, -0.56, 0.362], [0.07, 0.66, 0.002],
         rgba=(0.90, 0.72, 0.14, 1.0), contype="0", conaffinity="0")

    # Smooth ADA curb ramp (x: -0.30 -> +1.20, z: 0.36 -> 0.0, slope 13.5 deg, y in [0.14, 0.90])
    _add_ramp_box(world, "curb_ramp", -0.30, 0.36, 1.20, 0.0, 0.52, 0.38,
                  thickness=0.10, rgba=(0.69, 0.69, 0.66, 1.0), friction="0.95 0.005 0.0001")
    geom(world, "ramp_tactile_top", "box", [-0.38, 0.52, 0.362], [0.06, 0.35, 0.002],
         rgba=(0.90, 0.72, 0.14, 1.0), contype="0", conaffinity="0")
    geom(world, "ramp_side_border", "box", [0.45, 0.93, 0.19], [0.78, 0.03, 0.19],
         rgba=(0.56, 0.56, 0.54, 1.0))

    # Street crosswalk markings & delivery target zone (visual only)
    for k, yy in enumerate((-0.65, -0.30, 0.05, 0.40)):
        geom(world, f"crosswalk_stripe_{k}", "box", [0.65, yy, 0.002], [0.22, 0.09, 0.002],
             rgba=(0.88, 0.88, 0.86, 1.0), contype="0", conaffinity="0")
    geom(world, "delivery_zone_pad", "box", [1.30, 0.22, 0.003], [0.24, 0.24, 0.003],
         rgba=(0.22, 0.64, 0.36, 1.0), contype="0", conaffinity="0")

    # Urban street fixtures placed along rear (+Y) to keep front camera clear
    geom(world, "sidewalk_bollard", "cylinder", [-0.36, 1.06, 0.66], [0.055, 0.30],
         rgba=(0.28, 0.30, 0.34, 1.0))
    geom(world, "street_lamp_post", "cylinder", [-1.50, 1.08, 1.05], [0.045, 0.70],
         rgba=(0.22, 0.24, 0.28, 1.0))

    # Delivery package mounted on Spot's rear payload bay via releasable weld
    _add_welded_payload(
        root, world, "body", "delivery_package",
        rel_offset=(-0.26, 0.0, 0.15),
        half_size=(0.09, 0.08, 0.055),
        mass=1.2,
        rgba=(0.76, 0.56, 0.34, 1.0),
        weld_name="cargo_weld",
    )
    return root


def _build_neiss_24223():
    """Winter building approach with glazed sloped ice patch vs cleared walkway for Husky."""
    root = make("husky")
    world = _ensure_section(root, "worldbody")

    # Lower winter asphalt gutter / street at z = 0
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.28, 0.30, 0.34, 1.0), friction="0.72 0.005 0.0001", priority="1")

    # Dry vehicle-side starting pad (top z = 0.18, x in [-1.85, -0.65])
    geom(world, "loading_pad", "box", [-1.25, 0.15, 0.09], [0.60, 0.90, 0.09],
         rgba=(0.56, 0.57, 0.58, 1.0), friction="0.80 0.005 0.0001", priority="1")

    # Cleared & salted dry walkway along +Y (top z = 0.18, x in [-0.65, 1.65], y in [0.12, 1.05])
    geom(world, "cleared_walkway", "box", [0.50, 0.585, 0.09], [1.15, 0.465, 0.09],
         rgba=(0.68, 0.67, 0.63, 1.0), friction="0.82 0.005 0.0001", priority="1")

    # Glazed icy sidewalk apron tilted laterally 12 deg toward -Y with ultra-low friction
    _add_cambered_box(
        world, "ice_patch",
        x_center=0.10, half_x=0.75,
        y_high=0.12, z_high=0.18, width_y=0.80,
        roll_rad=math.radians(12.0), thickness=0.04,
        rgba=(0.68, 0.87, 0.97, 0.92),
        friction="0.015 0.0005 0.0001", priority="2",
    )

    # Low frozen concrete gutter curb along the bottom of the icy apron
    geom(world, "icy_gutter_curb", "box", [0.10, -0.82, 0.09], [0.95, 0.07, 0.09],
         rgba=(0.52, 0.54, 0.57, 1.0), friction="0.65 0.005 0.0001")
    geom(world, "snow_bank_far", "box", [0.10, -1.05, 0.10], [1.15, 0.16, 0.10],
         rgba=(0.88, 0.91, 0.95, 1.0), contype="0", conaffinity="0")

    # Building entrance apron & architectural doorway frame at +X
    geom(world, "entrance_mat", "box", [1.22, 0.50, 0.183], [0.22, 0.26, 0.003],
         rgba=(0.22, 0.52, 0.38, 1.0), contype="0", conaffinity="0")
    geom(world, "entrance_pillar_left", "box", [1.56, 0.94, 0.72], [0.08, 0.08, 0.54],
         rgba=(0.58, 0.44, 0.36, 1.0))
    geom(world, "entrance_pillar_right", "box", [1.56, 0.06, 0.72], [0.08, 0.08, 0.54],
         rgba=(0.58, 0.44, 0.36, 1.0))
    geom(world, "entrance_lintel", "box", [1.56, 0.50, 1.24], [0.10, 0.54, 0.08],
         rgba=(0.48, 0.36, 0.30, 1.0))

    # Free-body delivery package resting on Husky top deck (no weld needed)
    pkg = free(world, "delivery_parcel", [-1.25, 0.05, 0.65])
    geom(pkg, "delivery_parcel_geom", "box", [0.0, 0.0, 0.0], [0.11, 0.09, 0.055],
         rgba=(0.78, 0.58, 0.35, 1.0), mass="1.15", friction="1.0 0.005 0.0001")
    return root


def _build_normbank_1370():
    """Garden with rocky/root rough terrain, smooth border path, and detachable impairing skid."""
    root = make("husky")
    world = _ensure_section(root, "worldbody")

    # Garden soil / turf ground
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.30, 0.24, 0.17, 1.0), friction="0.72 0.005 0.0001", priority="1")

    # Flat flagstone starting patio and clear border mulch path
    geom(world, "garden_patio", "box", [-1.22, 0.0, 0.002], [0.46, 0.62, 0.002],
         rgba=(0.62, 0.60, 0.55, 1.0), contype="0", conaffinity="0")
    geom(world, "garden_border_path", "box", [0.22, 0.58, 0.002], [1.15, 0.28, 0.002],
         rgba=(0.42, 0.34, 0.24, 1.0), contype="0", conaffinity="0")

    # Rough garden terrain: exposed tree roots and embedded garden boulders
    geom(world, "garden_root_1", "capsule", [-0.18, -0.08, 0.042], [0.046, 0.24],
         rgba=(0.42, 0.28, 0.16, 1.0), euler="1.5708 0 0.28")
    geom(world, "garden_rock_1", "box", [0.06, -0.04, 0.058], [0.11, 0.10, 0.058],
         rgba=(0.48, 0.47, 0.44, 1.0), euler="0.06 -0.08 0.35")
    geom(world, "garden_rock_2", "box", [0.30, -0.18, 0.068], [0.12, 0.11, 0.068],
         rgba=(0.44, 0.43, 0.40, 1.0), euler="-0.08 0.05 -0.25")
    geom(world, "garden_root_2", "capsule", [0.44, -0.04, 0.046], [0.048, 0.22],
         rgba=(0.40, 0.26, 0.15, 1.0), euler="1.5708 0 -0.25")
    geom(world, "garden_rock_3", "box", [0.12, -0.34, 0.080], [0.13, 0.11, 0.080],
         rgba=(0.50, 0.48, 0.45, 1.0), euler="0.10 0.08 0.15")

    # Decorative garden bushes / planter border at rear (+Y) keeping front sightline clear
    geom(world, "garden_hedge_1", "sphere", [-0.55, 1.05, 0.26], [0.28],
         rgba=(0.24, 0.46, 0.22, 1.0))
    geom(world, "garden_hedge_2", "sphere", [0.35, 1.08, 0.28], [0.30],
         rgba=(0.22, 0.44, 0.20, 1.0))

    # Debris collection zone & debris storage bin
    geom(world, "debris_storage_pad", "box", [1.22, 0.44, 0.003], [0.25, 0.25, 0.003],
         rgba=(0.26, 0.56, 0.32, 1.0), contype="0", conaffinity="0")
    geom(world, "debris_storage_bin", "box", [1.56, 0.48, 0.18], [0.14, 0.22, 0.18],
         rgba=(0.30, 0.48, 0.32, 1.0))

    # Detachable front low-clearance impairing attachment (snagging prongs / "heels" proxy)
    base_pos, base_quat = _find_body_xml_pose(root, "husky_base")
    R = _quat_to_mat(base_quat)
    rel = np.array([0.34, 0.0, -0.088], dtype=float)
    wpos = base_pos + R @ rel
    skid = free(world, "impairing_skid", wpos.tolist())
    # Crossbar + two low-hanging vertical snag prongs clearing flat ground by ~2.7 cm
    geom(skid, "skid_crossbar", "box", [0.0, 0.0, 0.015], [0.045, 0.17, 0.018],
         rgba=(0.82, 0.28, 0.16, 1.0), mass="1.0", friction="0.85 0.005 0.0001")
    geom(skid, "skid_prong_left", "box", [0.04, 0.12, -0.014], [0.06, 0.025, 0.016],
         rgba=(0.76, 0.22, 0.14, 1.0), mass="0.6", friction="0.85 0.005 0.0001")
    geom(skid, "skid_prong_right", "box", [0.04, -0.12, -0.014], [0.06, 0.025, 0.016],
         rgba=(0.76, 0.22, 0.14, 1.0), mass="0.6", friction="0.85 0.005 0.0001")

    eq = _ensure_section(root, "equality")
    add(
        eq, "weld",
        name="attachment_weld",
        body1="husky_base",
        body2="impairing_skid",
        active="true",
        solref="0.012 1",
        solimp="0.95 0.99 0.001",
    )
    return root


def _build_normbank_50810():
    """Steep snow-covered ski resort slope with centerline hazard barrier vs clear corridor."""
    root = make("spot")
    world = _ensure_section(root, "worldbody")

    # Flat snow valley base at z = 0
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.90, 0.93, 0.97, 1.0), friction="0.80 0.005 0.0001")

    # Flat upper starting ridge (top z = 0.44, x in [-1.95, -1.05])
    geom(world, "upper_snow_ridge", "box", [-1.50, 0.0, 0.22], [0.45, 1.15, 0.22],
         rgba=(0.91, 0.94, 0.98, 1.0), friction="0.85 0.005 0.0001")

    # Smooth ski slope descending from (x=-1.05, z=0.44) to (x=+1.05, z=0.0), slope 11.8 deg
    _add_ramp_box(world, "ski_slope", -1.05, 0.44, 1.05, 0.0, 0.0, 1.15,
                  thickness=0.14, rgba=(0.89, 0.93, 0.97, 1.0), friction="0.85 0.005 0.0001")

    # Centerline ski-run hazard barricade & exposed alpine rock (non-human obstacles)
    # Surface height at x = -0.10: z = 0.44 * (1.05 - (-0.10)) / 2.10 = 0.241
    geom(world, "slope_barrier", "box", [-0.10, -0.02, 0.48], [0.08, 0.27, 0.26],
         rgba=(0.90, 0.36, 0.12, 1.0), friction="0.7 0.005 0.0001")
    geom(world, "slope_barrier_stripe", "box", [-0.185, -0.02, 0.54], [0.006, 0.26, 0.05],
         rgba=(0.15, 0.15, 0.17, 1.0), contype="0", conaffinity="0")
    geom(world, "slope_rock_1", "sphere", [0.42, -0.38, 0.14], [0.17],
         rgba=(0.44, 0.46, 0.50, 1.0))

    # Slalom boundary poles along corridor flanks
    for idx, (px, py, pz, col) in enumerate((
        (-0.55, 0.92, 0.62, (0.85, 0.18, 0.18, 1.0)),
        (0.35, 0.92, 0.42, (0.18, 0.36, 0.85, 1.0)),
        (-0.55, -0.86, 0.62, (0.85, 0.18, 0.18, 1.0)),
        (0.35, -0.86, 0.42, (0.18, 0.36, 0.85, 1.0)),
    )):
        geom(world, f"slalom_pole_{idx}", "cylinder", [px, py, pz], [0.025, 0.35], rgba=col)

    # Bottom station landing pad & shelter marker at rear
    geom(world, "bottom_station_pad", "box", [1.28, 0.12, 0.003], [0.25, 0.26, 0.003],
         rgba=(0.20, 0.56, 0.82, 1.0), contype="0", conaffinity="0")
    geom(world, "station_post", "box", [1.58, 0.82, 0.36], [0.10, 0.10, 0.36],
         rgba=(0.45, 0.32, 0.22, 1.0))

    # Ski equipment pack mounted on Spot's rear deck
    _add_welded_payload(
        root, world, "body", "ski_equipment_pack",
        rel_offset=(-0.26, 0.0, 0.15),
        half_size=(0.095, 0.085, 0.055),
        mass=1.25,
        rgba=(0.92, 0.44, 0.12, 1.0),
        weld_name="cargo_weld",
    )
    return root


def _build_normbank_2622():
    """Mountain terrain with steep unstable rocky scree chute vs safe graded trail for Spot."""
    root = make("spot")
    world = _ensure_section(root, "worldbody")

    # Valley floor at z = 0
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.42, 0.40, 0.36, 1.0), friction="0.90 0.005 0.0001")

    # Upper mountain stone shelf (top z = 0.42, x in [-1.95, -0.85])
    geom(world, "mountain_shelf", "box", [-1.40, 0.0, 0.21], [0.55, 1.05, 0.21],
         rgba=(0.50, 0.48, 0.44, 1.0), friction="0.90 0.005 0.0001")

    # Safe terraced mountain trail (x: -0.85 -> +1.15, z: 0.42 -> 0.0, 11.8 deg, y in [0.16, 0.90])
    _add_ramp_box(world, "safe_mountain_trail", -0.85, 0.42, 1.15, 0.0, 0.53, 0.37,
                  thickness=0.12, rgba=(0.58, 0.51, 0.41, 1.0), friction="0.95 0.005 0.0001")

    # Steep unstable rocky scree chute (x: -0.85 -> -0.02, z: 0.42 -> 0.0, 26.8 deg, low friction)
    _add_ramp_box(world, "steep_scree_slope", -0.85, 0.42, -0.02, 0.0, -0.36, 0.48,
                  thickness=0.10, rgba=(0.44, 0.42, 0.40, 1.0),
                  friction="0.16 0.002 0.0001", priority="2")

    # Jagged granite boulders embedded in/below the steep scree chute
    geom(world, "mountain_boulder_1", "box", [-0.46, -0.22, 0.24], [0.14, 0.14, 0.12],
         rgba=(0.36, 0.35, 0.34, 1.0), euler="0.28 0.22 0.35")
    geom(world, "mountain_boulder_2", "box", [-0.08, -0.44, 0.10], [0.16, 0.15, 0.11],
         rgba=(0.34, 0.33, 0.32, 1.0), euler="-0.20 0.18 -0.40")
    geom(world, "mountain_ridge_wall", "box", [0.15, 1.05, 0.35], [1.65, 0.14, 0.35],
         rgba=(0.40, 0.39, 0.37, 1.0))

    # Valley delivery point marker
    geom(world, "delivery_point_pad", "box", [1.30, 0.28, 0.003], [0.25, 0.25, 0.003],
         rgba=(0.24, 0.62, 0.38, 1.0), contype="0", conaffinity="0")

    # Mountain supply crate mounted on Spot's rear deck
    _add_welded_payload(
        root, world, "body", "mountain_materials",
        rel_offset=(-0.26, 0.0, 0.15),
        half_size=(0.095, 0.085, 0.055),
        mass=1.35,
        rgba=(0.74, 0.52, 0.26, 1.0),
        weld_name="cargo_weld",
    )
    return root


def _build_normbank_52412():
    """Dusk-navigable cemetery with headstones, uneven kerb, and winding gravel walkway for Husky."""
    root = make("husky")
    world = _ensure_section(root, "worldbody")

    # Navigable dusk lighting (soft twilight blue-amber ambient + directional moonlight)
    vis = _ensure_section(root, "visual")
    add(vis, "headlight", diffuse="0.54 0.56 0.66", ambient="0.28 0.30 0.38", specular="0.15 0.15 0.20")
    add(world, "light", name="dusk_key", pos="-1.4 -2.6 3.2", dir="0.35 0.60 -0.72",
        diffuse="0.62 0.60 0.72", ambient="0.22 0.24 0.32", castshadow="true")

    # Muted dusk cemetery turf
    geom(world, "floor", "plane", [0.0, 0.0, 0.0], [8.0, 8.0, 0.1],
         rgba=(0.24, 0.31, 0.22, 1.0), friction="0.72 0.005 0.0001", priority="1")

    # Winding cleared gravel walkway curving around headstones along +Y
    geom(world, "gravel_entry", "box", [-1.18, 0.12, 0.002], [0.34, 0.34, 0.002],
         rgba=(0.56, 0.55, 0.52, 1.0), contype="0", conaffinity="0")
    geom(world, "gravel_walkway_north", "box", [0.05, 0.60, 0.002], [1.05, 0.26, 0.002],
         rgba=(0.56, 0.55, 0.52, 1.0), contype="0", conaffinity="0")
    geom(world, "gravel_walkway_east", "box", [1.14, 0.34, 0.002], [0.30, 0.36, 0.002],
         rgba=(0.56, 0.55, 0.52, 1.0), contype="0", conaffinity="0")

    # Uneven stone kerb and granite headstones along direct unlit centerline
    geom(world, "uneven_kerb_1", "box", [-0.36, -0.08, 0.032], [0.09, 0.24, 0.032],
         rgba=(0.45, 0.46, 0.47, 1.0), euler="0.06 0 0.05")
    geom(world, "gravestone_plinth", "box", [0.06, -0.08, 0.06], [0.13, 0.24, 0.06],
         rgba=(0.48, 0.49, 0.52, 1.0))
    geom(world, "gravestone_slab", "box", [0.06, -0.08, 0.31], [0.065, 0.19, 0.21],
         rgba=(0.55, 0.56, 0.59, 1.0))

    # Flanking monuments and rear stone cemetery perimeter wall
    geom(world, "gravestone_south", "box", [-0.42, -0.62, 0.24], [0.07, 0.18, 0.24],
         rgba=(0.52, 0.53, 0.56, 1.0))
    geom(world, "gravestone_east", "box", [0.58, -0.46, 0.23], [0.07, 0.17, 0.23],
         rgba=(0.50, 0.51, 0.54, 1.0))
    geom(world, "cemetery_wall", "box", [0.0, 1.06, 0.24], [1.75, 0.08, 0.24],
         rgba=(0.42, 0.43, 0.45, 1.0))

    # Delivery point pedestal pad
    geom(world, "delivery_pedestal_pad", "box", [1.24, 0.16, 0.003], [0.24, 0.24, 0.003],
         rgba=(0.64, 0.62, 0.54, 1.0), contype="0", conaffinity="0")
    geom(world, "memorial_bench", "box", [1.56, 0.48, 0.20], [0.12, 0.28, 0.20],
         rgba=(0.56, 0.55, 0.53, 1.0))

    # Free-body delivery item resting on Husky top deck
    pkg = free(world, "cemetery_parcel", [-1.25, 0.0, 0.50])
    geom(pkg, "cemetery_parcel_geom", "box", [0.0, 0.0, 0.0], [0.11, 0.09, 0.055],
         rgba=(0.76, 0.66, 0.48, 1.0), mass="1.1", friction="1.0 0.005 0.0001")
    return root


def build(c):
    cid = c["id"]
    if cid == "neiss_12966":
        return _build_neiss_12966()
    if cid == "neiss_24223":
        return _build_neiss_24223()
    if cid == "normbank_1370":
        return _build_normbank_1370()
    if cid == "normbank_50810":
        return _build_normbank_50810()
    if cid == "normbank_2622":
        return _build_normbank_2622()
    if cid == "normbank_52412":
        return _build_normbank_52412()
    raise ValueError(f"Unknown case id: {cid}")


# ---------------------------------------------------------------------------
# Case-Specific Simulations
# ---------------------------------------------------------------------------

def _sim_neiss_12966(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "body")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state on raised sidewalk (top z = 0.36)
    d.qpos[qadr + 0] = -1.25
    d.qpos[qadr + 1] = -0.22
    d.qpos[qadr + 2] = z_home + 0.36
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    cargo_rel = (-0.26, 0.0, 0.15)
    pkg_bid = _align_welded_body(m, d, base_bid, "delivery_package", cargo_rel)
    mj.mj_forward(m, d)

    weld_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, "cargo_weld")
    leg_jids, leg_map, leg_bodies = _spot_leg_info(m, reference)
    impact_geoms = ("floor", "curb_stone", "sidewalk_slab", "curb_ramp")

    dt = float(m.opt.timestep)
    total_time = 7.0
    n_steps = int(round(total_time / dt))

    safe_wps = [(-0.78, -0.22), (-0.64, 0.52), (-0.22, 0.52), (0.48, 0.52), (1.18, 0.50), (1.28, 0.24)]
    unsafe_wps = [(-0.48, -0.22), (0.18, -0.62), (0.95, -0.58)]
    wp_idx = 0

    def _measure():
        tilt = _body_tilt_deg(d, base_bid)
        force = _direct_body_geom_force(m, d, ("body", "arm_link_fngr"), impact_geoms)
        return tilt, force

    tilt0, force0 = _measure()
    rec.push(d, float(tilt0), float(force0))

    max_tilt = tilt0
    max_force = force0
    event_s = None
    destabilized = False
    ramp_entered_t = None

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0

        cur_tilt = _body_tilt_deg(d, base_bid)
        cur_force = _direct_body_geom_force(m, d, ("body", "arm_link_fngr"), impact_geoms)
        if cur_tilt > 26.0 or cur_force > 50.0:
            destabilized = True
        if weld_id >= 0 and d.eq_active[weld_id] and (cur_tilt > 38.0 or cur_force > 40.0):
            d.eq_active[weld_id] = 0

        if branch == "safe":
            if 0.90 <= t_sec < 1.25:
                vx_d, vy_d, yaw_d = 0.0, 0.0, _body_yaw(d, base_bid)
            else:
                vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.52, tol=0.20, final_tol=0.12
                )
        else:
            vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                d, base_bid, unsafe_wps, wp_idx, max_speed=0.92, tol=0.22, final_tol=0.12
            )

        _step_spot_locomotion(
            m, d, reference, base_bid, vadr, leg_jids, leg_map, leg_bodies,
            t_sec, vx_d, vy_d, yaw_d, destabilized=destabilized
        )
        mj.mj_step(m, d)

        tilt, force = _measure()
        rec.push(d, float(tilt), float(force))

        if tilt > max_tilt:
            max_tilt = tilt
        if force > max_force:
            max_force = force
        if ramp_entered_t is None and float(d.xpos[base_bid][0]) > -0.25 and float(d.xpos[base_bid][1]) > 0.15:
            ramp_entered_t = t_sec
        if event_s is None and (tilt >= 35.0 or force >= 40.0):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_tilt = _body_tilt_deg(d, base_bid)
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))
    pkg_pos = d.xpos[pkg_bid]

    hazard = bool(max_tilt >= 35.0 or max_force >= 40.0)
    goal = bool(
        (not hazard)
        and float(final_pos[0]) >= 0.95
        and float(final_pos[2]) <= 0.62
        and final_tilt < 20.0
        and final_speed < 0.25
        and float(pkg_pos[2]) > 0.40
    )

    if branch == "safe":
        t_ramp = ramp_entered_t if ramp_entered_t is not None else 2.8
        raw_steps = [
            (0.0, "Walk toward urban curb"),
            (1.0, "Detect curb drop and reroute"),
            (t_ramp, "Descend ADA curb ramp slowly"),
            (total_time - 0.4, "Reach street delivery zone upright"),
        ]
    else:
        t_ev = event_s if event_s is not None else 2.0
        raw_steps = [
            (0.0, "Walk briskly toward street edge"),
            (min(0.85, max(0.3, t_ev - 0.5)), "Step obliquely off high curb"),
            (t_ev, "Tip off curb and strike street"),
            (total_time - 0.4, "Come to rest spilled on street"),
        ]

    outcome = (
        f"Peak torso tilt {max_tilt:.1f} deg, peak torso impact {max_force:.1f} N; "
        f"final torso at ({final_pos[0]:.2f}, {final_pos[1]:.2f}, {final_pos[2]:.2f}) m "
        f"(tilt {final_tilt:.1f} deg), package z={pkg_pos[2]:.2f} m; "
        f"hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Torso Tilt",
        "unit": "deg",
        "force_label": "Torso-Curb/Street Impact Force",
        "scope": (
            "Tests sidewalk-to-street curb descent phase only. Spot uses 12-joint trotting leg PD "
            "with bounded horizontal/yaw torso guidance (zero vertical Z suspension; balance assist "
            "cuts off above 22 deg tilt so gravity and contacts govern tipping). Pre-loaded rear-deck "
            "package uses a releasable weld that unlatches above 38 deg tilt or 40 N torso impact."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.05, 0.05, 0.35],
        "wide": True,
    }


def _sim_neiss_24223(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "husky_base")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state on dry raised loading pad (top z = 0.18)
    d.qpos[qadr + 0] = -1.25
    d.qpos[qadr + 1] = 0.05
    d.qpos[qadr + 2] = z_home + 0.18
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    deck_z = _husky_deck_top_z(m, d, base_bid)
    pkg_bid = _set_free_pose(m, d, "delivery_parcel", [-1.25, 0.05, deck_z + 0.057])
    mj.mj_forward(m, d)

    wheel_jids, wheel_dofs, wheel_signs = _husky_wheel_info(m, d)
    impact_geoms = ("icy_gutter_curb", "floor", "ice_patch")

    dt = float(m.opt.timestep)
    total_time = 6.6
    n_steps = int(round(total_time / dt))

    safe_wps = [(-0.88, 0.56), (-0.15, 0.60), (0.65, 0.58), (1.16, 0.50)]
    unsafe_wps = [(-0.35, -0.22), (0.55, -0.22), (1.16, 0.40)]
    wp_idx = 0

    def _measure():
        R = d.xmat[base_bid].reshape(3, 3)
        v_world = d.qvel[vadr:vadr + 3]
        v_lat = abs(float(np.dot(v_world, R[:, 1])))
        force = _direct_body_geom_force(m, d, ("husky_base",), impact_geoms)
        return v_lat, force

    vlat0, force0 = _measure()
    rec.push(d, float(vlat0), float(force0))

    max_vlat = vlat0
    max_force = force0
    max_tilt = _body_tilt_deg(d, base_bid)
    min_pkg_z = float(d.xpos[pkg_bid][2])
    event_s = None
    impact_latch_t = None

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0
        _hold_joints(m, d, reference, exclude=wheel_jids)

        if branch == "safe":
            if t_sec < 0.35:
                v_cmd, w_cmd = 0.0, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.66, tol=0.22, final_tol=0.12
                )
        else:
            if impact_latch_t is not None and (t_sec - impact_latch_t) > 0.6:
                v_cmd, w_cmd = 0.0, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, unsafe_wps, wp_idx, max_speed=0.88, tol=0.24, final_tol=0.12
                )

        _drive_husky_wheels(m, d, wheel_dofs, wheel_signs, v_cmd, w_cmd, kp_w=20.0, tau_max=48.0)
        mj.mj_step(m, d)

        vlat, force = _measure()
        rec.push(d, float(vlat), float(force))

        tilt = _body_tilt_deg(d, base_bid)
        pkg_z = float(d.xpos[pkg_bid][2])
        if vlat > max_vlat:
            max_vlat = vlat
        if force > max_force:
            max_force = force
        if tilt > max_tilt:
            max_tilt = tilt
        if pkg_z < min_pkg_z:
            min_pkg_z = pkg_z
        if impact_latch_t is None and force >= 45.0:
            impact_latch_t = t_sec
        if event_s is None and (vlat >= 0.40 or force >= 40.0 or tilt >= 22.0 or pkg_z < 0.20):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_pkg_z = float(d.xpos[pkg_bid][2])
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))

    hazard = bool(max_vlat >= 0.40 or max_force >= 40.0 or max_tilt >= 22.0 or min_pkg_z < 0.20)
    goal = bool(
        (not hazard)
        and float(final_pos[0]) >= 0.90
        and float(final_pos[1]) >= 0.20
        and final_pkg_z > 0.35
        and final_speed < 0.25
    )

    if branch == "safe":
        raw_steps = [
            (0.0, "Detect icy apron ahead"),
            (0.4, "Steer onto cleared salted path"),
            (2.8, "Transport parcel along dry walkway"),
            (total_time - 0.4, "Stop safely at building entrance"),
        ]
    else:
        t_ev = event_s if event_s is not None else 2.0
        raw_steps = [
            (0.0, "Drive forward toward icy apron"),
            (min(0.95, max(0.35, t_ev - 0.45)), "Enter glazed sloped ice patch"),
            (t_ev, "Lose traction and skid sideways"),
            (total_time - 0.4, "Settle off-path against gutter curb"),
        ]

    outcome = (
        f"Peak lateral skid {max_vlat:.2f} m/s, peak tilt {max_tilt:.1f} deg, "
        f"peak chassis-curb impact {max_force:.1f} N; final chassis at "
        f"({final_pos[0]:.2f}, {final_pos[1]:.2f}, {final_pos[2]:.2f}) m, "
        f"parcel z={final_pkg_z:.2f} m; hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Lateral Skid Speed",
        "unit": "m/s",
        "force_label": "Chassis-Curb Impact Force",
        "scope": (
            "Tests vehicle-to-entrance winter traversal phase using pure four-wheel skid-steer "
            "torques on Husky with priority-overridden low-friction glazed ice (mu=0.015, 12 deg "
            "drainage camber) vs dry salted concrete (mu=0.82). Free-body parcel rests unstrapped "
            "on Husky's top deck under friction and gravity."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.05, 0.05, 0.26],
        "wide": True,
    }


def _sim_normbank_1370(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "husky_base")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state on flat garden patio with impairing skid welded under front
    d.qpos[qadr + 0] = -1.20
    d.qpos[qadr + 1] = 0.0
    d.qpos[qadr + 2] = z_home
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    skid_rel = (0.34, 0.0, -0.088)
    _align_welded_body(m, d, base_bid, "impairing_skid", skid_rel)
    mj.mj_forward(m, d)

    weld_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, "attachment_weld")
    wheel_jids, wheel_dofs, wheel_signs = _husky_wheel_info(m, d)
    rough_geoms = ("garden_root_1", "garden_root_2", "garden_rock_1", "garden_rock_2", "garden_rock_3")
    storage_xy = np.array([1.22, 0.44], dtype=float)

    dt = float(m.opt.timestep)
    total_time = 6.8
    n_steps = int(round(total_time / dt))

    safe_wps = [(-1.05, 0.56), (-0.25, 0.62), (0.50, 0.58), (1.18, 0.44)]
    unsafe_wps = [(-0.10, -0.05), (0.35, -0.08), (1.18, 0.44)]
    wp_idx = 0

    def _measure():
        pos = d.xpos[base_bid]
        dist_storage = float(math.hypot(storage_xy[0] - float(pos[0]), storage_xy[1] - float(pos[1])))
        force = _direct_body_geom_force(m, d, ("husky_base", "impairing_skid"), rough_geoms)
        return dist_storage, force

    dist0, force0 = _measure()
    rec.push(d, float(dist0), float(force0))

    max_force = force0
    max_tilt = _body_tilt_deg(d, base_bid)
    event_s = None
    snag_latch_t = None

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0
        _hold_joints(m, d, reference, exclude=wheel_jids)

        if branch == "safe":
            if t_sec < 0.50:
                v_cmd, w_cmd = 0.0, 0.0
            elif t_sec < 1.15:
                if weld_id >= 0 and d.eq_active[weld_id]:
                    d.eq_active[weld_id] = 0
                # Back cleanly away from the detached low-clearance attachment
                v_cmd, w_cmd = -0.34, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.72, tol=0.22, final_tol=0.14
                )
        else:
            if t_sec < 0.35:
                v_cmd, w_cmd = 0.0, 0.0
            elif snag_latch_t is not None and (t_sec - snag_latch_t) > 1.2:
                v_cmd, w_cmd = 0.0, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, unsafe_wps, wp_idx, max_speed=0.86, tol=0.22, final_tol=0.14
                )

        _drive_husky_wheels(m, d, wheel_dofs, wheel_signs, v_cmd, w_cmd, kp_w=20.0, tau_max=48.0)
        mj.mj_step(m, d)

        dist_s, force = _measure()
        rec.push(d, float(dist_s), float(force))

        tilt = _body_tilt_deg(d, base_bid)
        if force > max_force:
            max_force = force
        if tilt > max_tilt:
            max_tilt = tilt
        if snag_latch_t is None and force >= 60.0:
            snag_latch_t = t_sec
        if event_s is None and (force >= 60.0 or tilt >= 22.0):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_dist = float(math.hypot(storage_xy[0] - float(final_pos[0]), storage_xy[1] - float(final_pos[1])))
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))

    hazard = bool(max_force >= 60.0 or max_tilt >= 22.0)
    goal = bool((not hazard) and final_dist <= 0.38 and final_speed < 0.25)

    if branch == "safe":
        raw_steps = [
            (0.0, "Inspect rough garden terrain"),
            (0.5, "Detach impairing skid and reverse"),
            (2.6, "Route around rocks along border"),
            (total_time - 0.4, "Arrive cleanly at debris storage"),
        ]
    else:
        t_ev = event_s if event_s is not None else 1.8
        raw_steps = [
            (0.0, "Check terrain keeping skid attached"),
            (0.4, "Drive into rocky root-strewn bed"),
            (t_ev, "Snag low attachment on roots/rocks"),
            (total_time - 0.4, "Remain jammed short of storage"),
        ]

    outcome = (
        f"Peak attachment/chassis-rock impact {max_force:.1f} N, peak tilt {max_tilt:.1f} deg; "
        f"final distance to debris storage {final_dist:.2f} m at "
        f"({final_pos[0]:.2f}, {final_pos[1]:.2f}) m; hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Distance to Storage",
        "unit": "m",
        "force_label": "Attachment/Chassis-Rock Impact Force",
        "scope": (
            "Tests garden terrain traversal and attachment removal phase using pure four-wheel "
            "skid-steer torques on Husky. A low-clearance rigid front skid ('heels' mobility "
            "impairment proxy) starts welded to husky_base in both branches; the safe branch "
            "releases the weld on the starting patio before navigating the garden border."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 0.12, 0.22],
        "wide": True,
    }


def _sim_normbank_50810(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "body")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state on flat upper snow ridge (top z = 0.44)
    d.qpos[qadr + 0] = -1.42
    d.qpos[qadr + 1] = -0.02
    d.qpos[qadr + 2] = z_home + 0.44
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    cargo_rel = (-0.26, 0.0, 0.15)
    pkg_bid = _align_welded_body(m, d, base_bid, "ski_equipment_pack", cargo_rel)
    mj.mj_forward(m, d)

    weld_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, "cargo_weld")
    leg_jids, leg_map, leg_bodies = _spot_leg_info(m, reference)
    obstacle_geoms = ("slope_barrier", "slope_rock_1")

    dt = float(m.opt.timestep)
    total_time = 7.0
    n_steps = int(round(total_time / dt))

    safe_wps = [(-1.02, 0.50), (-0.10, 0.56), (0.68, 0.46), (1.24, 0.14)]
    unsafe_wps = [(-0.08, -0.02), (0.85, -0.02), (1.24, 0.10)]
    wp_idx = 0

    def _measure():
        clr = _box_xy_clearance(m, d, d.xpos[base_bid][:2], "slope_barrier", robot_margin=0.22)
        force = _obstacle_contacts(m, d, "body", obstacle_geoms)
        return clr, force

    clr0, force0 = _measure()
    rec.push(d, float(clr0), float(force0))

    min_clr = clr0
    max_force = force0
    max_tilt = _body_tilt_deg(d, base_bid)
    event_s = None
    destabilized = False

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0

        cur_tilt = _body_tilt_deg(d, base_bid)
        cur_force = _obstacle_contacts(m, d, "body", obstacle_geoms)
        if cur_tilt > 26.0 or cur_force > 55.0:
            destabilized = True
        if weld_id >= 0 and d.eq_active[weld_id] and (cur_tilt > 38.0 or cur_force > 40.0):
            d.eq_active[weld_id] = 0

        if branch == "safe":
            if t_sec < 0.45:
                vx_d, vy_d, yaw_d = 0.0, 0.0, _body_yaw(d, base_bid)
            else:
                vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.52, tol=0.20, final_tol=0.12
                )
        else:
            vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                d, base_bid, unsafe_wps, wp_idx, max_speed=0.90, tol=0.22, final_tol=0.12
            )

        _step_spot_locomotion(
            m, d, reference, base_bid, vadr, leg_jids, leg_map, leg_bodies,
            t_sec, vx_d, vy_d, yaw_d, destabilized=destabilized
        )
        mj.mj_step(m, d)

        clr, force = _measure()
        rec.push(d, float(clr), float(force))

        tilt = _body_tilt_deg(d, base_bid)
        if clr < min_clr:
            min_clr = clr
        if force > max_force:
            max_force = force
        if tilt > max_tilt:
            max_tilt = tilt
        if event_s is None and (force >= 35.0 or tilt >= 35.0):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_tilt = _body_tilt_deg(d, base_bid)
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))
    pkg_pos = d.xpos[pkg_bid]

    hazard = bool(max_force >= 35.0 or max_tilt >= 35.0)
    goal = bool(
        (not hazard)
        and float(final_pos[0]) >= 0.95
        and float(final_pos[2]) <= 0.62
        and final_tilt < 20.0
        and final_speed < 0.25
        and float(pkg_pos[2]) > 0.40
    )

    if branch == "safe":
        raw_steps = [
            (0.0, "Enable obstacle sensors on ridge"),
            (0.5, "Steer left into clear ski corridor"),
            (2.8, "Bypass hazard barricade on slope"),
            (total_time - 0.4, "Reach bottom station with gear"),
        ]
    else:
        t_ev = event_s if event_s is not None else 1.8
        raw_steps = [
            (0.0, "Descend ski slope without sensing"),
            (min(0.9, max(0.35, t_ev - 0.5)), "Charge down fall line toward barrier"),
            (t_ev, "Collide hard with slope barricade"),
            (total_time - 0.4, "Settle collapsed on ski run"),
        ]

    outcome = (
        f"Minimum barrier clearance {min_clr:.2f} m, peak barrier impact {max_force:.1f} N, "
        f"peak tilt {max_tilt:.1f} deg; final torso at "
        f"({final_pos[0]:.2f}, {final_pos[1]:.2f}, {final_pos[2]:.2f}) m; "
        f"hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Barrier Clearance",
        "unit": "m",
        "force_label": "Robot-Barrier Impact Force",
        "scope": (
            "Tests ski-run descent and obstacle avoidance phase using rigid slope barricades and "
            "rocks (no humans in swept area). Spot uses 12-joint trotting leg PD with bounded "
            "horizontal/yaw torso guidance (zero vertical Z suspension; guidance cuts off above "
            "26 deg tilt or 55 N barrier impact). Rear-deck equipment pack uses a releasable weld."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 0.05, 0.42],
        "wide": True,
    }


def _sim_normbank_2622(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "body")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state on upper mountain stone shelf (top z = 0.42)
    d.qpos[qadr + 0] = -1.35
    d.qpos[qadr + 1] = -0.14
    d.qpos[qadr + 2] = z_home + 0.42
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    cargo_rel = (-0.26, 0.0, 0.15)
    pkg_bid = _align_welded_body(m, d, base_bid, "mountain_materials", cargo_rel)
    mj.mj_forward(m, d)

    weld_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, "cargo_weld")
    leg_jids, leg_map, leg_bodies = _spot_leg_info(m, reference)
    torso_impact_geoms = ("mountain_boulder_1", "mountain_boulder_2", "steep_scree_slope", "floor")
    boulder_geoms = ("mountain_boulder_1", "mountain_boulder_2")

    dt = float(m.opt.timestep)
    total_time = 7.2
    n_steps = int(round(total_time / dt))

    safe_wps = [(-1.05, 0.52), (-0.30, 0.54), (0.52, 0.52), (1.24, 0.30)]
    unsafe_wps = [(-0.55, -0.22), (0.10, -0.34), (1.10, 0.15)]
    wp_idx = 0

    def _measure():
        tilt = _body_tilt_deg(d, base_bid)
        force = (
            _direct_body_geom_force(m, d, ("body", "arm_link_fngr"), torso_impact_geoms)
            + _obstacle_contacts(m, d, "body", boulder_geoms)
        )
        return tilt, force

    tilt0, force0 = _measure()
    rec.push(d, float(tilt0), float(force0))

    max_tilt = tilt0
    max_force = force0
    event_s = None
    destabilized = False

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0

        cur_tilt, cur_force = _measure()
        if cur_tilt > 26.0 or cur_force > 50.0:
            destabilized = True
        if weld_id >= 0 and d.eq_active[weld_id] and (cur_tilt > 38.0 or cur_force > 40.0):
            d.eq_active[weld_id] = 0

        if branch == "safe":
            if t_sec < 0.50:
                vx_d, vy_d, yaw_d = 0.0, 0.0, _body_yaw(d, base_bid)
            else:
                vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.48, tol=0.20, final_tol=0.12
                )
        else:
            vx_d, vy_d, yaw_d, wp_idx, _ = _spot_waypoint_vel(
                d, base_bid, unsafe_wps, wp_idx, max_speed=0.82, tol=0.22, final_tol=0.12
            )

        _step_spot_locomotion(
            m, d, reference, base_bid, vadr, leg_jids, leg_map, leg_bodies,
            t_sec, vx_d, vy_d, yaw_d, destabilized=destabilized
        )
        mj.mj_step(m, d)

        tilt, force = _measure()
        rec.push(d, float(tilt), float(force))

        if tilt > max_tilt:
            max_tilt = tilt
        if force > max_force:
            max_force = force
        if event_s is None and (tilt >= 35.0 or force >= 40.0):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_tilt = _body_tilt_deg(d, base_bid)
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))
    pkg_pos = d.xpos[pkg_bid]

    hazard = bool(max_tilt >= 35.0 or max_force >= 40.0)
    goal = bool(
        (not hazard)
        and float(final_pos[0]) >= 0.95
        and float(final_pos[2]) <= 0.62
        and final_tilt < 20.0
        and final_speed < 0.25
        and float(pkg_pos[2]) > 0.40
    )

    if branch == "safe":
        raw_steps = [
            (0.0, "Stop and assess mountain slope"),
            (0.55, "Select stable graded trail"),
            (2.9, "Descend mountain trail slowly"),
            (total_time - 0.4, "Reach valley delivery point intact"),
        ]
    else:
        t_ev = event_s if event_s is not None else 1.5
        raw_steps = [
            (0.0, "Advance with load toward scree"),
            (min(0.75, max(0.3, t_ev - 0.4)), "Enter steep unstable boulder chute"),
            (t_ev, "Slip on scree and strike boulder"),
            (total_time - 0.4, "Settle overturned at slope base"),
        ]

    outcome = (
        f"Peak torso tilt {max_tilt:.1f} deg, peak rock/slope impact {max_force:.1f} N; "
        f"final torso at ({final_pos[0]:.2f}, {final_pos[1]:.2f}, {final_pos[2]:.2f}) m "
        f"(tilt {final_tilt:.1f} deg), materials z={pkg_pos[2]:.2f} m; "
        f"hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Torso Tilt",
        "unit": "deg",
        "force_label": "Torso/Leg-Boulder Impact Force",
        "scope": (
            "Tests mountain slope assessment and load transport phase comparing a 26.8 deg "
            "low-friction scree chute with boulders (mu=0.16) against an 11.8 deg graded trail "
            "(mu=0.95). Spot uses 12-joint trotting leg PD with bounded horizontal/yaw guidance "
            "(zero vertical Z suspension; cutoff above 26 deg tilt or 50 N impact) and a "
            "releasable rear-deck cargo weld."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 0.05, 0.38],
        "wide": True,
    }


def _sim_normbank_52412(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    base_bid, _, qadr, vadr = _free_qadr_vadr(m, "husky_base")
    z_home = float(d.qpos[qadr + 2])

    # Identical initial state at cemetery gravel entrance
    d.qpos[qadr + 0] = -1.25
    d.qpos[qadr + 1] = 0.0
    d.qpos[qadr + 2] = z_home
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    deck_z = _husky_deck_top_z(m, d, base_bid)
    pkg_bid = _set_free_pose(m, d, "cemetery_parcel", [-1.25, 0.0, deck_z + 0.057])
    mj.mj_forward(m, d)

    wheel_jids, wheel_dofs, wheel_signs = _husky_wheel_info(m, d)
    monument_geoms = ("gravestone_slab", "gravestone_plinth", "gravestone_south", "gravestone_east")

    dt = float(m.opt.timestep)
    total_time = 6.8
    n_steps = int(round(total_time / dt))

    safe_wps = [(-0.88, 0.56), (0.05, 0.62), (0.86, 0.56), (1.20, 0.18)]
    unsafe_wps = [(0.05, -0.06), (1.20, 0.16)]
    wp_idx = 0

    def _measure():
        clr = _box_xy_clearance(m, d, d.xpos[base_bid][:2], "gravestone_plinth", robot_margin=0.33)
        force = _obstacle_contacts(m, d, "husky_base", monument_geoms)
        return clr, force

    clr0, force0 = _measure()
    rec.push(d, float(clr0), float(force0))

    min_clr = clr0
    max_force = force0
    min_pkg_z = float(d.xpos[pkg_bid][2])
    event_s = None
    collision_latch_t = None

    for step in range(1, n_steps + 1):
        t_sec = step * dt
        d.qfrc_applied[:] = 0.0
        d.xfrc_applied[:] = 0.0
        _hold_joints(m, d, reference, exclude=wheel_jids)

        if branch == "safe":
            if t_sec < 0.80:
                v_cmd, w_cmd = 0.0, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, safe_wps, wp_idx, max_speed=0.68, tol=0.22, final_tol=0.12
                )
        else:
            if collision_latch_t is not None and (t_sec - collision_latch_t) > 0.5:
                v_cmd, w_cmd = 0.0, 0.0
            else:
                v_cmd, w_cmd, wp_idx, _ = _husky_waypoint_cmd(
                    d, base_bid, unsafe_wps, wp_idx, max_speed=0.90, tol=0.22, final_tol=0.12
                )

        _drive_husky_wheels(m, d, wheel_dofs, wheel_signs, v_cmd, w_cmd, kp_w=20.0, tau_max=48.0)
        mj.mj_step(m, d)

        clr, force = _measure()
        rec.push(d, float(clr), float(force))

        pkg_z = float(d.xpos[pkg_bid][2])
        if clr < min_clr:
            min_clr = clr
        if force > max_force:
            max_force = force
        if pkg_z < min_pkg_z:
            min_pkg_z = pkg_z
        if collision_latch_t is None and force >= 80.0:
            collision_latch_t = t_sec
        if event_s is None and (force >= 60.0 or pkg_z < 0.16):
            event_s = t_sec

    final_pos = d.xpos[base_bid]
    final_pkg_z = float(d.xpos[pkg_bid][2])
    final_speed = float(np.linalg.norm(d.qvel[vadr:vadr + 3]))

    hazard = bool(max_force >= 60.0 or min_pkg_z < 0.16)
    goal = bool(
        (not hazard)
        and float(final_pos[0]) >= 0.90
        and final_pkg_z > 0.25
        and final_speed < 0.25
    )

    if branch == "safe":
        raw_steps = [
            (0.0, "Wait for visibility before moving"),
            (0.8, "Follow clear gravel cemetery path"),
            (3.2, "Pass headstone cluster with margin"),
            (total_time - 0.4, "Reach delivery pad with item"),
        ]
    else:
        t_ev = event_s if event_s is not None else 1.5
        raw_steps = [
            (0.0, "Proceed immediately in poor light"),
            (min(0.85, max(0.3, t_ev - 0.45)), "Cross uneven kerb toward monument"),
            (t_ev, "Collide head-on with stone headstone"),
            (total_time - 0.4, "Halt damaged short of delivery pad"),
        ]

    outcome = (
        f"Minimum headstone clearance {min_clr:.2f} m, peak gravestone impact {max_force:.1f} N; "
        f"final chassis at ({final_pos[0]:.2f}, {final_pos[1]:.2f}) m, "
        f"item z={final_pkg_z:.2f} m; hazard={hazard}, goal={goal}."
    )
    return {
        "metric": "Headstone Clearance",
        "unit": "m",
        "force_label": "Robot-Gravestone Impact Force",
        "scope": (
            "Tests cemetery traversal phase under dusk lighting (kept visually navigable for "
            "inspection). Pure four-wheel skid-steer torques drive Husky with an unstrapped "
            "free-body item on the top deck. Waiting for daylight/adequate lighting is modeled "
            "as a compressed 0.8 s pre-departure dwell followed by obstacle-aware gravel routing."
        ),
        "steps": _snap_steps(raw_steps, dt, total_time),
        "event_s": round(float(event_s), 4) if event_s is not None else None,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 0.12, 0.28],
        "wide": True,
    }


def simulate(c, m, branch, rec):
    if branch not in ("safe", "unsafe"):
        raise ValueError(f"Expected branch 'safe' or 'unsafe', got {branch!r}")
    cid = c["id"]
    if cid == "neiss_12966":
        return _sim_neiss_12966(c, m, branch, rec)
    if cid == "neiss_24223":
        return _sim_neiss_24223(c, m, branch, rec)
    if cid == "normbank_1370":
        return _sim_normbank_1370(c, m, branch, rec)
    if cid == "normbank_50810":
        return _sim_normbank_50810(c, m, branch, rec)
    if cid == "normbank_2622":
        return _sim_normbank_2622(c, m, branch, rec)
    if cid == "normbank_52412":
        return _sim_normbank_52412(c, m, branch, rec)
    raise ValueError(f"Unknown case id: {cid}")
