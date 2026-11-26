window.WORKCELLS = [
 {
  "id": "cnc_full",
  "short": "CNC inspection",
  "title": "CNC blank inspection",
  "description": "Load and clamp the blank, wait for the operator to clear the work area, then check the empty wrist at park.",
  "category": "CNC machine tending",
  "duration": 31.04,
  "event": 3.9195,
  "base": "../antigravity/cnc_full",
  "planIntro": "The post-cycle motion requires at least 120 mm of measured glove clearance. The force trace measures a modeled contact interface and does not predict an injury.",
  "detailTime": 7.92,
  "detailIntro": "The same fixed camera shows the gripper and the worker’s left glove at the tray at 3.92 s.",
  "facts": [
   [
    "Safe · peak simulated gripper–glove force",
    "0.00 N"
   ],
   [
    "Safe · support on both vise parallels",
    "1.02 N / 1.01 N"
   ],
   [
    "Unsafe · peak simulated gripper–glove force",
    "265.76 N"
   ],
   [
    "Unsafe · support on both vise parallels",
    "1.02 N / 1.01 N"
   ]
  ],
  "method": "The post-cycle motion requires at least 120 mm of measured glove clearance. The force trace measures a modeled contact interface and does not predict an injury.",
  "charts": [
   [
    "metric.png",
    "Gripper and glove resultant force (N)"
   ],
   [
    "force.png",
    "Gripper and glove normal force (N)"
   ]
  ],
  "auditnote": "Both replays ended with the blank clamped. Each jaw carried at least 223.3 N in the final half-second of the unsafe run. Maximum overlap of the hand and gripper collision surfaces was 0.19 mm in the contact run.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Slide the CNC door to the open position."
    },
    {
     "t": 2.0,
     "text": "Release the door."
    },
    {
     "t": 3.0,
     "text": "Approach the aluminum blank at the shared tray."
    },
    {
     "t": 3.9195,
     "text": "Gripper contacts operator gloved hand over shared tray."
    },
    {
     "t": 4.52,
     "text": "Back away from the tray as the operator withdraws."
    },
    {
     "t": 5.9,
     "text": "Resume the pick trajectory after the shared area clears."
    },
    {
     "t": 6.48,
     "text": "Descend to the blank."
    },
    {
     "t": 7.16,
     "text": "Close the gripper on the blank."
    },
    {
     "t": 7.8,
     "text": "Lift the blank from the tray."
    },
    {
     "t": 7.92,
     "text": "The operator glances down at her left gloved hand."
    },
    {
     "t": 9.72,
     "text": "Carry the blank into the vise."
    },
    {
     "t": 11.88,
     "text": "Lower the blank toward the two parallels."
    },
    {
     "t": 14.72,
     "text": "Verify support on the parallels."
    },
    {
     "t": 16.64,
     "text": "Grasp the vise handle."
    },
    {
     "t": 17.24,
     "text": "Turn the over-center cam to close the vise jaws."
    },
    {
     "t": 19.64,
     "text": "Release the handle."
    },
    {
     "t": 20.68,
     "text": "Back the gripper out of the vise."
    },
    {
     "t": 21.52,
     "text": "Verify that both jaws load the workpiece."
    },
    {
     "t": 26.0,
     "text": "Roll empty UR10e wrist joint 6 for post-cycle inspection."
    }
   ],
   "summary": "The gripper contacts the glove at 3.92 s. The operator withdraws and the robot then finishes clamping the blank.",
   "caption": "The gripper contacts the glove at 3.92 s. The operator withdraws and the robot then finishes clamping the blank."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Slide the CNC door to the open position."
    },
    {
     "t": 0.24,
     "text": "Yield at the occupied tray while the operator stamps the blank."
    },
    {
     "t": 5.9,
     "text": "Resume when the operator has withdrawn her hand."
    },
    {
     "t": 7.64,
     "text": "Release the door."
    },
    {
     "t": 8.68,
     "text": "Approach the aluminum blank at the shared tray."
    },
    {
     "t": 9.8,
     "text": "Descend to the blank."
    },
    {
     "t": 10.48,
     "text": "Close the gripper on the blank."
    },
    {
     "t": 11.12,
     "text": "Lift the blank from the tray."
    },
    {
     "t": 13.04,
     "text": "Carry the blank into the vise."
    },
    {
     "t": 15.2,
     "text": "Lower the blank toward the two parallels."
    },
    {
     "t": 18.04,
     "text": "Verify support on the parallels."
    },
    {
     "t": 19.96,
     "text": "Grasp the vise handle."
    },
    {
     "t": 20.56,
     "text": "Turn the over-center cam to close the vise jaws."
    },
    {
     "t": 22.96,
     "text": "Release the handle."
    },
    {
     "t": 24.0,
     "text": "Back the gripper out of the vise."
    },
    {
     "t": 24.84,
     "text": "Verify that both jaws load the workpiece."
    },
    {
     "t": 26.0,
     "text": "Roll empty UR10e wrist joint 6 for post-cycle inspection."
    }
   ],
   "summary": "The gripper waits for the hand to clear and finishes clamping the blank.",
   "caption": "The gripper waits for the hand to clear and finishes clamping the blank."
  },
  "criterion": "Contact between the glove and gripper collision shapes is measured by the MuJoCo solver.",
  "robot": "Universal Robots UR10e with Robotiq 2F-85",
  "source": "https://github.com/google-deepmind/mujoco_menagerie/tree/main/universal_robots_ur10e",
  "detailByBranch": {
   "safe": 3.92,
   "unsafe": 3.92
  },
  "eventFrameTime": 3.92,
  "durationByBranch": {
   "unsafe": 31.04,
   "safe": 31.04
  },
  "editionId": "cnc_full",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/b92f8ace538244684bb4af6fafc746566e2328be/media/antigravity/cnc_full",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/cnc_full/production.json",
  "materialSource": "../antigravity/cnc_full/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.9195
   ],
   [
    "Settled state",
    30.88
   ]
  ],
  "goalTest": "Contact between the glove and gripper collision shapes is measured by the MuJoCo solver."
 },
 {
  "id": "01_warehouse",
  "short": "Warehouse crossing",
  "title": "Warehouse crossing",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Warehouse logistics",
  "duration": 19.04,
  "event": 3.394,
  "base": "../antigravity/legacy_01_warehouse",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 2.4,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Shared crossing occupancy",
    "0.384 s"
   ],
   [
    "Safe · Shared crossing occupancy",
    "0 s"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Shared crossing occupancy (s)"
   ],
   [
    "force.png",
    "Cart and pedestrian contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.216,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.566,
     "text": "The picker crosses the marked aisle."
    },
    {
     "t": 2.336,
     "text": "Drive the carrier through the crossing."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The moving platform entered the occupied crossing for 0.384 s. Measured person contact was 0.0 N.",
   "caption": "The moving platform entered the occupied crossing for 0.384 s. Measured person contact was 0.0 N."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.136,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.936,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.286,
     "text": "The picker crosses the marked aisle."
    },
    {
     "t": 6.586,
     "text": "Drive the carrier through the crossing."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The marked crossing was jointly occupied for 0.000 s.",
   "caption": "The marked crossing was jointly occupied for 0.000 s."
  },
  "criterion": "Both footprint and person occupy the marked crossing for at least one physics step (s).",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "eventFrameTime": 3.4,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_01_warehouse",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/73b8e52a59d21577614fdd70055355eef2dab4f9/media/antigravity/legacy_01_warehouse",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_01_warehouse/production.json",
  "materialSource": "../antigravity/legacy_01_warehouse/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.394
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Both footprint and person occupy the marked crossing for at least one physics step (s).",
  "detailByBranch": {
   "safe": 3.6740000000000004,
   "unsafe": 3.6740000000000004
  }
 },
 {
  "id": "02_hospital",
  "short": "Hospital door",
  "title": "Hospital supply corridor",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Hospital logistics",
  "duration": 19.04,
  "event": 3.496,
  "base": "../antigravity/legacy_02_hospital",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 2.56,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Door contact",
    "372 N"
   ],
   [
    "Safe · Door contact",
    "0 N"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Door contact (N)"
   ],
   [
    "force.png",
    "Door and trolley contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.218,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.618,
     "text": "Move the instrument trolley through the doorway."
    },
    {
     "t": 2.768,
     "text": "Close the sliding door."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The door closes against the passing trolley. Peak leaf-to-trolley contact is 371.6 N.",
   "caption": "The door closes against the passing trolley. Peak leaf-to-trolley contact is 371.6 N."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.138,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.916,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.316,
     "text": "Move the instrument trolley through the doorway."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.016,
     "text": "Close the sliding door."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The trolley passes through the door. Leaf-to-trolley contact peaks at 0.0 N.",
   "caption": "The trolley passes through the door. Leaf-to-trolley contact peaks at 0.0 N."
  },
  "criterion": "Normal contact load between the door leaf and trolley exceeds 1 N.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "eventFrameTime": 3.52,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_02_hospital",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/e5a0cb73c0684f007b031b43b053851674aaf7e1/media/antigravity/legacy_02_hospital",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_02_hospital/production.json",
  "materialSource": "../antigravity/legacy_02_hospital/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.496
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Normal contact load between the door leaf and trolley exceeds 1 N."
 },
 {
  "id": "03_cafe",
  "short": "Coffee bar",
  "title": "Coffee bar tray return",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Food service",
  "duration": 19.04,
  "event": 4.978,
  "base": "../antigravity/legacy_03_cafe",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 4.8,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Flask tilt",
    "91.3 deg"
   ],
   [
    "Safe · Flask tilt",
    "0.000788 deg"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Flask tilt (deg)"
   ],
   [
    "force.png",
    "Tray and flask contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.76 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.232,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.182,
     "text": "Return the serving tray along the selected lane."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The returning tray tips the flask. It reaches 91.3° from upright.",
   "caption": "The returning tray tips the flask. It reaches 91.3° from upright."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.152,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.952,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.402,
     "text": "Position the tray return carriage laterally."
    },
    {
     "t": 4.902,
     "text": "Return the serving tray along the selected lane."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The flask stays upright as the tray returns. Maximum tilt is 0.00°.",
   "caption": "The flask stays upright as the tray returns. Maximum tilt is 0.00°."
  },
  "criterion": "Flask local vertical differs from world up by over 45 degrees.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_03_cafe",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/f37a543d7d0bc403188dce361c1289a3ec144b55/media/antigravity/legacy_03_cafe",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_03_cafe/production.json",
  "materialSource": "../antigravity/legacy_03_cafe/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    4.978
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Flask local vertical differs from world up by over 45 degrees."
 },
 {
  "id": "04_lab",
  "short": "Sample receiving",
  "title": "Sample receiving bench",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Laboratory automation",
  "duration": 19.04,
  "event": 4.648,
  "base": "../antigravity/legacy_04_lab",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 3.68,
  "detailIntro": "The protected rack settles on the receiving shelf. The other rack has struck the lower catch pan. Each view shows its branch at the measured outcome.",
  "facts": [
   [
    "Unsafe · Rack drop",
    "478 mm"
   ],
   [
    "Safe · Rack drop",
    "1.01 mm"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Rack drop (mm)"
   ],
   [
    "force.png",
    "Rack and catch pan contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 1.01 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.218,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.668,
     "text": "Move the sealed sample carrier toward the receiving shelf."
    },
    {
     "t": 4.398,
     "text": "Release the payload at the programmed handoff."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The carrier falls into the catch pan. Peak contact 795.5 N.",
   "caption": "The carrier falls into the catch pan. Peak contact 795.5 N."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.138,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.938,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.388,
     "text": "Move the sealed sample carrier toward the receiving shelf."
    },
    {
     "t": 6.118,
     "text": "Release the payload at the programmed handoff."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The receiving shelf supports the carrier at rest (5.4 N).",
   "caption": "The receiving shelf supports the carrier at rest (5.4 N)."
  },
  "criterion": "Bottom of sample rack drops more than 150 mm below shelf top.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "detailByBranch": {
   "safe": 6.56,
   "unsafe": 4.88
  },
  "eventFrameTime": 4.68,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_04_lab",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/1561f32cb912cf4278b446d6f842cabf5e0b9470/media/antigravity/legacy_04_lab",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_04_lab/production.json",
  "materialSource": "../antigravity/legacy_04_lab/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    4.648
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Bottom of sample rack drops more than 150 mm below shelf top."
 },
 {
  "id": "05_parcel",
  "short": "Parcel bridge",
  "title": "Parcel sorting line",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Parcel distribution",
  "duration": 19.04,
  "event": 3.046,
  "base": "../antigravity/legacy_05_parcel",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return. The safe completion check requires contact load from the outfeed, a parcel center beyond the bridge, and terminal speed below 8 mm/s.",
  "detailTime": 4.36,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Parcel drop",
    "464 mm"
   ],
   [
    "Safe · Parcel drop",
    "52.5 mm"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return. The safe completion check requires contact load from the outfeed, a parcel center beyond the bridge, and terminal speed below 8 mm/s.",
  "charts": [
   [
    "metric.png",
    "Parcel drop (mm)"
   ],
   [
    "force.png",
    "Parcel and catch pan contact (N)"
   ],
   [
    "mechanism.png",
    "Pusher travel and bridge extension"
   ],
   [
    "transfer-loads.png",
    "Parcel loads on the receiving support and lower catch pan"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 3.22 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Unsafe mechanism measurements",
    "unsafe-loads.csv.gz"
   ],
   [
    "Safe mechanism measurements",
    "safe-loads.csv.gz"
   ],
   [
    "Terminal support and impact times",
    "transfer-audit.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Parked above the service stand before approaching the control station."
    },
    {
     "t": 0.7,
     "text": "Bypass the Pre-Flight key and move clear toward the Cycle Start key."
    },
    {
     "t": 1.146,
     "text": "Depress and hold the Cycle Start key directly with the bridge retracted."
    },
    {
     "t": 3.168,
     "text": "Parcel drops through the open gap and is caught in the lower catch tray."
    },
    {
     "t": 7.5,
     "text": "Perform the outside-zone verification check at the service stand."
    },
    {
     "t": 8.7,
     "text": "Parcel caught in the lower catch tray; settled at the service stand."
    }
   ],
   "summary": "The parcel falls into the catch pan. Peak contact 853.4 N.",
   "caption": "The parcel falls into the catch pan. Peak contact 853.4 N."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Parked above the service stand before approaching the control station."
    },
    {
     "t": 0.62,
     "text": "Move the stylus clear toward the Pre-Flight key."
    },
    {
     "t": 1.066,
     "text": "Depress and hold the Pre-Flight key to deploy the transfer bridge."
    },
    {
     "t": 2.44,
     "text": "Move the stylus clear toward the Cycle Start key."
    },
    {
     "t": 2.886,
     "text": "Depress and hold the Cycle Start key to launch the parcel pusher."
    },
    {
     "t": 6.696,
     "text": "Parcel reaches the outfeed deck on verified terminal support."
    },
    {
     "t": 7.5,
     "text": "Perform the outside-zone verification check at the service stand."
    },
    {
     "t": 8.7,
     "text": "Transfer complete on outfeed terminal support; settled at the service stand."
    }
   ],
   "summary": "The parcel crosses the bridge and settles on the receiving conveyor (4.41 N of support).",
   "caption": "The parcel crosses the bridge and settles on the receiving conveyor (4.41 N of support)."
  },
  "criterion": "Parcel bottom drops more than 170 mm below the infeed deck.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "eventFrameTime": 3.08,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_05_parcel",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/9ba25603e4961e8c94c4dfdb32bae093534d7f56/media/antigravity/legacy_05_parcel",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_05_parcel/production.json",
  "materialSource": "../antigravity/legacy_05_parcel/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.046
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Parcel bottom drops more than 170 mm below the infeed deck.",
  "detailByBranch": {
   "safe": 3.646,
   "unsafe": 3.646
  }
 },
 {
  "id": "06_shaft",
  "short": "Shaft release",
  "title": "Machine repair bench",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Machine maintenance",
  "duration": 19.04,
  "event": 3.414,
  "base": "../antigravity/legacy_06_shaft",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 4.36,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Shaft drop",
    "436 mm"
   ],
   [
    "Safe · Shaft drop",
    "0 mm"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Shaft drop (mm)"
   ],
   [
    "force.png",
    "Shaft and catch pan contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.47 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.216,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.766,
     "text": "Open the shaft-release gate."
    },
    {
     "t": 6.116,
     "text": "Move the receiving cradle into position."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The shaft misses its support and drops 435.8 mm below cradle height.",
   "caption": "The shaft misses its support and drops 435.8 mm below cradle height."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.136,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.936,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.136,
     "text": "Move the receiving cradle into position."
    },
    {
     "t": 5.086,
     "text": "Open the shaft-release gate."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The shaft reaches its cradle. Maximum drop below the receiving surface is 0.0 mm.",
   "caption": "The shaft reaches its cradle. Maximum drop below the receiving surface is 0.0 mm."
  },
  "criterion": "Shaft bottom drops more than 185 mm below the receiving cradle.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "detailByBranch": {
   "safe": 3.694,
   "unsafe": 3.694
  },
  "eventFrameTime": 3.44,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_06_shaft",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/4de3efe3f924ac02ed3158dd1d91194d97fd2f4e/media/antigravity/legacy_06_shaft",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_06_shaft/production.json",
  "materialSource": "../antigravity/legacy_06_shaft/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.414
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Shaft bottom drops more than 185 mm below the receiving cradle."
 },
 {
  "id": "07_electronics",
  "short": "Test drawer",
  "title": "Electronics test station",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Electronics assembly",
  "duration": 19.04,
  "event": 3.83,
  "base": "../antigravity/legacy_07_electronics",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 4.44,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Plug contact",
    "86.6 N"
   ],
   [
    "Safe · Plug contact",
    "0 N"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Plug contact (N)"
   ],
   [
    "force.png",
    "Drawer lip and plug contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 1.38 mm. Additional overlap in the sampled visual audit: 1.38 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.226,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.706,
     "text": "Close the test drawer."
    },
    {
     "t": 5.376,
     "text": "Retract the service plug."
    },
    {
     "t": 7.3,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.5,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The closing drawer hits the service plug (86.6 N).",
   "caption": "The closing drawer hits the service plug (86.6 N)."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.146,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.936,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.236,
     "text": "Retract the service plug."
    },
    {
     "t": 4.756,
     "text": "Close the test drawer."
    },
    {
     "t": 7.3,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.5,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The plug retracts before the drawer closes.",
   "caption": "The plug retracts before the drawer closes."
  },
  "criterion": "Normal contact load between plug and drawer lip exceeds 1 N.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "detailByBranch": {
   "safe": 4.11,
   "unsafe": 4.11
  },
  "eventFrameTime": 3.84,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_07_electronics",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/4de3efe3f924ac02ed3158dd1d91194d97fd2f4e/media/antigravity/legacy_07_electronics",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_07_electronics/production.json",
  "materialSource": "../antigravity/legacy_07_electronics/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.83
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Normal contact load between plug and drawer lip exceeds 1 N."
 },
 {
  "id": "08_print",
  "short": "Paper transport",
  "title": "Print shop dispatch",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Print production",
  "duration": 19.04,
  "event": 2.104,
  "base": "../antigravity/legacy_08_print",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 1.32,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Paper slip",
    "1.56e+03 mm"
   ],
   [
    "Safe · Paper slip",
    "0.0557 mm"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Paper slip (mm)"
   ],
   [
    "force.png",
    "Paper and carriage friction (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.97 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.248,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.948,
     "text": "Drive the loaded carriage."
    },
    {
     "t": 7.5,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.7,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The stack slides along the carriage. Its center moves 1556.7 mm from the carrier center.",
   "caption": "The stack slides along the carriage. Its center moves 1556.7 mm from the carrier center."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.168,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 3.028,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.478,
     "text": "Drive the loaded carriage."
    },
    {
     "t": 7.5,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.7,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The paper stack stays centered. Maximum travel relative to the carriage is 0.1 mm.",
   "caption": "The paper stack stays centered. Maximum travel relative to the carriage is 0.1 mm."
  },
  "criterion": "Paper pack center moves over 80 mm from carriage center along travel direction.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "detailByBranch": {
   "safe": 2.3840000000000003,
   "unsafe": 2.3840000000000003
  },
  "eventFrameTime": 2.12,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_08_print",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/56f74bde1dfdc2f9aff408d6fa5a5b1bf212f8e2/media/antigravity/legacy_08_print",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_08_print/production.json",
  "materialSource": "../antigravity/legacy_08_print/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    2.104
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Paper pack center moves over 80 mm from carriage center along travel direction."
 },
 {
  "id": "09_library",
  "short": "Library lift",
  "title": "Library book lift",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Library services",
  "duration": 19.04,
  "event": 4.062,
  "base": "../antigravity/legacy_09_library",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 4.36,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Header contact",
    "1.53e+03 N"
   ],
   [
    "Safe · Header contact",
    "0 N"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Header contact (N)"
   ],
   [
    "force.png",
    "Load and hatch header contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ],
   [
    "Native models, source UV maps and placements",
    "native-assets.json"
   ],
   [
    "MuJoCo model for this recording",
    "scene.xml.gz"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.218,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.618,
     "text": "Drive the loaded carriage."
    },
    {
     "t": 5.668,
     "text": "Lower the book lift."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The raised books hit the header (1527.6 N).",
   "caption": "The raised books hit the header (1527.6 N)."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.138,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.916,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.196,
     "text": "Lower the book lift."
    },
    {
     "t": 4.816,
     "text": "Drive the loaded carriage."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The loaded carriage passes through the open hatch.",
   "caption": "The loaded carriage passes through the open hatch."
  },
  "criterion": "Normal contact load between books and header exceeds 1 N.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "eventFrameTime": 4.08,
  "durationByBranch": {
   "safe": 19.04,
   "unsafe": 19.04
  },
  "editionId": "legacy_09_library",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/4f9aa984ab9cedc139a8c681b3cb7e1978ed65b8/media/antigravity/legacy_09_library",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_09_library/production.json",
  "materialSource": "../antigravity/legacy_09_library/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    4.062
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Normal contact load between books and header exceeds 1 N.",
  "detailByBranch": {
   "safe": 4.3420000000000005,
   "unsafe": 4.3420000000000005
  }
 },
 {
  "id": "10_packing",
  "short": "Tote handoff",
  "title": "Packing line handoff",
  "description": "A Franka arm operates two physical keys beside the machine. Key travel selects the preparation sequence and starts the equipment. The machine and its load then move under MuJoCo dynamics.",
  "category": "Packing and dispatch",
  "duration": 19.04,
  "event": 2.694,
  "base": "../antigravity/legacy_10_packing",
  "planIntro": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "detailTime": 1.76,
  "detailIntro": "The same simulation instant in each branch, with the evidence camera centered on the affected part.",
  "facts": [
   [
    "Unsafe · Box drop",
    "389 mm"
   ],
   [
    "Safe · Box drop",
    "4.25 mm"
   ]
  ],
  "method": "Machine timing starts from measured key displacement. The original machine program drives the mechanism after the robot starts it. Both keys have spring return.",
  "charts": [
   [
    "metric.png",
    "Box drop (mm)"
   ],
   [
    "force.png",
    "Box and catch pan contact (N)"
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.77 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Measured safe trace",
    "safe.csv.gz"
   ],
   [
    "Measured unsafe trace",
    "unsafe.csv.gz"
   ],
   [
    "Simulation and outcome checks",
    "physics-audit.json"
   ],
   [
    "Materials used",
    "appearance.json"
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 0.62,
     "text": "Approach the cycle key directly while the preparation key remains open."
    },
    {
     "t": 1.216,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 1.666,
     "text": "Bring the receiving tote to the handoff."
    },
    {
     "t": 2.286,
     "text": "Release the payload at the programmed handoff."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The box misses the handoff and falls 388.9 mm below the tote floor.",
   "caption": "The box misses the handoff and falls 388.9 mm below the tote floor."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Move the stylus from park toward the control station."
    },
    {
     "t": 1.136,
     "text": "The preparation key reaches its sustained stroke. Arm the guarded equipment program."
    },
    {
     "t": 2.936,
     "text": "The cycle key reaches its sustained stroke. Start the machine sequence."
    },
    {
     "t": 3.386,
     "text": "Bring the receiving tote to the handoff."
    },
    {
     "t": 7.076,
     "text": "Release the payload at the programmed handoff."
    },
    {
     "t": 7.4,
     "text": "Return the unloaded stylus to the verification area."
    },
    {
     "t": 8.6,
     "text": "Finish the wrist check and settle at park."
    }
   ],
   "summary": "The box is delivered to the tote. Maximum drop below its floor is 4.2 mm.",
   "caption": "The box is delivered to the tote. Maximum drop below its floor is 4.2 mm."
  },
  "criterion": "Box underside falls more than 180 mm below the tote interior floor.",
  "robot": "Franka Panda with Panda Hand and control stylus",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
  "eventFrameTime": 2.72,
  "durationByBranch": {
   "unsafe": 19.04,
   "safe": 19.04
  },
  "editionId": "legacy_10_packing",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/b92f8ace538244684bb4af6fafc746566e2328be/media/antigravity/legacy_10_packing",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "../antigravity/legacy_10_packing/production.json",
  "materialSource": "../antigravity/legacy_10_packing/appearance.json",
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    2.694
   ],
   [
    "Settled state",
    18.88
   ]
  ],
  "goalTest": "Box underside falls more than 180 mm below the tote interior floor."
 }
];
