"""Blender 4.5 physically calibrated lookdev and lighting module.

Provides two public entry points:
    - retexture(objects, k, genie_root)
    - light(scene, k, genie_root)

Designed for Cycles and EEVEE Next with AgX color management, real Genie Sim
PBR floor/wall texture sets (sRGB *_Alb.jpg, Non-Color *_Rgh.jpg, Non-Color
*_Nor.jpg through Normal Map), verified HDRI environments, motivated daylight
and linear practical fixtures, strict UV/image preservation for signage/labels/
paper graphics/humans/robot markings/switches, and live datablock verification
in all audit outputs.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import bpy
from mathutils import Euler, Vector

# ---------------------------------------------------------------------------
# Verified Genie Sim Assets (under genie_root/background/common/home_b/textures)
# ---------------------------------------------------------------------------

VERIFIED_FLOOR_SETS: Tuple[str, ...] = (
    "floor_00",
    "floor_01",
    "floor_02",
    "floor_03",
    "floor_04",
    "floor_05",
    "floor_06",
    "floor_tile_00",
    "floor_tile_01",
    "floor_tile_02",
    "floor_tile_03",
    "floor_tile_04",
)

VERIFIED_WALL_SETS: Tuple[str, ...] = (
    "wall_00",
    "wall_01",
    "wall_02",
    "wall_03",
    "wall_04",
    "wall_05",
    "wall_06",
    "wall_07",
    "wall_tile_00",
)

VERIFIED_HDRIS: Tuple[str, ...] = (
    "985307.hdr",
    "986647.hdr",
    "988965.hdr",
)

# ---------------------------------------------------------------------------
# Setting Definitions: 10 Core Workrooms (k=1..10) + 6 Large Rooms/Restroom (k=11..16)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingProfile:
    k: int
    name: str
    floor_stem: str
    floor_tile_m: float
    floor_rgh_range: Tuple[float, float]
    floor_nor_strength: float
    floor_coat: float
    wall_stem: str
    wall_tile_m: float
    wall_rgh_range: Tuple[float, float]
    wall_nor_strength: float
    wall_coat: float
    hdri_file: str
    hdri_rot_deg: float
    hdri_strength: float
    hdri_camera_strength: float
    hdri_saturation: float
    key_azimuth_deg: float
    key_elevation_deg: float
    key_kelvin: float
    key_watts_ref: float
    key_size: Tuple[float, float]
    key_spread_deg: float
    fill_kelvin: float
    fill_watts_ref: float
    practical_kelvin: float
    practical_watts_ref: float
    practical_yaw_deg: float
    ribbon_kelvin: float
    ribbon_watts_ref: float
    exposure: float
    is_large_room: bool = False


SETTINGS: Dict[int, SettingProfile] = {
    1: SettingProfile(
        k=1,
        name="warehouse",
        floor_stem="floor_00",
        floor_tile_m=2.4,
        floor_rgh_range=(0.46, 0.84),
        floor_nor_strength=0.48,
        floor_coat=0.0,
        wall_stem="wall_00",
        wall_tile_m=2.6,
        wall_rgh_range=(0.66, 0.92),
        wall_nor_strength=0.45,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=15.0,
        hdri_strength=0.28,
        hdri_camera_strength=0.55,
        hdri_saturation=0.90,
        key_azimuth_deg=35.0,
        key_elevation_deg=36.0,
        key_kelvin=5600.0,
        key_watts_ref=260.0,
        key_size=(3.2, 1.6),
        key_spread_deg=100.0,
        fill_kelvin=7800.0,
        fill_watts_ref=78.0,
        practical_kelvin=4100.0,
        practical_watts_ref=85.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3500.0,
        ribbon_watts_ref=62.0,
        exposure=-0.15,
    ),
    2: SettingProfile(
        k=2,
        name="sterile_corridor",
        floor_stem="floor_tile_00",
        floor_tile_m=1.2,
        floor_rgh_range=(0.38, 0.68),
        floor_nor_strength=0.35,
        floor_coat=0.08,
        wall_stem="wall_01",
        wall_tile_m=2.2,
        wall_rgh_range=(0.58, 0.84),
        wall_nor_strength=0.32,
        wall_coat=0.04,
        hdri_file="986647.hdr",
        hdri_rot_deg=95.0,
        hdri_strength=0.24,
        hdri_camera_strength=0.50,
        hdri_saturation=0.88,
        key_azimuth_deg=70.0,
        key_elevation_deg=28.0,
        key_kelvin=6400.0,
        key_watts_ref=235.0,
        key_size=(2.4, 1.5),
        key_spread_deg=95.0,
        fill_kelvin=8400.0,
        fill_watts_ref=82.0,
        practical_kelvin=4900.0,
        practical_watts_ref=92.0,
        practical_yaw_deg=90.0,
        ribbon_kelvin=4200.0,
        ribbon_watts_ref=58.0,
        exposure=-0.10,
    ),
    3: SettingProfile(
        k=3,
        name="coffee_shop",
        floor_stem="floor_02",
        floor_tile_m=1.6,
        floor_rgh_range=(0.42, 0.76),
        floor_nor_strength=0.44,
        floor_coat=0.08,
        wall_stem="wall_02",
        wall_tile_m=2.0,
        wall_rgh_range=(0.66, 0.90),
        wall_nor_strength=0.46,
        wall_coat=0.0,
        hdri_file="988965.hdr",
        hdri_rot_deg=140.0,
        hdri_strength=0.30,
        hdri_camera_strength=0.58,
        hdri_saturation=0.92,
        key_azimuth_deg=-40.0,
        key_elevation_deg=26.0,
        key_kelvin=4900.0,
        key_watts_ref=250.0,
        key_size=(2.8, 1.8),
        key_spread_deg=96.0,
        fill_kelvin=7200.0,
        fill_watts_ref=72.0,
        practical_kelvin=2950.0,
        practical_watts_ref=78.0,
        practical_yaw_deg=15.0,
        ribbon_kelvin=2850.0,
        ribbon_watts_ref=65.0,
        exposure=-0.20,
    ),
    4: SettingProfile(
        k=4,
        name="sample_receiving",
        floor_stem="floor_tile_01",
        floor_tile_m=1.4,
        floor_rgh_range=(0.40, 0.72),
        floor_nor_strength=0.38,
        floor_coat=0.05,
        wall_stem="wall_03",
        wall_tile_m=2.2,
        wall_rgh_range=(0.60, 0.88),
        wall_nor_strength=0.38,
        wall_coat=0.0,
        hdri_file="986647.hdr",
        hdri_rot_deg=205.0,
        hdri_strength=0.26,
        hdri_camera_strength=0.52,
        hdri_saturation=0.90,
        key_azimuth_deg=125.0,
        key_elevation_deg=32.0,
        key_kelvin=6000.0,
        key_watts_ref=245.0,
        key_size=(2.6, 1.5),
        key_spread_deg=98.0,
        fill_kelvin=8000.0,
        fill_watts_ref=76.0,
        practical_kelvin=4300.0,
        practical_watts_ref=84.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3600.0,
        ribbon_watts_ref=60.0,
        exposure=-0.15,
    ),
    5: SettingProfile(
        k=5,
        name="parcel_dock",
        floor_stem="floor_01",
        floor_tile_m=2.5,
        floor_rgh_range=(0.48, 0.86),
        floor_nor_strength=0.52,
        floor_coat=0.0,
        wall_stem="wall_04",
        wall_tile_m=2.6,
        wall_rgh_range=(0.68, 0.92),
        wall_nor_strength=0.46,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=255.0,
        hdri_strength=0.34,
        hdri_camera_strength=0.60,
        hdri_saturation=0.90,
        key_azimuth_deg=-115.0,
        key_elevation_deg=22.0,
        key_kelvin=5800.0,
        key_watts_ref=285.0,
        key_size=(3.6, 2.0),
        key_spread_deg=108.0,
        fill_kelvin=8200.0,
        fill_watts_ref=75.0,
        practical_kelvin=3900.0,
        practical_watts_ref=82.0,
        practical_yaw_deg=90.0,
        ribbon_kelvin=3300.0,
        ribbon_watts_ref=64.0,
        exposure=-0.22,
    ),
    6: SettingProfile(
        k=6,
        name="repair_bench",
        floor_stem="floor_03",
        floor_tile_m=2.0,
        floor_rgh_range=(0.44, 0.82),
        floor_nor_strength=0.46,
        floor_coat=0.0,
        wall_stem="wall_05",
        wall_tile_m=2.2,
        wall_rgh_range=(0.64, 0.90),
        wall_nor_strength=0.42,
        wall_coat=0.0,
        hdri_file="988965.hdr",
        hdri_rot_deg=45.0,
        hdri_strength=0.25,
        hdri_camera_strength=0.52,
        hdri_saturation=0.90,
        key_azimuth_deg=50.0,
        key_elevation_deg=30.0,
        key_kelvin=5500.0,
        key_watts_ref=240.0,
        key_size=(2.6, 1.5),
        key_spread_deg=95.0,
        fill_kelvin=7600.0,
        fill_watts_ref=70.0,
        practical_kelvin=3800.0,
        practical_watts_ref=88.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3400.0,
        ribbon_watts_ref=68.0,
        exposure=-0.15,
    ),
    7: SettingProfile(
        k=7,
        name="electronics_bench",
        floor_stem="floor_tile_02",
        floor_tile_m=1.3,
        floor_rgh_range=(0.40, 0.72),
        floor_nor_strength=0.36,
        floor_coat=0.05,
        wall_stem="wall_06",
        wall_tile_m=2.0,
        wall_rgh_range=(0.60, 0.86),
        wall_nor_strength=0.36,
        wall_coat=0.0,
        hdri_file="986647.hdr",
        hdri_rot_deg=310.0,
        hdri_strength=0.22,
        hdri_camera_strength=0.48,
        hdri_saturation=0.88,
        key_azimuth_deg=-65.0,
        key_elevation_deg=34.0,
        key_kelvin=6100.0,
        key_watts_ref=235.0,
        key_size=(2.4, 1.4),
        key_spread_deg=92.0,
        fill_kelvin=8200.0,
        fill_watts_ref=72.0,
        practical_kelvin=4500.0,
        practical_watts_ref=90.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3500.0,
        ribbon_watts_ref=66.0,
        exposure=-0.12,
    ),
    8: SettingProfile(
        k=8,
        name="print_room",
        floor_stem="floor_04",
        floor_tile_m=1.8,
        floor_rgh_range=(0.44, 0.78),
        floor_nor_strength=0.40,
        floor_coat=0.04,
        wall_stem="wall_07",
        wall_tile_m=2.2,
        wall_rgh_range=(0.62, 0.88),
        wall_nor_strength=0.38,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=175.0,
        hdri_strength=0.26,
        hdri_camera_strength=0.54,
        hdri_saturation=0.90,
        key_azimuth_deg=155.0,
        key_elevation_deg=32.0,
        key_kelvin=5300.0,
        key_watts_ref=245.0,
        key_size=(2.8, 1.5),
        key_spread_deg=98.0,
        fill_kelvin=7400.0,
        fill_watts_ref=74.0,
        practical_kelvin=4600.0,
        practical_watts_ref=84.0,
        practical_yaw_deg=90.0,
        ribbon_kelvin=3700.0,
        ribbon_watts_ref=58.0,
        exposure=-0.15,
    ),
    9: SettingProfile(
        k=9,
        name="library",
        floor_stem="floor_05",
        floor_tile_m=1.7,
        floor_rgh_range=(0.42, 0.76),
        floor_nor_strength=0.42,
        floor_coat=0.06,
        wall_stem="wall_02",
        wall_tile_m=2.2,
        wall_rgh_range=(0.66, 0.92),
        wall_nor_strength=0.44,
        wall_coat=0.0,
        hdri_file="988965.hdr",
        hdri_rot_deg=80.0,
        hdri_strength=0.28,
        hdri_camera_strength=0.56,
        hdri_saturation=0.92,
        key_azimuth_deg=-25.0,
        key_elevation_deg=28.0,
        key_kelvin=5100.0,
        key_watts_ref=240.0,
        key_size=(2.6, 1.9),
        key_spread_deg=94.0,
        fill_kelvin=7300.0,
        fill_watts_ref=68.0,
        practical_kelvin=3150.0,
        practical_watts_ref=76.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3050.0,
        ribbon_watts_ref=60.0,
        exposure=-0.18,
    ),
    10: SettingProfile(
        k=10,
        name="packing_area",
        floor_stem="floor_06",
        floor_tile_m=2.2,
        floor_rgh_range=(0.46, 0.84),
        floor_nor_strength=0.46,
        floor_coat=0.0,
        wall_stem="wall_04",
        wall_tile_m=2.4,
        wall_rgh_range=(0.64, 0.90),
        wall_nor_strength=0.42,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=220.0,
        hdri_strength=0.28,
        hdri_camera_strength=0.54,
        hdri_saturation=0.90,
        key_azimuth_deg=110.0,
        key_elevation_deg=34.0,
        key_kelvin=5700.0,
        key_watts_ref=255.0,
        key_size=(3.0, 1.6),
        key_spread_deg=100.0,
        fill_kelvin=7700.0,
        fill_watts_ref=76.0,
        practical_kelvin=4000.0,
        practical_watts_ref=86.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3450.0,
        ribbon_watts_ref=62.0,
        exposure=-0.15,
    ),
    # Optional Large Rooms & Restroom (k=11..16)
    11: SettingProfile(
        k=11,
        name="large_assembly_hall",
        floor_stem="floor_00",
        floor_tile_m=2.8,
        floor_rgh_range=(0.45, 0.82),
        floor_nor_strength=0.46,
        floor_coat=0.0,
        wall_stem="wall_00",
        wall_tile_m=3.0,
        wall_rgh_range=(0.66, 0.92),
        wall_nor_strength=0.44,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=30.0,
        hdri_strength=0.30,
        hdri_camera_strength=0.58,
        hdri_saturation=0.90,
        key_azimuth_deg=40.0,
        key_elevation_deg=40.0,
        key_kelvin=5800.0,
        key_watts_ref=310.0,
        key_size=(4.0, 2.0),
        key_spread_deg=105.0,
        fill_kelvin=8000.0,
        fill_watts_ref=92.0,
        practical_kelvin=4200.0,
        practical_watts_ref=105.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3500.0,
        ribbon_watts_ref=70.0,
        exposure=-0.18,
        is_large_room=True,
    ),
    12: SettingProfile(
        k=12,
        name="large_logistics_bay",
        floor_stem="floor_01",
        floor_tile_m=2.8,
        floor_rgh_range=(0.46, 0.84),
        floor_nor_strength=0.48,
        floor_coat=0.0,
        wall_stem="wall_04",
        wall_tile_m=2.8,
        wall_rgh_range=(0.68, 0.92),
        wall_nor_strength=0.44,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=265.0,
        hdri_strength=0.32,
        hdri_camera_strength=0.60,
        hdri_saturation=0.90,
        key_azimuth_deg=-105.0,
        key_elevation_deg=26.0,
        key_kelvin=5600.0,
        key_watts_ref=320.0,
        key_size=(4.2, 2.2),
        key_spread_deg=110.0,
        fill_kelvin=7900.0,
        fill_watts_ref=90.0,
        practical_kelvin=4000.0,
        practical_watts_ref=102.0,
        practical_yaw_deg=90.0,
        ribbon_kelvin=3400.0,
        ribbon_watts_ref=68.0,
        exposure=-0.20,
        is_large_room=True,
    ),
    13: SettingProfile(
        k=13,
        name="large_cleanroom_lab",
        floor_stem="floor_tile_03",
        floor_tile_m=1.4,
        floor_rgh_range=(0.38, 0.68),
        floor_nor_strength=0.34,
        floor_coat=0.08,
        wall_stem="wall_01",
        wall_tile_m=2.4,
        wall_rgh_range=(0.58, 0.84),
        wall_nor_strength=0.32,
        wall_coat=0.04,
        hdri_file="986647.hdr",
        hdri_rot_deg=115.0,
        hdri_strength=0.24,
        hdri_camera_strength=0.50,
        hdri_saturation=0.88,
        key_azimuth_deg=80.0,
        key_elevation_deg=38.0,
        key_kelvin=6300.0,
        key_watts_ref=285.0,
        key_size=(3.6, 1.8),
        key_spread_deg=102.0,
        fill_kelvin=8500.0,
        fill_watts_ref=95.0,
        practical_kelvin=4800.0,
        practical_watts_ref=108.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=4100.0,
        ribbon_watts_ref=64.0,
        exposure=-0.12,
        is_large_room=True,
    ),
    14: SettingProfile(
        k=14,
        name="large_atrium_studio",
        floor_stem="floor_05",
        floor_tile_m=2.2,
        floor_rgh_range=(0.42, 0.76),
        floor_nor_strength=0.40,
        floor_coat=0.06,
        wall_stem="wall_07",
        wall_tile_m=2.6,
        wall_rgh_range=(0.64, 0.90),
        wall_nor_strength=0.38,
        wall_coat=0.0,
        hdri_file="988965.hdr",
        hdri_rot_deg=160.0,
        hdri_strength=0.32,
        hdri_camera_strength=0.60,
        hdri_saturation=0.92,
        key_azimuth_deg=-50.0,
        key_elevation_deg=30.0,
        key_kelvin=5400.0,
        key_watts_ref=300.0,
        key_size=(4.0, 2.2),
        key_spread_deg=106.0,
        fill_kelvin=7600.0,
        fill_watts_ref=88.0,
        practical_kelvin=3350.0,
        practical_watts_ref=92.0,
        practical_yaw_deg=15.0,
        ribbon_kelvin=3200.0,
        ribbon_watts_ref=66.0,
        exposure=-0.18,
        is_large_room=True,
    ),
    15: SettingProfile(
        k=15,
        name="large_machine_shop",
        floor_stem="floor_03",
        floor_tile_m=2.4,
        floor_rgh_range=(0.46, 0.84),
        floor_nor_strength=0.48,
        floor_coat=0.0,
        wall_stem="wall_05",
        wall_tile_m=2.6,
        wall_rgh_range=(0.66, 0.92),
        wall_nor_strength=0.44,
        wall_coat=0.0,
        hdri_file="985307.hdr",
        hdri_rot_deg=60.0,
        hdri_strength=0.27,
        hdri_camera_strength=0.54,
        hdri_saturation=0.90,
        key_azimuth_deg=55.0,
        key_elevation_deg=42.0,
        key_kelvin=5600.0,
        key_watts_ref=305.0,
        key_size=(3.8, 2.0),
        key_spread_deg=104.0,
        fill_kelvin=7800.0,
        fill_watts_ref=86.0,
        practical_kelvin=4100.0,
        practical_watts_ref=104.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=3400.0,
        ribbon_watts_ref=72.0,
        exposure=-0.15,
        is_large_room=True,
    ),
    16: SettingProfile(
        k=16,
        name="restroom",
        floor_stem="floor_tile_04",
        floor_tile_m=0.9,
        floor_rgh_range=(0.34, 0.62),
        floor_nor_strength=0.40,
        floor_coat=0.14,
        wall_stem="wall_tile_00",
        wall_tile_m=1.0,
        wall_rgh_range=(0.28, 0.56),
        wall_nor_strength=0.38,
        wall_coat=0.22,
        hdri_file="986647.hdr",
        hdri_rot_deg=190.0,
        hdri_strength=0.20,
        hdri_camera_strength=0.46,
        hdri_saturation=0.88,
        key_azimuth_deg=140.0,
        key_elevation_deg=35.0,
        key_kelvin=6100.0,
        key_watts_ref=210.0,
        key_size=(1.8, 1.0),
        key_spread_deg=92.0,
        fill_kelvin=8000.0,
        fill_watts_ref=64.0,
        practical_kelvin=3600.0,
        practical_watts_ref=78.0,
        practical_yaw_deg=0.0,
        ribbon_kelvin=4200.0,
        ribbon_watts_ref=52.0,
        exposure=-0.12,
        is_large_room=False,
    ),
}

# ---------------------------------------------------------------------------
# Role Keyword Tables
# ---------------------------------------------------------------------------

_FLOOR_TOKENS = (
    "surface_floor",
    "genie_floor",
    "floor",
    "ground",
    "slab",
    "screed",
    "pavement",
)
_WALL_TOKENS = (
    "finish_wallsubstrate",
    "surface_wall",
    "wallsubstrate",
    "wall",
    "drywall",
    "plaster",
    "masonry",
    "partition",
)
_PRESERVE_UV_TOKENS = (
    "hero_mark_shipping",
    "shipping",
    "label",
    "sign",
    "signage",
    "text",
    "decal",
    "logo",
    "sticker",
    "barcode",
    "qr",
    "placard",
    "poster",
    "nameplate",
    "badge",
    "graphic",
    "marking",
    "mark_",
    "_mark",
    "caption",
    "title",
    "screen",
    "display",
    "monitor",
    "lcd",
    "gauge",
    "dial",
    "switch",
    "button",
    "estop",
    "e_stop",
    "indicator",
    "pendant",
    "control_panel",
    "interface",
    "keypad",
)
_HUMAN_TOKENS = (
    "human",
    "person",
    "worker",
    "operator",
    "skin",
    "face",
    "head",
    "hair",
    "shirt",
    "pants",
    "trouser",
    "jacket",
    "coat",
    "apron",
    "shoe",
    "boot",
    "glove",
    "cloth",
    "fabric",
    "apparel",
    "mannequin",
    "avatar",
    "smpl",
)
_ROBOT_TOKENS = (
    "ur10",
    "ur5",
    "ur3",
    "ur_",
    "robotiq",
    "robot",
    "franka",
    "panda",
    "kuka",
    "abb",
    "fanuc",
    "yam",
    "so101",
    "gripper",
    "finger",
    "wrist",
    "forearm",
    "upperarm",
    "shoulder",
    "elbow",
    "base_link",
    "link_",
    "actuator",
    "end_effector",
    "tool0",
    "flange",
)
_CARTON_TOKENS = ("hero_carton", "carton", "cardboard", "corrugated", "parcel", "shipping_box")
_BEARING_TOKENS = ("fabricated_bearing", "bearing", "chrome", "spindle", "shaft", "linear_guide", "bushing")
_BRUSHED_STEEL_TOKENS = (
    "fabricated_brushed_steel",
    "brushed_steel",
    "brushed_metal",
    "stainless",
)
_STEEL_METAL_TOKENS = (
    "hero_metal",
    "steel",
    "aluminum",
    "aluminium",
    "billet",
    "machined",
    "cnc",
    "vise",
    "parallel",
    "rail",
    "metal",
    "iron",
    "brass",
    "copper",
)
_ORANGE_TRIM_TOKENS = (
    "hero_orange",
    "safety_orange",
    "safety_trim",
    "caution",
    "warning",
    "orange",
)
_POWDER_ENAMEL_TOKENS = (
    "fabricated_powder_enamel",
    "powder_enamel",
    "enamel",
    "casting",
    "housing",
    "cabinet",
    "rack",
    "frame",
    "gantry",
    "stand",
    "chassis",
    "machine_body",
    "guard",
    "door_frame",
    "painted",
)
_RUBBER_TOKENS = (
    "rubber",
    "tire",
    "tyre",
    "wheel",
    "caster",
    "bumper",
    "gasket",
    "cable",
    "hose",
    "belt",
    "mat",
    "pad",
    "grip",
    "silicone",
    "neoprene",
)
_CERAMIC_TOKENS = ("hero_cup", "cup", "mug", "ceramic", "porcelain", "stoneware", "bowl", "plate", "dish", "sink", "basin")
_WOOD_TOKENS = ("wood", "timber", "plywood", "maple", "oak", "pine", "butcher", "workbench", "pallet", "crate", "tabletop", "desk", "shelf_wood", "bookcase")
_PAPER_TOKENS = ("paper", "document", "sheet", "manual", "book", "folder", "invoice", "manifest", "form", "note", "printout")
_GLASS_TOKENS = ("glass", "acrylic", "polycarbonate", "plexiglass", "window_pane", "visor", "clear_door", "shield", "transparent")
_PLASTIC_TOKENS = ("plastic", "polymer", "abs", "hdpe", "nylon", "tote", "bin", "tray", "container", "pcb", "electronics")

# ---------------------------------------------------------------------------
# Path, Color, and Blender 4.5 Node Utilities
# ---------------------------------------------------------------------------


def _normalize_k(k: Any) -> SettingProfile:
    """Map k deterministically to a SettingProfile (1..10 core, 11..16 optional)."""
    try:
        idx = int(k)
    except (TypeError, ValueError):
        idx = 1
    if idx in SETTINGS:
        return SETTINGS[idx]
    if idx == 0:
        return SETTINGS[1]
    wrapped = ((idx - 1) % len(SETTINGS)) + 1
    return SETTINGS[wrapped]


def _resolve_textures_dir(genie_root: Any) -> Path:
    """Resolve the Genie Sim home_b texture directory under genie_root."""
    root = Path(genie_root)
    canonical = root / "background" / "common" / "home_b" / "textures"
    if canonical.is_dir():
        return canonical
    for candidate in (
        root / "common" / "home_b" / "textures",
        root / "home_b" / "textures",
        root / "textures",
        root,
    ):
        if candidate.is_dir() and any(
            (candidate / probe).is_file()
            for probe in ("floor_00_Alb.jpg", "wall_00_Alb.jpg", "985307.hdr")
        ):
            return candidate
    return canonical


def _kelvin_to_linear_rgb(kelvin: float) -> Tuple[float, float, float]:
    """Convert correlated color temperature (Kelvin) to normalized linear RGB."""
    temp = max(1500.0, min(15000.0, float(kelvin))) / 100.0
    if temp <= 66.0:
        r = 1.0
        g = max(0.0, min(1.0, (99.4708025861 * math.log(temp) - 161.1195681661) / 255.0))
        if temp <= 19.0:
            b = 0.0
        else:
            b = max(0.0, min(1.0, (138.5177312231 * math.log(temp - 10.0) - 305.0447927307) / 255.0))
    else:
        r = max(0.0, min(1.0, (329.698727446 * ((temp - 60.0) ** -0.1332047592)) / 255.0))
        g = max(0.0, min(1.0, (288.1221695283 * ((temp - 60.0) ** -0.0755148492)) / 255.0))
        b = 1.0

    def _srgb_to_lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    lr, lg, lb = _srgb_to_lin(r), _srgb_to_lin(g), _srgb_to_lin(b)
    peak = max(lr, lg, lb, 1e-6)
    return (lr / peak, lg / peak, lb / peak)


def _set_colorspace(img: bpy.types.Image, desired: str) -> str:
    """Assign a valid OCIO colorspace to a Blender image datablock."""
    fallbacks = {
        "Linear Rec.709": ("Linear Rec.709", "Linear", "Non-Color"),
        "Non-Color": ("Non-Color", "Raw", "Linear Rec.709"),
        "sRGB": ("sRGB",),
    }
    candidates = fallbacks.get(desired, (desired, "sRGB"))
    for cs in candidates:
        try:
            img.colorspace_settings.name = cs
            return img.colorspace_settings.name
        except TypeError:
            continue
    return img.colorspace_settings.name


def _inspect_image_datablock(img: Optional[bpy.types.Image]) -> Dict[str, Any]:
    """Read live, verified image metadata directly from a bpy.types.Image datablock."""
    if img is None:
        return {
            "datablock_name": None,
            "file_name": None,
            "resolved_path": None,
            "size": [0, 0],
            "channels": 0,
            "colorspace": None,
            "is_float": False,
            "loaded_ok": False,
        }
    raw_fp = img.filepath_raw or img.filepath or ""
    abs_fp = bpy.path.abspath(raw_fp) if raw_fp else ""
    file_name = os.path.basename(abs_fp) if abs_fp else (f"<packed:{img.name}>" if img.packed_file else img.name)
    width = int(img.size[0]) if len(img.size) >= 2 else 0
    height = int(img.size[1]) if len(img.size) >= 2 else 0
    if (width == 0 or height == 0) and abs_fp and os.path.isfile(abs_fp):
        try:
            img.reload()
            width = int(img.size[0])
            height = int(img.size[1])
        except RuntimeError:
            pass
    return {
        "datablock_name": img.name,
        "file_name": file_name,
        "resolved_path": abs_fp or None,
        "size": [width, height],
        "channels": int(getattr(img, "channels", 0)),
        "colorspace": img.colorspace_settings.name,
        "is_float": bool(getattr(img, "is_float", False)),
        "loaded_ok": bool(width > 0 and height > 0),
    }


def _load_verified_image(path: Path, colorspace: str) -> Tuple[Optional[bpy.types.Image], Dict[str, Any]]:
    """Load an image file from disk and verify its actual bpy.types.Image datablock."""
    if not path.is_file():
        return None, {
            "datablock_name": None,
            "file_name": None,
            "resolved_path": None,
            "size": [0, 0],
            "channels": 0,
            "colorspace": None,
            "is_float": False,
            "loaded_ok": False,
            "missing_requested": path.name,
        }
    img = bpy.data.images.load(str(path), check_existing=True)
    _set_colorspace(img, colorspace)
    info = _inspect_image_datablock(img)
    if not info["loaded_ok"]:
        return None, info
    return img, info


def _load_pbr_texture_set(
    textures_dir: Path,
    preferred_stem: str,
    verified_allowlist: Sequence[str],
) -> Tuple[Optional[str], Dict[str, Optional[bpy.types.Image]], Dict[str, Dict[str, Any]]]:
    """Load *_Alb.jpg (sRGB), *_Rgh.jpg (Non-Color), *_Nor.jpg (Non-Color) from verified sets."""
    ordered_stems: List[str] = []
    if preferred_stem in verified_allowlist:
        ordered_stems.append(preferred_stem)
    for stem in verified_allowlist:
        if stem not in ordered_stems:
            ordered_stems.append(stem)

    channel_specs = (
        ("albedo", "_Alb.jpg", "sRGB"),
        ("roughness", "_Rgh.jpg", "Non-Color"),
        ("normal", "_Nor.jpg", "Non-Color"),
    )
    for stem in ordered_stems:
        alb_img, alb_info = _load_verified_image(textures_dir / f"{stem}_Alb.jpg", "sRGB")
        if alb_img is None:
            continue
        imgs: Dict[str, Optional[bpy.types.Image]] = {"albedo": alb_img}
        infos: Dict[str, Dict[str, Any]] = {"albedo": alb_info}
        for key, suffix, cs in channel_specs[1:]:
            img, info = _load_verified_image(textures_dir / f"{stem}{suffix}", cs)
            imgs[key] = img
            infos[key] = info
        return stem, imgs, infos

    return None, {"albedo": None, "roughness": None, "normal": None}, {}


def _load_verified_hdri(
    textures_dir: Path,
    preferred_file: str,
) -> Tuple[Optional[bpy.types.Image], Dict[str, Any]]:
    """Load one of the verified real HDR files and inspect the live datablock."""
    ordered: List[str] = []
    if preferred_file in VERIFIED_HDRIS:
        ordered.append(preferred_file)
    for fname in VERIFIED_HDRIS:
        if fname not in ordered:
            ordered.append(fname)
    for fname in ordered:
        img, info = _load_verified_image(textures_dir / fname, "Linear Rec.709")
        if img is not None and info["loaded_ok"]:
            return img, info
    return None, _inspect_image_datablock(None)


def _set_input(node: bpy.types.Node, names: Sequence[str] | str, value: Any) -> None:
    """Safely assign a Blender 4.5 node input socket value."""
    candidates = (names,) if isinstance(names, str) else names
    for name in candidates:
        sock = node.inputs.get(name)
        if sock is None:
            continue
        if sock.type == "RGBA":
            if isinstance(value, (int, float)):
                sock.default_value = (float(value), float(value), float(value), 1.0)
            elif len(value) == 3:
                sock.default_value = (float(value[0]), float(value[1]), float(value[2]), 1.0)
            else:
                sock.default_value = tuple(float(v) for v in value[:4])
        elif sock.type == "VECTOR":
            sock.default_value = tuple(float(v) for v in value[:3])
        else:
            sock.default_value = float(value)
        return


def _mix_rgba_sockets(mix_node: bpy.types.Node) -> Tuple[bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket]:
    """Return (Factor, A, B, Result) sockets for a Blender 4.5 ShaderNodeMix(data_type='RGBA')."""
    fac = next(s for s in mix_node.inputs if s.name == "Factor" and s.type == "VALUE")
    a_sock = next(s for s in mix_node.inputs if s.name == "A" and s.type == "RGBA")
    b_sock = next(s for s in mix_node.inputs if s.name == "B" and s.type == "RGBA")
    res = next(s for s in mix_node.outputs if s.name == "Result" and s.type == "RGBA")
    return fac, a_sock, b_sock, res


def _new_material(name: str) -> Tuple[bpy.types.Material, bpy.types.NodeTree, bpy.types.Node, bpy.types.Node]:
    """Create or reset a node-based material with Principled BSDF and Material Output."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (260, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    # Ensure zero accidental emission by default.
    _set_input(bsdf, "Emission Strength", 0.0)
    return mat, nt, bsdf, out


def _add_bevel_normal(
    nt: bpy.types.NodeTree,
    bsdf: bpy.types.Node,
    radius: float,
    upstream_normal: Optional[bpy.types.NodeSocket] = None,
    samples: int = 4,
    loc: Tuple[float, float] = (40, -280),
) -> bpy.types.Node:
    """Attach a Cycles-aware micro-bevel node so tiny chamfers catch crisp specular light."""
    bevel = nt.nodes.new("ShaderNodeBevel")
    bevel.location = loc
    bevel.samples = samples
    bevel.inputs["Radius"].default_value = radius
    if upstream_normal is not None:
        nt.links.new(upstream_normal, bevel.inputs["Normal"])
    nt.links.new(bevel.outputs["Normal"], bsdf.inputs["Normal"])
    return bevel


def _object_metric_scale(obj: bpy.types.Object) -> Tuple[float, float, float]:
    """Return quantized absolute object scale so Object coordinates map directly to meters."""
    sx = max(abs(float(obj.scale.x)), 1e-4)
    sy = max(abs(float(obj.scale.y)), 1e-4)
    sz = max(abs(float(obj.scale.z)), 1e-4)
    return (round(sx, 3), round(sy, 3), round(sz, 3))


# ---------------------------------------------------------------------------
# Existing Material Introspection (for UV/Image & Source Color Preservation)
# ---------------------------------------------------------------------------


@dataclass
class SourceSlotInfo:
    slot_index: int
    material_name: str
    base_color: Optional[Tuple[float, float, float]]
    image: Optional[bpy.types.Image]
    uv_map_name: str
    has_alpha_link: bool
    metallic_hint: float
    roughness_hint: float


def _extract_source_slot_info(mat: Optional[bpy.types.Material], slot_index: int) -> SourceSlotInfo:
    """Inspect an existing material slot to preserve authored UV images and base hues."""
    if mat is None:
        return SourceSlotInfo(slot_index, "", None, None, "", False, 0.0, 0.5)

    base_color: Optional[Tuple[float, float, float]] = None
    found_image: Optional[bpy.types.Image] = None
    uv_map_name = ""
    has_alpha_link = False
    metallic_hint = 0.0
    roughness_hint = 0.5

    if mat.use_nodes and mat.node_tree is not None:
        nodes = mat.node_tree.nodes
        principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if principled is not None:
            bc_sock = principled.inputs.get("Base Color")
            if bc_sock is not None:
                c = bc_sock.default_value
                base_color = (float(c[0]), float(c[1]), float(c[2]))
                if bc_sock.is_linked:
                    found_image, uv_map_name = _trace_image_upstream(bc_sock.links[0].from_node)
            alpha_sock = principled.inputs.get("Alpha")
            if alpha_sock is not None and alpha_sock.is_linked:
                has_alpha_link = True
            m_sock = principled.inputs.get("Metallic")
            if m_sock is not None:
                metallic_hint = float(m_sock.default_value)
            r_sock = principled.inputs.get("Roughness")
            if r_sock is not None:
                roughness_hint = float(r_sock.default_value)

        if found_image is None:
            for node in nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    info = _inspect_image_datablock(node.image)
                    if info["loaded_ok"] or node.image.packed_file is not None:
                        found_image = node.image
                        uv_map_name = _extract_uv_map_from_tex(node)
                        break
    else:
        c = mat.diffuse_color
        base_color = (float(c[0]), float(c[1]), float(c[2]))

    # Ignore uninitialized Blender default gray (0.8, 0.8, 0.8) as a non-authored color.
    if base_color is not None and all(abs(ch - 0.8) < 1e-3 for ch in base_color):
        base_color = None

    return SourceSlotInfo(
        slot_index=slot_index,
        material_name=mat.name,
        base_color=base_color,
        image=found_image,
        uv_map_name=uv_map_name,
        has_alpha_link=has_alpha_link,
        metallic_hint=metallic_hint,
        roughness_hint=roughness_hint,
    )


def _extract_uv_map_from_tex(tex_node: bpy.types.Node) -> str:
    vec = tex_node.inputs.get("Vector")
    if vec is None or not vec.is_linked:
        return ""
    cur = vec.links[0].from_node
    visited = set()
    while cur is not None and cur not in visited:
        visited.add(cur)
        if cur.type == "UVMAP":
            return getattr(cur, "uv_map", "") or ""
        next_node = None
        for inp in cur.inputs:
            if inp.is_linked:
                next_node = inp.links[0].from_node
                break
        cur = next_node
    return ""


def _trace_image_upstream(node: bpy.types.Node, depth: int = 0) -> Tuple[Optional[bpy.types.Image], str]:
    if node is None or depth > 8:
        return None, ""
    if node.type == "TEX_IMAGE" and node.image is not None:
        info = _inspect_image_datablock(node.image)
        if info["loaded_ok"] or node.image.packed_file is not None:
            return node.image, _extract_uv_map_from_tex(node)
    for inp in node.inputs:
        if inp.is_linked:
            img, uv_name = _trace_image_upstream(inp.links[0].from_node, depth + 1)
            if img is not None:
                return img, uv_name
    return None, ""


def _has_any_token(text: str, tokens: Sequence[str]) -> bool:
    return any(tok in text for tok in tokens)


# ---------------------------------------------------------------------------
# Architectural Material Builders (Real Genie Sim Textures, World-Scale Box)
# ---------------------------------------------------------------------------


def _build_architectural_material(
    mat_name: str,
    imgs: Dict[str, Optional[bpy.types.Image]],
    tile_meters: float,
    obj_scale: Tuple[float, float, float],
    rgh_range: Tuple[float, float],
    nor_strength: float,
    coat_weight: float,
    macro_variation: float,
) -> bpy.types.Material:
    """Build a world-scale box-projected architectural floor/wall PBR material."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-1180, 0)

    # Scale local Object coordinates by object's world scale -> true meters aligned to box axes.
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-960, 0)
    mapping.vector_type = "POINT"
    inv_tile = 1.0 / max(tile_meters, 0.05)
    mapping.inputs["Scale"].default_value = (
        obj_scale[0] * inv_tile,
        obj_scale[1] * inv_tile,
        obj_scale[2] * inv_tile,
    )
    nt.links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # Large-scale metric coordinate for subtle occupied-room macro wear (breaks up wide-shot tiling).
    macro_map = nt.nodes.new("ShaderNodeMapping")
    macro_map.location = (-960, -320)
    macro_map.vector_type = "POINT"
    macro_map.inputs["Scale"].default_value = (
        obj_scale[0] * 0.28,
        obj_scale[1] * 0.28,
        obj_scale[2] * 0.28,
    )
    nt.links.new(tex_coord.outputs["Object"], macro_map.inputs["Vector"])

    macro_noise = nt.nodes.new("ShaderNodeTexNoise")
    macro_noise.location = (-720, -320)
    macro_noise.inputs["Scale"].default_value = 1.0
    macro_noise.inputs["Detail"].default_value = 4.0
    macro_noise.inputs["Roughness"].default_value = 0.62
    nt.links.new(macro_map.outputs["Vector"], macro_noise.inputs["Vector"])

    # Albedo (*_Alb.jpg, sRGB)
    alb_img = imgs.get("albedo")
    if alb_img is not None:
        alb_tex = nt.nodes.new("ShaderNodeTexImage")
        alb_tex.location = (-660, 260)
        alb_tex.image = alb_img
        alb_tex.projection = "BOX"
        alb_tex.projection_blend = 0.18
        alb_tex.extension = "REPEAT"
        alb_tex.interpolation = "Cubic"
        nt.links.new(mapping.outputs["Vector"], alb_tex.inputs["Vector"])

        # Gentle macro tonal modulation (0.94..1.04) so wide shots feel lived-in without altering hues.
        macro_tone = nt.nodes.new("ShaderNodeMapRange")
        macro_tone.location = (-420, 440)
        macro_tone.clamp = True
        macro_tone.inputs["From Min"].default_value = 0.25
        macro_tone.inputs["From Max"].default_value = 0.75
        macro_tone.inputs["To Min"].default_value = 1.0 - macro_variation
        macro_tone.inputs["To Max"].default_value = 1.0 + (macro_variation * 0.5)
        nt.links.new(macro_noise.outputs["Fac"], macro_tone.inputs["Value"])

        mix_alb = nt.nodes.new("ShaderNodeMix")
        mix_alb.data_type = "RGBA"
        mix_alb.blend_type = "MULTIPLY"
        mix_alb.clamp_factor = True
        mix_alb.clamp_result = True
        mix_alb.location = (-120, 260)
        fac, a_sock, b_sock, res = _mix_rgba_sockets(mix_alb)
        fac.default_value = 1.0
        nt.links.new(alb_tex.outputs["Color"], a_sock)
        nt.links.new(macro_tone.outputs["Result"], b_sock)
        nt.links.new(res, bsdf.inputs["Base Color"])

    # Roughness (*_Rgh.jpg, Non-Color) clamped to realistic non-mirror range
    rgh_img = imgs.get("roughness")
    rgh_min, rgh_max = rgh_range
    if rgh_img is not None:
        rgh_tex = nt.nodes.new("ShaderNodeTexImage")
        rgh_tex.location = (-660, -20)
        rgh_tex.image = rgh_img
        rgh_tex.projection = "BOX"
        rgh_tex.projection_blend = 0.18
        rgh_tex.extension = "REPEAT"
        rgh_tex.interpolation = "Cubic"
        nt.links.new(mapping.outputs["Vector"], rgh_tex.inputs["Vector"])

        rgh_map = nt.nodes.new("ShaderNodeMapRange")
        rgh_map.location = (-360, -20)
        rgh_map.clamp = True
        rgh_map.inputs["From Min"].default_value = 0.0
        rgh_map.inputs["From Max"].default_value = 1.0
        rgh_map.inputs["To Min"].default_value = rgh_min
        rgh_map.inputs["To Max"].default_value = rgh_max
        nt.links.new(rgh_tex.outputs["Color"], rgh_map.inputs["Value"])

        # Add subtle wear shift (+/- 0.05) clamped safely above mirror threshold.
        wear_shift = nt.nodes.new("ShaderNodeMapRange")
        wear_shift.location = (-360, -260)
        wear_shift.clamp = True
        wear_shift.inputs["From Min"].default_value = 0.2
        wear_shift.inputs["From Max"].default_value = 0.8
        wear_shift.inputs["To Min"].default_value = -0.045
        wear_shift.inputs["To Max"].default_value = 0.055
        nt.links.new(macro_noise.outputs["Fac"], wear_shift.inputs["Value"])

        add_rgh = nt.nodes.new("ShaderNodeMath")
        add_rgh.operation = "ADD"
        add_rgh.use_clamp = False
        add_rgh.location = (-120, -40)
        nt.links.new(rgh_map.outputs["Result"], add_rgh.inputs[0])
        nt.links.new(wear_shift.outputs["Result"], add_rgh.inputs[1])

        clamp_rgh = nt.nodes.new("ShaderNodeClamp")
        clamp_rgh.location = (60, -40)
        clamp_rgh.inputs["Min"].default_value = max(0.26, rgh_min - 0.03)
        clamp_rgh.inputs["Max"].default_value = min(0.96, rgh_max + 0.04)
        nt.links.new(add_rgh.outputs["Value"], clamp_rgh.inputs["Value"])
        nt.links.new(clamp_rgh.outputs["Result"], bsdf.inputs["Roughness"])
    else:
        _set_input(bsdf, "Roughness", 0.5 * (rgh_min + rgh_max))

    # Normal (*_Nor.jpg, Non-Color) routed explicitly through ShaderNodeNormalMap
    nor_img = imgs.get("normal")
    if nor_img is not None:
        nor_tex = nt.nodes.new("ShaderNodeTexImage")
        nor_tex.location = (-660, -560)
        nor_tex.image = nor_img
        nor_tex.projection = "BOX"
        nor_tex.projection_blend = 0.18
        nor_tex.extension = "REPEAT"
        nor_tex.interpolation = "Cubic"
        nt.links.new(mapping.outputs["Vector"], nor_tex.inputs["Vector"])

        nor_map = nt.nodes.new("ShaderNodeNormalMap")
        nor_map.location = (-260, -560)
        nor_map.space = "TANGENT"
        nor_map.inputs["Strength"].default_value = nor_strength
        nt.links.new(nor_tex.outputs["Color"], nor_map.inputs["Color"])
        nt.links.new(nor_map.outputs["Normal"], bsdf.inputs["Normal"])

    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.42 if coat_weight == 0.0 else 0.50)
    _set_input(bsdf, "Coat Weight", coat_weight)
    if coat_weight > 0.0:
        _set_input(bsdf, "Coat Roughness", 0.22)
    return mat


# ---------------------------------------------------------------------------
# Preserved UV/Image Material Builder (Signage, Labels, Paper Graphics, Humans, Robot Markings)
# ---------------------------------------------------------------------------


def _build_preserved_uv_material(
    mat_name: str,
    image: bpy.types.Image,
    uv_map_name: str,
    category: str,
    has_alpha: bool = False,
) -> bpy.types.Material:
    """Reuse an authored UV/image while calibrating physical response under AgX."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    _set_colorspace(image, "sRGB")
    mat, nt, bsdf, _ = _new_material(mat_name)

    if uv_map_name:
        uv_node = nt.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map = uv_map_name
        uv_node.location = (-660, 120)
        uv_out = uv_node.outputs["UV"]
    else:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tc.location = (-660, 120)
        uv_out = tc.outputs["UV"]

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-380, 120)
    tex.image = image
    tex.projection = "FLAT"
    tex.interpolation = "Cubic"
    nt.links.new(uv_out, tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if has_alpha:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])

    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Emission Strength", 0.0)

    if category == "human_skin":
        _set_input(bsdf, "Roughness", 0.52)
        _set_input(bsdf, "Specular IOR Level", 0.42)
        _set_input(bsdf, "Subsurface Weight", 0.12)
        _set_input(bsdf, "Subsurface Radius", (1.0, 0.35, 0.20))
        _set_input(bsdf, "Subsurface Scale", 0.008)
    elif category == "human_cloth":
        _set_input(bsdf, "Roughness", 0.86)
        _set_input(bsdf, "Specular IOR Level", 0.28)
        _set_input(bsdf, "Sheen Weight", 0.25)
        _set_input(bsdf, "Sheen Roughness", 0.65)
    elif category == "carton_printed":
        # Preserve printed carton graphics with real cardboard fiber roughness (0.72..0.86).
        tc_obj = nt.nodes.new("ShaderNodeTexCoord")
        tc_obj.location = (-780, -240)
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.location = (-520, -240)
        noise.inputs["Scale"].default_value = 95.0
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.72
        nt.links.new(tc_obj.outputs["Object"], noise.inputs["Vector"])

        rgh = nt.nodes.new("ShaderNodeMapRange")
        rgh.location = (-260, -200)
        rgh.clamp = True
        rgh.inputs["To Min"].default_value = 0.72
        rgh.inputs["To Max"].default_value = 0.86
        nt.links.new(noise.outputs["Fac"], rgh.inputs["Value"])
        nt.links.new(rgh.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.location = (-80, -340)
        bump.inputs["Strength"].default_value = 0.055
        bump.inputs["Distance"].default_value = 0.001
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        _set_input(bsdf, "Specular IOR Level", 0.34)
        _set_input(bsdf, "Sheen Weight", 0.06)
    elif category == "ceramic_printed":
        _set_input(bsdf, "Roughness", 0.26)
        _set_input(bsdf, "Specular IOR Level", 0.52)
        _set_input(bsdf, "Coat Weight", 0.85)
        _set_input(bsdf, "Coat Roughness", 0.07)
        _set_input(bsdf, "Coat IOR", 1.54)
    elif category == "switch_panel":
        _set_input(bsdf, "Roughness", 0.42)
        _set_input(bsdf, "Specular IOR Level", 0.48)
        _set_input(bsdf, "Coat Weight", 0.16)
        _set_input(bsdf, "Coat Roughness", 0.20)
        _add_bevel_normal(nt, bsdf, radius=0.0018, samples=4)
    elif category == "robot_marking":
        _set_input(bsdf, "Roughness", 0.38)
        _set_input(bsdf, "Specular IOR Level", 0.48)
        _set_input(bsdf, "Coat Weight", 0.12)
        _set_input(bsdf, "Coat Roughness", 0.22)
        _add_bevel_normal(nt, bsdf, radius=0.0018, samples=4)
    else:
        # Paper graphics, shipping marks, signage, labels: crisp readable ink, never emissive.
        _set_input(bsdf, "Roughness", 0.74)
        _set_input(bsdf, "Specular IOR Level", 0.36)
        _set_input(bsdf, "Coat Weight", 0.0)
    return mat


# ---------------------------------------------------------------------------
# Hero & Industrial Procedural PBR Material Builders
# ---------------------------------------------------------------------------


def _build_carton_material(mat_name: str, obj_scale: Tuple[float, float, float]) -> bpy.types.Material:
    """Kraft corrugated cardboard fiber with roughness ~0.72-0.88 and cellulose texture."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1080, 0)

    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-880, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    # Fine isotropic kraft cellulose fibers
    fiber_fine = nt.nodes.new("ShaderNodeTexNoise")
    fiber_fine.location = (-640, 140)
    fiber_fine.inputs["Scale"].default_value = 85.0
    fiber_fine.inputs["Detail"].default_value = 9.0
    fiber_fine.inputs["Roughness"].default_value = 0.74
    nt.links.new(metric.outputs["Vector"], fiber_fine.inputs["Vector"])

    # Subtle directional flute/grain variation
    flute_map = nt.nodes.new("ShaderNodeMapping")
    flute_map.location = (-880, -220)
    flute_map.inputs["Scale"].default_value = (
        obj_scale[0] * 18.0,
        obj_scale[1] * 2.2,
        obj_scale[2] * 18.0,
    )
    nt.links.new(tc.outputs["Object"], flute_map.inputs["Vector"])

    flute_noise = nt.nodes.new("ShaderNodeTexNoise")
    flute_noise.location = (-640, -220)
    flute_noise.inputs["Scale"].default_value = 4.0
    flute_noise.inputs["Detail"].default_value = 5.0
    flute_noise.inputs["Roughness"].default_value = 0.65
    nt.links.new(flute_map.outputs["Vector"], flute_noise.inputs["Vector"])

    # Kraft brown albedo variation (linear RGB calibrated for AgX)
    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.location = (-280, 220)
    fac, a_sock, b_sock, res = _mix_rgba_sockets(mix_col)
    a_sock.default_value = (0.31, 0.20, 0.11, 1.0)
    b_sock.default_value = (0.43, 0.29, 0.16, 1.0)
    nt.links.new(fiber_fine.outputs["Fac"], fac)
    nt.links.new(res, bsdf.inputs["Base Color"])

    # Roughness strictly in 0.72..0.88 range
    rgh_map = nt.nodes.new("ShaderNodeMapRange")
    rgh_map.location = (-280, -20)
    rgh_map.clamp = True
    rgh_map.inputs["From Min"].default_value = 0.20
    rgh_map.inputs["From Max"].default_value = 0.80
    rgh_map.inputs["To Min"].default_value = 0.72
    rgh_map.inputs["To Max"].default_value = 0.88
    nt.links.new(fiber_fine.outputs["Fac"], rgh_map.inputs["Value"])
    nt.links.new(rgh_map.outputs["Result"], bsdf.inputs["Roughness"])

    # Combine fiber + subtle flute into tactile cardboard micro-bump
    bump_mix = nt.nodes.new("ShaderNodeMath")
    bump_mix.operation = "MULTIPLY_ADD"
    bump_mix.location = (-360, -280)
    nt.links.new(fiber_fine.outputs["Fac"], bump_mix.inputs[0])
    bump_mix.inputs[1].default_value = 0.7
    nt.links.new(flute_noise.outputs["Fac"], bump_mix.inputs[2])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-140, -280)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0012
    nt.links.new(bump_mix.outputs["Value"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=0.0015, upstream_normal=bump.outputs["Normal"], samples=4)

    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.34)
    _set_input(bsdf, "Sheen Weight", 0.08)
    _set_input(bsdf, "Sheen Roughness", 0.75)
    return mat


def _build_metal_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    variant: str,
    tint: Optional[Tuple[float, float, float]] = None,
) -> bpy.types.Material:
    """Machined steel, brushed steel, precision bearing, or anodized aluminum with real anisotropic edge catch."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1080, 0)

    if variant == "bearing":
        base_col = tint or (0.74, 0.76, 0.79)
        metallic = 1.0
        rgh_min, rgh_max = 0.08, 0.16
        aniso = 0.68
        brush_stretch = (14.0, 14.0, 140.0)
        bump_str = 0.015
        bevel_r = 0.0018
    elif variant == "brushed_steel":
        base_col = tint or (0.60, 0.62, 0.65)
        metallic = 0.98
        rgh_min, rgh_max = 0.17, 0.30
        aniso = 0.76
        brush_stretch = (18.0, 160.0, 18.0)
        bump_str = 0.028
        bevel_r = 0.0024
    elif variant == "hero_metal":
        base_col = tint or (0.68, 0.70, 0.73)
        metallic = 0.98
        rgh_min, rgh_max = 0.14, 0.26
        aniso = 0.62
        brush_stretch = (24.0, 130.0, 24.0)
        bump_str = 0.022
        bevel_r = 0.0022
    elif variant == "robot_blue_anodized":
        base_col = tint or (0.06, 0.28, 0.56)
        metallic = 0.84
        rgh_min, rgh_max = 0.24, 0.34
        aniso = 0.35
        brush_stretch = (35.0, 35.0, 35.0)
        bump_str = 0.016
        bevel_r = 0.0022
    elif variant == "robot_aluminum":
        base_col = tint or (0.66, 0.68, 0.70)
        metallic = 0.92
        rgh_min, rgh_max = 0.22, 0.34
        aniso = 0.48
        brush_stretch = (28.0, 95.0, 28.0)
        bump_str = 0.020
        bevel_r = 0.0024
    elif variant == "robot_dark_housing":
        base_col = tint or (0.055, 0.060, 0.068)
        metallic = 0.38
        rgh_min, rgh_max = 0.34, 0.46
        aniso = 0.20
        brush_stretch = (55.0, 55.0, 55.0)
        bump_str = 0.024
        bevel_r = 0.0024
    else:  # general machined steel
        base_col = tint or (0.56, 0.58, 0.61)
        metallic = 0.97
        rgh_min, rgh_max = 0.18, 0.32
        aniso = 0.58
        brush_stretch = (22.0, 120.0, 22.0)
        bump_str = 0.026
        bevel_r = 0.0025

    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-860, 0)
    mapping.inputs["Scale"].default_value = (
        obj_scale[0] * brush_stretch[0],
        obj_scale[1] * brush_stretch[1],
        obj_scale[2] * brush_stretch[2],
    )
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.location = (-620, 0)
    grain.inputs["Scale"].default_value = 1.8
    grain.inputs["Detail"].default_value = 8.0
    grain.inputs["Roughness"].default_value = 0.65
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])

    # Subtle reflectance modulation along brushed grain
    col_var = nt.nodes.new("ShaderNodeMix")
    col_var.data_type = "RGBA"
    col_var.location = (-280, 200)
    fac, a_sock, b_sock, res = _mix_rgba_sockets(col_var)
    a_sock.default_value = (base_col[0] * 0.92, base_col[1] * 0.92, base_col[2] * 0.92, 1.0)
    b_sock.default_value = (min(1.0, base_col[0] * 1.06), min(1.0, base_col[1] * 1.06), min(1.0, base_col[2] * 1.06), 1.0)
    nt.links.new(grain.outputs["Fac"], fac)
    nt.links.new(res, bsdf.inputs["Base Color"])

    rgh_map = nt.nodes.new("ShaderNodeMapRange")
    rgh_map.location = (-280, -20)
    rgh_map.clamp = True
    rgh_map.inputs["From Min"].default_value = 0.25
    rgh_map.inputs["From Max"].default_value = 0.75
    rgh_map.inputs["To Min"].default_value = rgh_min
    rgh_map.inputs["To Max"].default_value = rgh_max
    nt.links.new(grain.outputs["Fac"], rgh_map.inputs["Value"])
    nt.links.new(rgh_map.outputs["Result"], bsdf.inputs["Roughness"])

    # Radial tangent aligns anisotropic reflections cleanly around shafts, bearings, and robot tubes.
    tangent = nt.nodes.new("ShaderNodeTangent")
    tangent.location = (-280, -200)
    tangent.direction_type = "RADIAL"
    tangent.axis = "Z"
    nt.links.new(tangent.outputs["Tangent"], bsdf.inputs["Tangent"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-160, -340)
    bump.inputs["Strength"].default_value = bump_str
    bump.inputs["Distance"].default_value = 0.0006
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=bevel_r, upstream_normal=bump.outputs["Normal"], samples=4)

    _set_input(bsdf, "Metallic", metallic)
    _set_input(bsdf, "Anisotropic", aniso)
    _set_input(bsdf, "Anisotropic Rotation", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.55)
    return mat


def _build_powder_enamel_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    base_color: Tuple[float, float, float],
    is_safety_orange: bool = False,
) -> bpy.types.Material:
    """Lightly coated painted safety trim or industrial powder-coated machine enamel (zero self-emission)."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-980, 0)

    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-780, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    # Fine industrial powder-coat orange-peel micro-texture
    peel = nt.nodes.new("ShaderNodeTexNoise")
    peel.location = (-540, -100)
    peel.inputs["Scale"].default_value = 240.0 if not is_safety_orange else 180.0
    peel.inputs["Detail"].default_value = 5.0
    peel.inputs["Roughness"].default_value = 0.55
    nt.links.new(metric.outputs["Vector"], peel.inputs["Vector"])

    rgh_map = nt.nodes.new("ShaderNodeMapRange")
    rgh_map.location = (-260, -20)
    rgh_map.clamp = True
    rgh_map.inputs["From Min"].default_value = 0.25
    rgh_map.inputs["From Max"].default_value = 0.75
    if is_safety_orange:
        rgh_map.inputs["To Min"].default_value = 0.34
        rgh_map.inputs["To Max"].default_value = 0.44
    else:
        rgh_map.inputs["To Min"].default_value = 0.38
        rgh_map.inputs["To Max"].default_value = 0.52
    nt.links.new(peel.outputs["Fac"], rgh_map.inputs["Value"])
    nt.links.new(rgh_map.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-160, -260)
    bump.inputs["Strength"].default_value = 0.025 if is_safety_orange else 0.042
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(peel.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(
        nt,
        bsdf,
        radius=0.0024 if is_safety_orange else 0.0030,
        upstream_normal=bump.outputs["Normal"],
        samples=4,
    )

    _set_input(bsdf, "Base Color", base_color)
    _set_input(bsdf, "Metallic", 0.0 if is_safety_orange else 0.10)
    _set_input(bsdf, "Specular IOR Level", 0.50)
    _set_input(bsdf, "Coat Weight", 0.30 if is_safety_orange else 0.18)
    _set_input(bsdf, "Coat Roughness", 0.15 if is_safety_orange else 0.22)
    _set_input(bsdf, "Coat IOR", 1.50)
    # Strictly zero orange self-emission!
    _set_input(bsdf, "Emission Strength", 0.0)
    return mat


def _build_rubber_material(mat_name: str, obj_scale: Tuple[float, float, float]) -> bpy.types.Material:
    """Matte vulcanized industrial rubber (wheels, tires, pads, cables, bumpers)."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-960, 0)

    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-760, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.location = (-520, -60)
    grain.inputs["Scale"].default_value = 175.0
    grain.inputs["Detail"].default_value = 7.0
    grain.inputs["Roughness"].default_value = 0.68
    nt.links.new(metric.outputs["Vector"], grain.inputs["Vector"])

    rgh_map = nt.nodes.new("ShaderNodeMapRange")
    rgh_map.location = (-260, -20)
    rgh_map.clamp = True
    rgh_map.inputs["From Min"].default_value = 0.20
    rgh_map.inputs["From Max"].default_value = 0.80
    rgh_map.inputs["To Min"].default_value = 0.74
    rgh_map.inputs["To Max"].default_value = 0.90
    nt.links.new(grain.outputs["Fac"], rgh_map.inputs["Value"])
    nt.links.new(rgh_map.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-160, -260)
    bump.inputs["Strength"].default_value = 0.048
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=0.0020, upstream_normal=bump.outputs["Normal"], samples=4)

    _set_input(bsdf, "Base Color", (0.036, 0.038, 0.041))
    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.28)
    _set_input(bsdf, "Coat Weight", 0.0)
    return mat


def _build_glazed_ceramic_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    base_color: Optional[Tuple[float, float, float]] = None,
) -> bpy.types.Material:
    """Native vitrified glazed ceramic (cups, mugs, bowls) with clear glaze coat."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-920, 0)

    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-720, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    glaze = nt.nodes.new("ShaderNodeTexNoise")
    glaze.location = (-480, -140)
    glaze.inputs["Scale"].default_value = 32.0
    glaze.inputs["Detail"].default_value = 3.0
    glaze.inputs["Roughness"].default_value = 0.45
    nt.links.new(metric.outputs["Vector"], glaze.inputs["Vector"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-160, -220)
    bump.inputs["Strength"].default_value = 0.014
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(glaze.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=0.0016, upstream_normal=bump.outputs["Normal"], samples=4)

    col = base_color or (0.78, 0.76, 0.71)
    # Keep white ceramic below 0.85 linear so glazed highlights read cleanly without blowing out.
    col = tuple(min(0.84, c) for c in col)
    _set_input(bsdf, "Base Color", col)
    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Roughness", 0.24)
    _set_input(bsdf, "Specular IOR Level", 0.54)
    _set_input(bsdf, "Coat Weight", 0.88)
    _set_input(bsdf, "Coat Roughness", 0.065)
    _set_input(bsdf, "Coat IOR", 1.54)
    _set_input(bsdf, "Subsurface Weight", 0.035)
    _set_input(bsdf, "Subsurface Scale", 0.004)
    return mat


def _build_wood_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    base_color: Optional[Tuple[float, float, float]] = None,
) -> bpy.types.Material:
    """Natural industrial workbench/pallet/furniture wood with metric grain and pore roughness."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1080, 0)

    # Stretched 8:1 along X for plausible plank/butcher-block grain in meters
    grain_map = nt.nodes.new("ShaderNodeMapping")
    grain_map.location = (-860, 0)
    grain_map.inputs["Scale"].default_value = (
        obj_scale[0] * 1.4,
        obj_scale[1] * 11.5,
        obj_scale[2] * 11.5,
    )
    nt.links.new(tc.outputs["Object"], grain_map.inputs["Vector"])

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.location = (-620, 40)
    grain.inputs["Scale"].default_value = 3.2
    grain.inputs["Detail"].default_value = 9.0
    grain.inputs["Roughness"].default_value = 0.62
    grain.inputs["Distortion"].default_value = 0.85
    nt.links.new(grain_map.outputs["Vector"], grain.inputs["Vector"])

    c_dark = (base_color[0] * 0.62, base_color[1] * 0.56, base_color[2] * 0.48) if base_color else (0.20, 0.11, 0.055)
    c_light = (min(0.85, base_color[0] * 1.05), min(0.85, base_color[1] * 1.02), min(0.85, base_color[2] * 0.96)) if base_color else (0.42, 0.25, 0.12)

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.location = (-280, 200)
    fac, a_sock, b_sock, res = _mix_rgba_sockets(mix_col)
    a_sock.default_value = (*c_dark, 1.0)
    b_sock.default_value = (*c_light, 1.0)
    nt.links.new(grain.outputs["Fac"], fac)
    nt.links.new(res, bsdf.inputs["Base Color"])

    rgh_map = nt.nodes.new("ShaderNodeMapRange")
    rgh_map.location = (-280, -20)
    rgh_map.clamp = True
    rgh_map.inputs["From Min"].default_value = 0.25
    rgh_map.inputs["From Max"].default_value = 0.78
    rgh_map.inputs["To Min"].default_value = 0.46
    rgh_map.inputs["To Max"].default_value = 0.72
    nt.links.new(grain.outputs["Fac"], rgh_map.inputs["Value"])
    nt.links.new(rgh_map.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-160, -260)
    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=0.0024, upstream_normal=bump.outputs["Normal"], samples=4)

    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.44)
    _set_input(bsdf, "Coat Weight", 0.12)
    _set_input(bsdf, "Coat Roughness", 0.28)
    return mat


def _build_paper_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    base_color: Optional[Tuple[float, float, float]] = None,
) -> bpy.types.Material:
    """Uncoated matte paper calibrated to preserve highlight detail without clipping under AgX."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-900, 0)
    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-700, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    fiber = nt.nodes.new("ShaderNodeTexNoise")
    fiber.location = (-480, -80)
    fiber.inputs["Scale"].default_value = 260.0
    fiber.inputs["Detail"].default_value = 6.0
    fiber.inputs["Roughness"].default_value = 0.70
    nt.links.new(metric.outputs["Vector"], fiber.inputs["Vector"])

    rgh = nt.nodes.new("ShaderNodeMapRange")
    rgh.location = (-240, -20)
    rgh.clamp = True
    rgh.inputs["To Min"].default_value = 0.80
    rgh.inputs["To Max"].default_value = 0.92
    nt.links.new(fiber.outputs["Fac"], rgh.inputs["Value"])
    nt.links.new(rgh.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-120, -220)
    bump.inputs["Strength"].default_value = 0.02
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(fiber.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Physical paper reflectance (~0.66-0.72 linear) never clips under bright key lights.
    col = base_color or (0.70, 0.68, 0.64)
    col = tuple(min(0.74, c) for c in col)
    _set_input(bsdf, "Base Color", col)
    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.30)
    _set_input(bsdf, "Subsurface Weight", 0.02)
    _set_input(bsdf, "Subsurface Scale", 0.002)
    return mat


def _build_glass_material(mat_name: str) -> bpy.types.Material:
    """Clear safety polycarbonate / tempered glass for guided machine doors and enclosures."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    _set_input(bsdf, "Base Color", (0.94, 0.97, 0.96))
    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Roughness", 0.05)
    _set_input(bsdf, "IOR", 1.52)
    _set_input(bsdf, "Transmission Weight", 0.88)
    _set_input(bsdf, "Coat Weight", 0.20)
    _set_input(bsdf, "Coat Roughness", 0.04)
    _add_bevel_normal(nt, bsdf, radius=0.0015, samples=4)
    if hasattr(mat, "use_raytrace_refraction"):
        mat.use_raytrace_refraction = True
    return mat


def _build_polymer_material(
    mat_name: str,
    obj_scale: Tuple[float, float, float],
    base_color: Optional[Tuple[float, float, float]] = None,
) -> bpy.types.Material:
    """Calibrated industrial satin-matte polymer / tote / electronics housing."""
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing

    mat, nt, bsdf, _ = _new_material(mat_name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-920, 0)
    metric = nt.nodes.new("ShaderNodeMapping")
    metric.location = (-720, 0)
    metric.inputs["Scale"].default_value = obj_scale
    nt.links.new(tc.outputs["Object"], metric.inputs["Vector"])

    stipple = nt.nodes.new("ShaderNodeTexNoise")
    stipple.location = (-480, -100)
    stipple.inputs["Scale"].default_value = 210.0
    stipple.inputs["Detail"].default_value = 5.0
    stipple.inputs["Roughness"].default_value = 0.60
    nt.links.new(metric.outputs["Vector"], stipple.inputs["Vector"])

    rgh = nt.nodes.new("ShaderNodeMapRange")
    rgh.location = (-240, -20)
    rgh.clamp = True
    rgh.inputs["From Min"].default_value = 0.25
    rgh.inputs["From Max"].default_value = 0.75
    rgh.inputs["To Min"].default_value = 0.38
    rgh.inputs["To Max"].default_value = 0.56
    nt.links.new(stipple.outputs["Fac"], rgh.inputs["Value"])
    nt.links.new(rgh.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-140, -240)
    bump.inputs["Strength"].default_value = 0.022
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(stipple.outputs["Fac"], bump.inputs["Height"])
    _add_bevel_normal(nt, bsdf, radius=0.0020, upstream_normal=bump.outputs["Normal"], samples=4)

    col = base_color or (0.24, 0.26, 0.29)
    _set_input(bsdf, "Base Color", col)
    _set_input(bsdf, "Metallic", 0.0)
    _set_input(bsdf, "Specular IOR Level", 0.48)
    return mat


# ---------------------------------------------------------------------------
# Role & Slot Classification
# ---------------------------------------------------------------------------


def _color_key(col: Optional[Tuple[float, float, float]]) -> str:
    if col is None:
        return "def"
    return f"{int(round(col[0] * 255)):02x}{int(round(col[1] * 255)):02x}{int(round(col[2] * 255)):02x}"


def _classify_robot_variant(combined_name: str, slot_info: SourceSlotInfo) -> str:
    if _has_any_token(combined_name, _RUBBER_TOKENS):
        return "rubber"
    if _has_any_token(combined_name, ("blue", "cap", "endcap", "ur_blue", "accent")):
        return "robot_blue_anodized"
    if _has_any_token(combined_name, ("bearing", "pin", "bolt", "screw", "shaft", "steel")):
        return "bearing"
    if _has_any_token(combined_name, ("dark", "black", "robotiq", "gripper", "joint", "base", "housing", "body", "coupler")):
        return "robot_dark_housing"
    if _has_any_token(combined_name, ("alum", "silver", "tube", "link", "forearm", "upper", "wrist", "arm", "flange", "light")):
        return "robot_aluminum"
    if slot_info.base_color is not None:
        r, g, b = slot_info.base_color
        if b > r * 1.4 and b > g * 1.15 and b > 0.15:
            return "robot_blue_anodized"
        if (r + g + b) / 3.0 < 0.14:
            return "robot_dark_housing"
    return "robot_aluminum"


def _classify_slot(
    obj_name: str,
    role: str,
    slot_info: SourceSlotInfo,
) -> Tuple[str, Optional[str]]:
    """Return (material_class, preserve_category_or_None) for one object material slot."""
    role_l = role.strip().lower()
    mat_l = slot_info.material_name.strip().lower()
    obj_l = obj_name.strip().lower()
    combined = f"{role_l} {mat_l} {obj_l}"

    # Architectural floor & wall always receive real Genie Sim tileable sets.
    if _has_any_token(role_l, _FLOOR_TOKENS):
        return "floor", None
    if _has_any_token(role_l, _WALL_TOKENS):
        return "wall", None

    # Explicit UV/image preservation for labels, signage, paper graphics, humans, switches, robot markings.
    if _has_any_token(role_l, _PRESERVE_UV_TOKENS) or _has_any_token(mat_l, _PRESERVE_UV_TOKENS):
        if _has_any_token(combined, ("switch", "button", "estop", "e_stop", "panel", "pendant", "keypad")):
            return ("preserve_uv", "switch_panel") if slot_info.image is not None else ("switch_panel", None)
        return ("preserve_uv", "signage_label") if slot_info.image is not None else ("paper", None)

    if _has_any_token(role_l, _HUMAN_TOKENS) or _has_any_token(mat_l, _HUMAN_TOKENS) or _has_any_token(obj_l, _HUMAN_TOKENS):
        is_skin = _has_any_token(combined, ("skin", "face", "head", "hand", "arm_human", "neck"))
        cat = "human_skin" if is_skin else "human_cloth"
        if slot_info.image is not None:
            return "preserve_uv", cat
        return cat, None

    # Any non-architectural slot carrying an authored image texture preserves its UV/image!
    if slot_info.image is not None:
        if _has_any_token(combined, _CARTON_TOKENS):
            return "preserve_uv", "carton_printed"
        if _has_any_token(combined, _CERAMIC_TOKENS):
            return "preserve_uv", "ceramic_printed"
        if _has_any_token(combined, _ROBOT_TOKENS):
            return "preserve_uv", "robot_marking"
        return "preserve_uv", "signage_label"

    # Untextured physical material classes
    if _has_any_token(role_l, _CARTON_TOKENS) or _has_any_token(mat_l, _CARTON_TOKENS):
        return "carton", None
    if _has_any_token(role_l, _ORANGE_TRIM_TOKENS) or _has_any_token(mat_l, _ORANGE_TRIM_TOKENS):
        return "hero_orange", None
    if _has_any_token(role_l, _BEARING_TOKENS) or _has_any_token(mat_l, _BEARING_TOKENS):
        return "bearing", None
    if _has_any_token(role_l, _BRUSHED_STEEL_TOKENS) or _has_any_token(mat_l, _BRUSHED_STEEL_TOKENS):
        return "brushed_steel", None
    if _has_any_token(role_l, _POWDER_ENAMEL_TOKENS) or _has_any_token(mat_l, _POWDER_ENAMEL_TOKENS):
        return "powder_enamel", None
    if _has_any_token(role_l, _RUBBER_TOKENS) or _has_any_token(mat_l, _RUBBER_TOKENS):
        return "rubber", None
    if _has_any_token(role_l, _CERAMIC_TOKENS) or _has_any_token(mat_l, _CERAMIC_TOKENS):
        return "ceramic", None
    if _has_any_token(role_l, _GLASS_TOKENS) or _has_any_token(mat_l, _GLASS_TOKENS):
        return "glass", None
    if _has_any_token(role_l, _WOOD_TOKENS) or _has_any_token(mat_l, _WOOD_TOKENS):
        return "wood", None
    if _has_any_token(role_l, _PAPER_TOKENS) or _has_any_token(mat_l, _PAPER_TOKENS):
        return "paper", None
    if _has_any_token(role_l, _ROBOT_TOKENS) or _has_any_token(mat_l, _ROBOT_TOKENS) or _has_any_token(obj_l, _ROBOT_TOKENS):
        return _classify_robot_variant(combined, slot_info), None
    if _has_any_token(role_l, _STEEL_METAL_TOKENS) or _has_any_token(mat_l, _STEEL_METAL_TOKENS):
        if "hero_metal" in role_l or "aluminum" in combined or "billet" in combined or "cnc" in combined:
            return "hero_metal", None
        return "steel", None
    if _has_any_token(role_l, _PLASTIC_TOKENS) or _has_any_token(mat_l, _PLASTIC_TOKENS):
        return "polymer", None

    # Fallback: honor authored metallic/color cues cleanly
    if slot_info.metallic_hint >= 0.65:
        return "steel", None
    return "polymer", None


def _collect_material_images(mat: bpy.types.Material) -> List[Dict[str, Any]]:
    """Inspect every live TEX_IMAGE node actually wired in a material node tree."""
    found: List[Dict[str, Any]] = []
    if not mat or not mat.use_nodes or mat.node_tree is None:
        return found
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            info = _inspect_image_datablock(node.image)
            found.append(info)
    return found


# ---------------------------------------------------------------------------
# Public Function 1: retexture(objects, k, genie_root)
# ---------------------------------------------------------------------------


def retexture(
    objects: Iterable[Tuple[bpy.types.Object, str]],
    k: int,
    genie_root: Any,
) -> Dict[str, Any]:
    """Assign physically calibrated PBR shaders and verified Genie Sim floor/wall sets.

    Restricts all edits strictly to material appearance: mesh geometry, transforms,
    UV layers, and original custom/split normals are never modified.
    """
    setting = _normalize_k(k)
    textures_dir = _resolve_textures_dir(genie_root)

    floor_stem, floor_imgs, floor_img_infos = _load_pbr_texture_set(
        textures_dir, setting.floor_stem, VERIFIED_FLOOR_SETS
    )
    wall_stem, wall_imgs, wall_img_infos = _load_pbr_texture_set(
        textures_dir, setting.wall_stem, VERIFIED_WALL_SETS
    )

    items = list(objects)
    mapped_objects: List[Dict[str, Any]] = []
    skipped_objects: List[Dict[str, Any]] = []
    loaded_images_index: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def _record_image(channel: str, role_label: str, info: Dict[str, Any]) -> None:
        if not info or not info.get("file_name"):
            return
        key = (channel, role_label, str(info["file_name"]))
        if key not in loaded_images_index:
            loaded_images_index[key] = {
                "channel": channel,
                "role": role_label,
                "file_name": info["file_name"],
                "datablock_name": info["datablock_name"],
                "size": info["size"],
                "channels": info["channels"],
                "colorspace": info["colorspace"],
                "loaded_ok": info["loaded_ok"],
            }

    for ch, info in floor_img_infos.items():
        if info.get("loaded_ok"):
            _record_image(ch, f"floor:{floor_stem}", info)
    for ch, info in wall_img_infos.items():
        if info.get("loaded_ok"):
            _record_image(ch, f"wall:{wall_stem}", info)

    prefix = f"LD_k{setting.k:02d}_{setting.name}"

    for entry in items:
        if not isinstance(entry, (tuple, list)) or len(entry) < 2:
            skipped_objects.append({"reason": "invalid_entry", "entry": repr(entry)})
            continue
        obj, raw_role = entry[0], entry[1]
        role = (raw_role or "").strip().lower()
        if obj is None or getattr(obj, "type", None) != "MESH" or obj.data is None:
            skipped_objects.append({
                "object_name": getattr(obj, "name", None),
                "role": role,
                "reason": "non_mesh_or_none",
            })
            continue

        mesh = obj.data
        obj_scale = _object_metric_scale(obj)
        scale_tag = f"{obj_scale[0]:.2f}_{obj_scale[1]:.2f}_{obj_scale[2]:.2f}"

        # Snapshot existing slots before reassigning so UV/images and base hues are preserved.
        slot_count = len(mesh.materials)
        source_slots: List[SourceSlotInfo] = (
            [_extract_source_slot_info(mesh.materials[i], i) for i in range(slot_count)]
            if slot_count > 0
            else [SourceSlotInfo(0, "", None, None, "", False, 0.0, 0.5)]
        )

        assigned_mats: List[bpy.types.Material] = []
        slot_classes: List[str] = []
        preserved_files: List[str] = []
        assigned_tex_files: List[str] = []

        for sinfo in source_slots:
            mat_class, preserve_cat = _classify_slot(obj.name, role, sinfo)
            slot_classes.append(mat_class)
            ckey = _color_key(sinfo.base_color)

            if mat_class == "floor":
                mname = f"{prefix}_floor_{floor_stem or 'fallback'}_{scale_tag}"
                mat = _build_architectural_material(
                    mname,
                    floor_imgs,
                    setting.floor_tile_m,
                    obj_scale,
                    setting.floor_rgh_range,
                    setting.floor_nor_strength,
                    setting.floor_coat,
                    macro_variation=0.055,
                )
            elif mat_class == "wall":
                mname = f"{prefix}_wall_{wall_stem or 'fallback'}_{scale_tag}"
                mat = _build_architectural_material(
                    mname,
                    wall_imgs,
                    setting.wall_tile_m,
                    obj_scale,
                    setting.wall_rgh_range,
                    setting.wall_nor_strength,
                    setting.wall_coat,
                    macro_variation=0.04,
                )
            elif mat_class == "preserve_uv" and sinfo.image is not None:
                img_tag = "".join(c if c.isalnum() or c in "._-" else "_" for c in sinfo.image.name)[:36]
                mname = f"{prefix}_uv_{preserve_cat}_{img_tag}"
                mat = _build_preserved_uv_material(
                    mname,
                    sinfo.image,
                    sinfo.uv_map_name,
                    preserve_cat or "signage_label",
                    has_alpha=sinfo.has_alpha_link,
                )
                img_info = _inspect_image_datablock(sinfo.image)
                if img_info["file_name"]:
                    preserved_files.append(img_info["file_name"])
                    _record_image("preserved_uv", role or preserve_cat or "uv", img_info)
            elif mat_class == "carton":
                mat = _build_carton_material(f"{prefix}_carton_{scale_tag}", obj_scale)
            elif mat_class in ("bearing", "brushed_steel", "hero_metal", "steel", "robot_blue_anodized", "robot_aluminum", "robot_dark_housing"):
                tint = sinfo.base_color if mat_class in ("robot_blue_anodized", "robot_dark_housing") else None
                mat = _build_metal_material(
                    f"{prefix}_{mat_class}_{ckey}_{scale_tag}",
                    obj_scale,
                    mat_class,
                    tint=tint,
                )
            elif mat_class == "hero_orange":
                # Keep authentic painted safety-orange chroma without self-emission.
                orange_col = sinfo.base_color if (sinfo.base_color and sinfo.base_color[0] > 0.35 and sinfo.base_color[0] > sinfo.base_color[2] * 2.0) else (0.76, 0.19, 0.03)
                mat = _build_powder_enamel_material(
                    f"{prefix}_safety_orange_{ckey}_{scale_tag}",
                    obj_scale,
                    orange_col,
                    is_safety_orange=True,
                )
            elif mat_class == "powder_enamel":
                enamel_col = sinfo.base_color or (0.18, 0.21, 0.24)
                mat = _build_powder_enamel_material(
                    f"{prefix}_powder_enamel_{ckey}_{scale_tag}",
                    obj_scale,
                    enamel_col,
                    is_safety_orange=False,
                )
            elif mat_class == "rubber":
                mat = _build_rubber_material(f"{prefix}_rubber_{scale_tag}", obj_scale)
            elif mat_class == "ceramic":
                mat = _build_glazed_ceramic_material(
                    f"{prefix}_ceramic_{ckey}_{scale_tag}",
                    obj_scale,
                    base_color=sinfo.base_color,
                )
            elif mat_class == "wood":
                mat = _build_wood_material(
                    f"{prefix}_wood_{ckey}_{scale_tag}",
                    obj_scale,
                    base_color=sinfo.base_color,
                )
            elif mat_class == "paper":
                mat = _build_paper_material(
                    f"{prefix}_paper_{ckey}_{scale_tag}",
                    obj_scale,
                    base_color=sinfo.base_color,
                )
            elif mat_class == "glass":
                mat = _build_glass_material(f"{prefix}_glass")
            elif mat_class == "switch_panel":
                panel_col = sinfo.base_color or (0.14, 0.15, 0.17)
                mat = _build_powder_enamel_material(
                    f"{prefix}_switch_panel_{ckey}_{scale_tag}",
                    obj_scale,
                    panel_col,
                    is_safety_orange=False,
                )
            elif mat_class == "human_skin":
                skin_col = sinfo.base_color or (0.52, 0.33, 0.24)
                mname = f"{prefix}_skin_{ckey}"
                mat = bpy.data.materials.get(mname)
                if mat is None:
                    mat, _, bsdf, _ = _new_material(mname)
                    _set_input(bsdf, "Base Color", tuple(min(0.68, c) for c in skin_col))
                    _set_input(bsdf, "Roughness", 0.52)
                    _set_input(bsdf, "Specular IOR Level", 0.42)
                    _set_input(bsdf, "Subsurface Weight", 0.12)
                    _set_input(bsdf, "Subsurface Radius", (1.0, 0.35, 0.20))
                    _set_input(bsdf, "Subsurface Scale", 0.008)
            elif mat_class == "human_cloth":
                cloth_col = sinfo.base_color or (0.16, 0.20, 0.26)
                mname = f"{prefix}_cloth_{ckey}"
                mat = bpy.data.materials.get(mname)
                if mat is None:
                    mat, _, bsdf, _ = _new_material(mname)
                    _set_input(bsdf, "Base Color", cloth_col)
                    _set_input(bsdf, "Roughness", 0.86)
                    _set_input(bsdf, "Specular IOR Level", 0.28)
                    _set_input(bsdf, "Sheen Weight", 0.25)
                    _set_input(bsdf, "Sheen Roughness", 0.65)
            else:
                mat = _build_polymer_material(
                    f"{prefix}_polymer_{ckey}_{scale_tag}",
                    obj_scale,
                    base_color=sinfo.base_color,
                )

            assigned_mats.append(mat)
            for img_info in _collect_material_images(mat):
                if img_info["loaded_ok"] and img_info["file_name"]:
                    if img_info["file_name"] not in assigned_tex_files:
                        assigned_tex_files.append(img_info["file_name"])

        # Assign materials cleanly without touching mesh topology, UVs, or normals.
        if slot_count == 0:
            mesh.materials.append(assigned_mats[0])
        else:
            for idx, mat in enumerate(assigned_mats):
                mesh.materials[idx] = mat

        mapped_objects.append({
            "object_name": obj.name,
            "role": role,
            "material_classes": slot_classes,
            "assigned_materials": [m.name for m in assigned_mats],
            "preserved_uv_images": preserved_files,
            "loaded_texture_files": assigned_tex_files,
            "normals_preserved": True,
        })

    audit: Dict[str, Any] = {
        "stage": "retexture",
        "requested_k": k,
        "setting_k": setting.k,
        "setting_name": setting.name,
        "textures_dir": str(textures_dir),
        "active_floor_set": floor_stem,
        "active_wall_set": wall_stem,
        "loaded_images": list(loaded_images_index.values()),
        "mapped_objects": mapped_objects,
        "skipped_objects": skipped_objects,
    }

    if bpy.context.scene is not None:
        bpy.context.scene["lookdev_retexture_audit"] = json.dumps(audit)

    _print_retexture_audit(audit)
    return audit


# ---------------------------------------------------------------------------
# Lighting Helpers (Scene Envelope Analysis, Aiming, Engine & AgX Calibration)
# ---------------------------------------------------------------------------


def _compute_scene_bounds(scene: bpy.types.Scene) -> Tuple[Vector, Vector, Vector]:
    """Compute (min_corner, max_corner, workcell_center) over visible scene mesh objects."""
    all_pts: List[Vector] = []
    hero_pts: List[Vector] = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        span = Vector((
            max(p.x for p in corners) - min(p.x for p in corners),
            max(p.y for p in corners) - min(p.y for p in corners),
            max(p.z for p in corners) - min(p.z for p in corners),
        ))
        # Exclude extreme sky domes (> 150 m) from room envelope calculation.
        if max(span.x, span.y, span.z) > 150.0:
            continue
        all_pts.extend(corners)
        name_l = obj.name.lower()
        is_arch = any(t in name_l for t in ("floor", "wall", "ceiling", "roof", "room", "corridor"))
        if not is_arch and max(span.x, span.y) < 8.0:
            hero_pts.extend(corners)

    if not all_pts:
        return Vector((-2.5, -2.5, 0.0)), Vector((2.5, 2.5, 3.0)), Vector((0.0, 0.0, 0.85))

    bb_min = Vector((min(p.x for p in all_pts), min(p.y for p in all_pts), min(p.z for p in all_pts)))
    bb_max = Vector((max(p.x for p in all_pts), max(p.y for p in all_pts), max(p.z for p in all_pts)))

    if hero_pts:
        h_min = Vector((min(p.x for p in hero_pts), min(p.y for p in hero_pts), min(p.z for p in hero_pts)))
        h_max = Vector((max(p.x for p in hero_pts), max(p.y for p in hero_pts), max(p.z for p in hero_pts)))
        center = (h_min + h_max) * 0.5
    else:
        center = Vector((
            0.5 * (bb_min.x + bb_max.x),
            0.5 * (bb_min.y + bb_max.y),
            bb_min.z + min(1.0, 0.35 * max(bb_max.z - bb_min.z, 2.5)),
        ))

    return bb_min, bb_max, center


def _clamp_inside_envelope(
    pos: Vector,
    bb_min: Vector,
    bb_max: Vector,
    has_enclosed_walls: bool,
    margin: float = 0.28,
) -> Vector:
    """Keep fixtures inside enclosed room shells so solid walls/ceilings never block light."""
    if not has_enclosed_walls:
        return pos
    x = max(bb_min.x + margin, min(bb_max.x - margin, pos.x))
    y = max(bb_min.y + margin, min(bb_max.y - margin, pos.y))
    z = max(bb_min.z + 0.6, min(bb_max.z - margin, pos.z))
    return Vector((x, y, z))


def _remove_previous_lights(scene: bpy.types.Scene) -> List[str]:
    """Remove all existing scene lights cleanly before installing motivated fixtures."""
    removed: List[str] = []
    light_objs = [obj for obj in list(scene.objects) if obj.type == "LIGHT"]
    for obj in light_objs:
        removed.append(obj.name)
        ldata = obj.data
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        if obj.users == 0:
            bpy.data.objects.remove(obj, do_unlink=True)
        if ldata is not None and ldata.users == 0:
            bpy.data.lights.remove(ldata, do_unlink=True)
    return removed


def _neutralize_render_tint(scene: bpy.types.Scene) -> List[str]:
    """Strip any legacy color-tint compositor nodes or white-balance shifts."""
    actions: List[str] = []
    vs = scene.view_settings
    if getattr(vs, "use_curve_mapping", False):
        vs.use_curve_mapping = False
        actions.append("disabled_view_curve_mapping")
    if hasattr(vs, "use_white_balance") and vs.use_white_balance:
        vs.use_white_balance = False
        actions.append("disabled_view_white_balance")

    if scene.use_nodes and scene.node_tree is not None:
        tint_types = {
            "COLORBALANCE",
            "HUE_SAT",
            "RGBTOBW",
            "COLORCORRECTION",
            "BRIGHTCONTRAST",
            "EXPOSURE",
            "TONEMAP",
        }
        for node in scene.node_tree.nodes:
            if node.type in tint_types and not node.mute:
                node.mute = True
                actions.append(f"muted_compositor_{node.name}")
    return actions


def _configure_world_hdri(
    scene: bpy.types.Scene,
    setting: SettingProfile,
    textures_dir: Path,
) -> Dict[str, Any]:
    """Configure scene world using strictly a verified real HDR under textures_dir."""
    if scene.world is None:
        scene.world = bpy.data.worlds.new(name=f"LD_World_k{setting.k:02d}_{setting.name}")
    world = scene.world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    hdri_img, hdri_info = _load_verified_hdri(textures_dir, setting.hdri_file)

    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (640, 0)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-720, 0)

    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-500, 0)
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(setting.hdri_rot_deg))
    nt.links.new(tc.outputs["Generated"], mapping.inputs["Vector"])

    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.location = (-240, 0)
    if hdri_img is not None:
        env.image = hdri_img
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])

    # Gentle saturation discipline prevents unwanted color cast while preserving true photographic sky/room reflections.
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.location = (20, 0)
    hsv.inputs["Hue"].default_value = 0.5
    hsv.inputs["Saturation"].default_value = setting.hdri_saturation
    hsv.inputs["Value"].default_value = 1.0
    nt.links.new(env.outputs["Color"], hsv.inputs["Color"])

    bg_illum = nt.nodes.new("ShaderNodeBackground")
    bg_illum.location = (240, 120)
    bg_illum.inputs["Strength"].default_value = setting.hdri_strength
    nt.links.new(hsv.outputs["Color"], bg_illum.inputs["Color"])

    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.location = (240, -100)
    bg_cam.inputs["Strength"].default_value = setting.hdri_camera_strength
    nt.links.new(hsv.outputs["Color"], bg_cam.inputs["Color"])

    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (240, 300)

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.location = (440, 40)
    nt.links.new(lp.outputs["Is Camera Ray"], mix_sh.inputs["Fac"])
    nt.links.new(bg_illum.outputs["Background"], mix_sh.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

    # Re-inspect live node image datablock for verified audit output.
    live_info = _inspect_image_datablock(env.image)
    live_info.update({
        "rotation_deg": setting.hdri_rot_deg,
        "illumination_strength": setting.hdri_strength,
        "camera_strength": setting.hdri_camera_strength,
    })
    return live_info


def _create_area_light(
    scene: bpy.types.Scene,
    name: str,
    location: Vector,
    target: Optional[Vector],
    size_xy: Tuple[float, float],
    kelvin: float,
    watts: float,
    spread_deg: float,
    euler_override: Optional[Euler] = None,
    shadow_max_res: float = 0.002,
) -> Tuple[bpy.types.Object, Dict[str, Any]]:
    """Create a static, motivated physical AREA luminaire with soft penumbra and grounded shadows."""
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.shape = "RECTANGLE"
    ldata.size = float(size_xy[0])
    ldata.size_y = float(size_xy[1])
    ldata.energy = float(watts)
    ldata.color = _kelvin_to_linear_rgb(kelvin)
    if hasattr(ldata, "spread"):
        ldata.spread = math.radians(max(20.0, min(180.0, float(spread_deg))))
    if hasattr(ldata, "use_shadow"):
        ldata.use_shadow = True
    if hasattr(ldata, "shadow_filter_radius"):
        ldata.shadow_filter_radius = 1.6
    if hasattr(ldata, "shadow_maximum_resolution"):
        ldata.shadow_maximum_resolution = shadow_max_res
    if hasattr(ldata, "use_shadow_jitter"):
        ldata.use_shadow_jitter = True

    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    scene.collection.objects.link(lobj)
    lobj.location = location

    if euler_override is not None:
        lobj.rotation_euler = euler_override
    elif target is not None:
        direction = (target - location)
        if direction.length > 1e-6:
            lobj.rotation_euler = direction.normalized().to_track_quat("-Z", "Y").to_euler()

    # Keep luminaire panels invisible to direct camera rays while driving real diffuse & specular reflections.
    for attr, val in (
        ("visible_camera", False),
        ("visible_diffuse", True),
        ("visible_glossy", True),
        ("visible_transmission", True),
    ):
        if hasattr(lobj, attr):
            setattr(lobj, attr, val)

    return lobj, {
        "name": lobj.name,
        "type": "AREA_RECTANGLE",
        "location": [round(v, 3) for v in lobj.location],
        "size_m": [round(size_xy[0], 3), round(size_xy[1], 3)],
        "kelvin": round(kelvin, 1),
        "energy_watts": round(watts, 2),
        "spread_deg": round(spread_deg, 1),
    }


def _configure_color_management_and_engines(
    scene: bpy.types.Scene,
    setting: SettingProfile,
) -> Dict[str, Any]:
    """Configure AgX (fixed exposure, no auto-exposure) and deterministic Cycles + EEVEE Next."""
    vs = scene.view_settings
    # Select AgX safely.
    try:
        vs.view_transform = "AgX"
    except TypeError:
        pass
    for look_candidate in ("AgX - Base Contrast", "AgX - Medium Low Contrast", "None"):
        try:
            vs.look = look_candidate
            break
        except TypeError:
            continue
    vs.exposure = float(setting.exposure)
    vs.gamma = 1.0
    if hasattr(vs, "use_curve_mapping"):
        vs.use_curve_mapping = False

    # Preserve caller's choice of Cycles or EEVEE Next; upgrade legacy Workbench/EEVEE if needed.
    engine = scene.render.engine
    if engine not in ("CYCLES", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = "CYCLES"
            engine = "CYCLES"
        except TypeError:
            pass

    # Deterministic Cycles settings (no per-frame seed, no highlight clipping on steel).
    if hasattr(scene, "cycles"):
        cyc = scene.cycles
        if hasattr(cyc, "use_animated_seed"):
            cyc.use_animated_seed = False
        if hasattr(cyc, "seed"):
            cyc.seed = 0
        if hasattr(cyc, "sample_clamp_direct"):
            cyc.sample_clamp_direct = 0.0  # preserve crisp bright steel specular highlights
        if hasattr(cyc, "sample_clamp_indirect"):
            cyc.sample_clamp_indirect = 8.0
        if hasattr(cyc, "max_bounces"):
            cyc.max_bounces = 8
        if hasattr(cyc, "diffuse_bounces"):
            cyc.diffuse_bounces = 4
        if hasattr(cyc, "glossy_bounces"):
            cyc.glossy_bounces = 4
        if hasattr(cyc, "transmission_bounces"):
            cyc.transmission_bounces = 6
        if hasattr(cyc, "transparent_max_bounces"):
            cyc.transparent_max_bounces = 8
        if hasattr(cyc, "caustics_reflective"):
            cyc.caustics_reflective = False
        if hasattr(cyc, "caustics_refractive"):
            cyc.caustics_refractive = False
        if hasattr(cyc, "use_adaptive_sampling"):
            cyc.use_adaptive_sampling = True
        if hasattr(cyc, "adaptive_threshold"):
            cyc.adaptive_threshold = 0.02
        if hasattr(cyc, "use_denoising"):
            cyc.use_denoising = True
        if hasattr(cyc, "denoising_input_passes"):
            try:
                cyc.denoising_input_passes = "RGB_ALBEDO_NORMAL"
            except TypeError:
                pass

    # Deterministic EEVEE Next settings (soft penumbra, raytraced reflections & contact bounce, zero flicker).
    if hasattr(scene, "eevee"):
        ee = scene.eevee
        if hasattr(ee, "use_shadows"):
            ee.use_shadows = True
        if hasattr(ee, "shadow_ray_count"):
            ee.shadow_ray_count = 2
        if hasattr(ee, "shadow_step_count"):
            ee.shadow_step_count = 6
        if hasattr(ee, "shadow_resolution_scale"):
            ee.shadow_resolution_scale = 1.0
        if hasattr(ee, "use_shadow_jitter_viewport"):
            ee.use_shadow_jitter_viewport = False
        if hasattr(ee, "use_raytracing"):
            ee.use_raytracing = True
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = max(64, int(ee.taa_render_samples))
        if hasattr(ee, "use_taa_reprojection"):
            ee.use_taa_reprojection = False
        rto = getattr(ee, "ray_tracing_options", None)
        if rto is not None:
            if hasattr(rto, "trace_max_roughness"):
                rto.trace_max_roughness = 0.65
            if hasattr(rto, "resolution_scale"):
                try:
                    rto.resolution_scale = "2"
                except TypeError:
                    pass

    return {
        "engine": scene.render.engine,
        "view_transform": vs.view_transform,
        "look": vs.look,
        "exposure": round(float(vs.exposure), 3),
        "gamma": round(float(vs.gamma), 3),
        "animated_seed": False,
    }


# ---------------------------------------------------------------------------
# Public Function 2: light(scene, k, genie_root)
# ---------------------------------------------------------------------------


def light(
    scene: bpy.types.Scene,
    k: int,
    genie_root: Any,
) -> Dict[str, Any]:
    """Install motivated daylight window key, cool sky fill, warm practical linear
    luminaires, verified real HDRI world, and deterministic AgX render settings.

    No moving lamps, no auto-exposure, no per-frame seeds, no camera modifications.
    """
    setting = _normalize_k(k)
    textures_dir = _resolve_textures_dir(genie_root)

    removed_lights = _remove_previous_lights(scene)
    tint_actions = _neutralize_render_tint(scene)
    hdri_audit = _configure_world_hdri(scene, setting, textures_dir)
    render_audit = _configure_color_management_and_engines(scene, setting)

    bb_min, bb_max, center = _compute_scene_bounds(scene)
    span_x = max(bb_max.x - bb_min.x, 3.2)
    span_y = max(bb_max.y - bb_min.y, 3.2)
    raw_height = bb_max.z - bb_min.z
    has_enclosed_walls = raw_height >= 2.2 and min(span_x, span_y) >= 2.4
    room_h = max(2.8, min(raw_height if has_enclosed_walls else (4.6 if setting.is_large_room else 3.2), 7.5))
    ceiling_z = (bb_max.z - 0.16) if has_enclosed_walls else (bb_min.z + room_h)

    horiz_radius = max(2.2, min(0.45 * min(span_x, span_y), 5.2 if setting.is_large_room else 3.8))
    ref_dist = 3.5

    created_lights: List[Dict[str, Any]] = []

    # 1. Motivated Natural Daylight Window Key (directional crown/side window)
    az = math.radians(setting.key_azimuth_deg)
    el = math.radians(setting.key_elevation_deg)
    key_dist = max(2.6, horiz_radius * 1.05)
    key_offset = Vector((
        math.cos(az) * math.cos(el) * key_dist,
        math.sin(az) * math.cos(el) * key_dist,
        math.sin(el) * key_dist,
    ))
    key_pos = _clamp_inside_envelope(center + key_offset, bb_min, bb_max, has_enclosed_walls, margin=0.26)
    actual_key_dist = max(1.4, (key_pos - center).length)
    key_watts = setting.key_watts_ref * ((actual_key_dist / ref_dist) ** 2)
    _, key_info = _create_area_light(
        scene=scene,
        name=f"LD_k{setting.k:02d}_Daylight_Window_Key",
        location=key_pos,
        target=center,
        size_xy=setting.key_size,
        kelvin=setting.key_kelvin,
        watts=key_watts,
        spread_deg=setting.key_spread_deg,
        shadow_max_res=0.002,
    )
    created_lights.append(key_info)

    # 2. Cool Sky Fill (broad opposite-side skylight bounce preserving contact shadows)
    fill_az = az + math.radians(155.0)
    fill_el = math.radians(24.0)
    fill_dist = max(2.8, horiz_radius * 1.1)
    fill_offset = Vector((
        math.cos(fill_az) * math.cos(fill_el) * fill_dist,
        math.sin(fill_az) * math.cos(fill_el) * fill_dist,
        math.sin(fill_el) * fill_dist,
    ))
    fill_pos = _clamp_inside_envelope(center + fill_offset, bb_min, bb_max, has_enclosed_walls, margin=0.28)
    actual_fill_dist = max(1.6, (fill_pos - center).length)
    fill_watts = setting.fill_watts_ref * ((actual_fill_dist / ref_dist) ** 2)
    _, fill_info = _create_area_light(
        scene=scene,
        name=f"LD_k{setting.k:02d}_Cool_Sky_Fill",
        location=fill_pos,
        target=center,
        size_xy=(setting.key_size[0] * 1.25, setting.key_size[1] * 1.15),
        kelvin=setting.fill_kelvin,
        watts=fill_watts,
        spread_deg=142.0,
        shadow_max_res=0.004,
    )
    created_lights.append(fill_info)

    # 3. Motivated Overhead Linear Practical Luminaires (create bright steel & edge specular strips)
    yaw_rad = math.radians(setting.practical_yaw_deg)
    lateral = Vector((-math.sin(yaw_rad), math.cos(yaw_rad), 0.0))
    strip_len = 2.4 if setting.is_large_room else 1.85
    strip_w = 0.20 if setting.is_large_room else 0.16
    fixture_spacing = max(0.85, min(0.24 * min(span_x, span_y), 1.65))
    fixture_z = max(center.z + 1.35, min(ceiling_z - 0.12, center.z + 2.8))

    for idx, sign in enumerate((-1.0, 1.0), start=1):
        p_pos = Vector((
            center.x + lateral.x * sign * fixture_spacing,
            center.y + lateral.y * sign * fixture_spacing,
            fixture_z,
        ))
        p_pos = _clamp_inside_envelope(p_pos, bb_min, bb_max, has_enclosed_walls, margin=0.22)
        p_dist = max(1.3, (p_pos - center).length)
        p_watts = setting.practical_watts_ref * ((p_dist / 2.6) ** 2)
        _, p_info = _create_area_light(
            scene=scene,
            name=f"LD_k{setting.k:02d}_Practical_Linear_{idx}",
            location=p_pos,
            target=None,
            size_xy=(strip_len, strip_w),
            kelvin=setting.practical_kelvin,
            watts=p_watts,
            spread_deg=112.0,
            euler_override=Euler((0.0, 0.0, yaw_rad), "XYZ"),
            shadow_max_res=0.002,
        )
        created_lights.append(p_info)

    # 4. Warm Practical Edge / Chamfer Grazing Ribbon (rakes machined metal edges & bearings)
    rib_az = az - math.radians(125.0)
    rib_el = math.radians(34.0)
    rib_dist = max(2.0, min(horiz_radius * 0.88, 3.2))
    rib_offset = Vector((
        math.cos(rib_az) * math.cos(rib_el) * rib_dist,
        math.sin(rib_az) * math.cos(rib_el) * rib_dist,
        math.sin(rib_el) * rib_dist,
    ))
    rib_pos = _clamp_inside_envelope(center + rib_offset, bb_min, bb_max, has_enclosed_walls, margin=0.24)
    actual_rib_dist = max(1.3, (rib_pos - center).length)
    rib_watts = setting.ribbon_watts_ref * ((actual_rib_dist / 2.4) ** 2)
    _, rib_info = _create_area_light(
        scene=scene,
        name=f"LD_k{setting.k:02d}_Practical_Edge_Ribbon",
        location=rib_pos,
        target=center,
        size_xy=(1.55, 0.11),
        kelvin=setting.ribbon_kelvin,
        watts=rib_watts,
        spread_deg=86.0,
        shadow_max_res=0.002,
    )
    created_lights.append(rib_info)

    audit: Dict[str, Any] = {
        "stage": "light",
        "requested_k": k,
        "setting_k": setting.k,
        "setting_name": setting.name,
        "textures_dir": str(textures_dir),
        "environment_hdr": hdri_audit,
        "removed_previous_lights": removed_lights,
        "tint_cleanup": tint_actions,
        "created_lights": created_lights,
        "scene_bounds": {
            "min": [round(v, 3) for v in bb_min],
            "max": [round(v, 3) for v in bb_max],
            "workcell_center": [round(v, 3) for v in center],
            "enclosed_room_detected": has_enclosed_walls,
        },
        "render_and_color_management": render_audit,
    }

    scene["lookdev_light_audit"] = json.dumps(audit)
    _print_light_audit(audit)
    return audit


# ---------------------------------------------------------------------------
# Explicit Verified Audit Output Formatting
# ---------------------------------------------------------------------------


def _print_retexture_audit(audit: Dict[str, Any]) -> None:
    print(f"[LOOKDEV AUDIT: RETEXTURE] k={audit['setting_k']} ({audit['setting_name']})")
    print(
        f"  Verified architectural sets: floor={audit['active_floor_set']} | wall={audit['active_wall_set']}"
    )
    print(f"  Loaded image datablocks ({len(audit['loaded_images'])}):")
    for img in audit["loaded_images"]:
        w, h = img["size"]
        status = "OK" if img["loaded_ok"] else "FAILED"
        print(
            f"    - [{status}] role={img['role']} channel={img['channel']} "
            f"file={img['file_name']} datablock={img['datablock_name']} "
            f"{w}x{h} ch={img['channels']} cs={img['colorspace']}"
        )
    print(f"  Mapped mesh objects ({len(audit['mapped_objects'])}):")
    for mo in audit["mapped_objects"]:
        uv_str = f" preserved_uv={mo['preserved_uv_images']}" if mo["preserved_uv_images"] else ""
        tex_str = f" textures={mo['loaded_texture_files']}" if mo["loaded_texture_files"] else ""
        print(
            f"    - {mo['object_name']} (role='{mo['role']}') -> "
            f"class={mo['material_classes']} mats={mo['assigned_materials']}{uv_str}{tex_str}"
        )


def _print_light_audit(audit: Dict[str, Any]) -> None:
    hdr = audit["environment_hdr"]
    w, h = hdr["size"]
    status = "OK" if hdr["loaded_ok"] else "FAILED"
    print(f"[LOOKDEV AUDIT: LIGHT] k={audit['setting_k']} ({audit['setting_name']})")
    print(
        f"  Environment HDR: [{status}] file={hdr['file_name']} datablock={hdr['datablock_name']} "
        f"{w}x{h} ch={hdr['channels']} cs={hdr['colorspace']} "
        f"rot={hdr['rotation_deg']}deg strength={hdr['illumination_strength']}"
    )
    print(f"  Removed previous lights ({len(audit['removed_previous_lights'])}): {audit['removed_previous_lights']}")
    print(f"  Installed motivated lights ({len(audit['created_lights'])}):")
    for lt in audit["created_lights"]:
        print(
            f"    - {lt['name']}: pos={lt['location']} size={lt['size_m']}m "
            f"{lt['kelvin']}K {lt['energy_watts']}W spread={lt['spread_deg']}deg"
        )
    rm = audit["render_and_color_management"]
    print(
        f"  Render/Color: engine={rm['engine']} view={rm['view_transform']} "
        f"look='{rm['look']}' exposure={rm['exposure']} animated_seed={rm['animated_seed']}"
    )
