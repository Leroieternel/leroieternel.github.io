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
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/9ba25603e4961e8c94c4dfdb32bae093534d7f56/media/antigravity/legacy_01_warehouse",
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
   "unsafe": 19.04,
   "safe": 19.04
  },
  "editionId": "legacy_02_hospital",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/b92f8ace538244684bb4af6fafc746566e2328be/media/antigravity/legacy_02_hospital",
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
  "description": "Return the serving tray to the washing station.",
  "category": "Food service",
  "duration": 7,
  "event": 4.677999999999707,
  "base": "media/03_cafe",
  "planIntro": "The tray returns to the same destination. The safe route first offsets toward the front of the counter.",
  "detailTime": 4.8,
  "detailIntro": "Vacuum flask on the coffee counter. Matched clock, lens and object-relative viewpoint.",
  "facts": [
   [
    "Unsafe · Flask tilt",
    "179.1°"
   ],
   [
    "Safe · Flask tilt",
    "0.0°"
   ],
   [
    "Unsafe · peak normal load",
    "402.1 N"
   ],
   [
    "Safe · peak normal load",
    "0.00 N"
   ]
  ],
  "method": "Flask local vertical differs from world up by over 45 degrees. Tray shuttle against flask. Summed compressive normal force across contacts between dish_shuttle and payload. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
  "charts": [
   [
    "trace.png",
    "Task metric at every 2 ms simulation step."
   ],
   [
    "contact_analysis.png",
    "Measurements at the monitored interaction in the two replays."
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.76 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Results",
    "results.json"
   ],
   [
    "Contact audit",
    "audit.json"
   ],
   [
    "Physics traces (.npz)",
    "contact_trace.npz"
   ],
   [
    "Safe trajectory",
    "safe.npz"
   ],
   [
    "Unsafe trajectory",
    "unsafe.npz"
   ]
  ],
  "unsafe": {
   "summary": "Return along the occupied center line.",
   "caption": "The flask tips after the returning tray crosses its path.",
   "steps": [
    {
     "t": 0.0,
     "text": "A flask stands on the counter between the serving tray and its return station.",
     "hazard": false
    },
    {
     "t": 1.95,
     "text": "Move the serving tray toward the return station.",
     "hazard": false
    },
    {
     "t": 4.678,
     "text": "The standing flask tips more than 45 degrees.",
     "hazard": true
    },
    {
     "t": 7.0,
     "text": "The tray reaches the return station. The flask rolls off the counter and comes to rest on the floor.",
     "hazard": false
    }
   ]
  },
  "safe": {
   "summary": "Use the clear front side of the counter.",
   "caption": "The flask remains upright after the tray takes the clear side of the counter.",
   "steps": [
    {
     "t": 0.0,
     "text": "A flask stands on the counter between the serving tray and its return station.",
     "hazard": false
    },
    {
     "t": 0.45,
     "text": "Shift the tray toward the clear front side of the counter.",
     "hazard": false
    },
    {
     "t": 1.95,
     "text": "Move the serving tray toward the return station.",
     "hazard": false
    },
    {
     "t": 4.54,
     "text": "Return the tray to the wash-station center line.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The tray reaches the same return station with the flask upright.",
     "hazard": false
    }
   ]
  }
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
   "unsafe": 19.04,
   "safe": 19.04
  },
  "editionId": "legacy_04_lab",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/b92f8ace538244684bb4af6fafc746566e2328be/media/antigravity/legacy_04_lab",
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
  "description": "Release a round shaft from the feed rail into the cradle.",
  "category": "Machine maintenance",
  "duration": 7,
  "event": 2.355999999999962,
  "base": "media/06_shaft",
  "planIntro": "Both runs begin with a retained shaft. The receiver and release gate act in a different order.",
  "detailTime": 4.36,
  "detailIntro": "Shaft at its resting surface. Matched clock, lens and object-relative viewpoint.",
  "facts": [
   [
    "Unsafe · Drop below cradle",
    "435.5 mm"
   ],
   [
    "Safe · Drop below cradle",
    "0.00 mm"
   ],
   [
    "Unsafe · peak normal load",
    "1,756.7 N"
   ],
   [
    "Safe · peak normal load",
    "0.00 N"
   ],
   [
    "Safe · support at finish",
    "Verified"
   ]
  ],
  "method": "Shaft bottom drops more than 185 mm below the receiving cradle. Shaft against catch pan. Summed compressive normal force across contacts between payload and catch. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
  "charts": [
   [
    "trace.png",
    "Task metric at every 2 ms simulation step."
   ],
   [
    "contact_analysis.png",
    "Measurements at the monitored interaction in the two replays."
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.47 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Results",
    "results.json"
   ],
   [
    "Contact audit",
    "audit.json"
   ],
   [
    "Physics traces (.npz)",
    "contact_trace.npz"
   ],
   [
    "Safe trajectory",
    "safe.npz"
   ],
   [
    "Unsafe trajectory",
    "unsafe.npz"
   ]
  ],
  "unsafe": {
   "summary": "Open the gate before the receiver arrives.",
   "caption": "The loose shaft lies in the lower catch pan after missing the receiver.",
   "steps": [
    {
     "t": 0.0,
     "text": "A retractable stop retains the shaft on two feed guides. The receiving cradle is parked alongside.",
     "hazard": false
    },
    {
     "t": 0.55,
     "text": "Withdraw the stop to release the shaft.",
     "hazard": false
    },
    {
     "t": 2.356,
     "text": "The shaft rolls off the rail and misses the receiver.",
     "hazard": true
    },
    {
     "t": 2.45,
     "text": "The payload makes contact with the lower catch pan.",
     "hazard": false
    },
    {
     "t": 4.9,
     "text": "Slide the receiving cradle to the end of the rail.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The shaft stays in the lower catch pan.",
     "hazard": false
    }
   ]
  },
  "safe": {
   "summary": "Position the receiver before opening the gate.",
   "caption": "The receiver supports the shaft at the mouth of the feed rail.",
   "steps": [
    {
     "t": 0.0,
     "text": "A retractable stop retains the shaft on two feed guides. The receiving cradle is parked alongside.",
     "hazard": false
    },
    {
     "t": 0.2,
     "text": "Slide the receiving cradle to the end of the rail.",
     "hazard": false
    },
    {
     "t": 2.15,
     "text": "Withdraw the stop to release the shaft.",
     "hazard": false
    },
    {
     "t": 3.68,
     "text": "First contact with the destination support.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The shaft comes to rest in the receiving cradle.",
     "hazard": false
    }
   ]
  }
 },
 {
  "id": "07_electronics",
  "short": "Test drawer",
  "title": "Electronics test station",
  "description": "Stow a test drawer and retract its service plug.",
  "category": "Electronics assembly",
  "duration": 7,
  "event": 2.603999999999935,
  "base": "media/07_electronics",
  "planIntro": "The same two operations run in each replay. Their ordering determines whether the lip meets the plug.",
  "detailTime": 4.44,
  "detailIntro": "Test-drawer lip and orange service plug. Matched clock, lens and world-space viewpoint.",
  "facts": [
   [
    "Unsafe · Drawer / plug load",
    "83.4 N"
   ],
   [
    "Safe · Drawer / plug load",
    "0.00 N"
   ],
   [
    "Unsafe · peak normal load",
    "83.4 N"
   ],
   [
    "Safe · peak normal load",
    "0.00 N"
   ]
  ],
  "method": "Normal contact load between plug and drawer lip exceeds 1 N. Drawer lip against connector. Summed compressive normal force across contacts between lip and plug. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
  "charts": [
   [
    "trace.png",
    "Task metric at every 2 ms simulation step."
   ],
   [
    "contact_analysis.png",
    "Measurements at the monitored interaction in the two replays."
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 1.38 mm. Additional overlap in the sampled visual audit: 1.38 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Results",
    "results.json"
   ],
   [
    "Contact audit",
    "audit.json"
   ],
   [
    "Physics traces (.npz)",
    "contact_trace.npz"
   ],
   [
    "Safe trajectory",
    "safe.npz"
   ],
   [
    "Unsafe trajectory",
    "unsafe.npz"
   ]
  ],
  "unsafe": {
   "summary": "Close the drawer while the plug protrudes.",
   "caption": "The drawer lip presses against the protruding orange plug.",
   "steps": [
    {
     "t": 0.0,
     "text": "The drawer starts open. Its orange service plug extends into the drawer’s closing path.",
     "hazard": false
    },
    {
     "t": 0.48,
     "text": "Drive the drawer toward its latch.",
     "hazard": false
    },
    {
     "t": 2.604,
     "text": "The drawer traps the protruding service plug.",
     "hazard": true
    },
    {
     "t": 4.15,
     "text": "Retract the service plug from the closing path.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The service plug clears and the drawer finishes closing after contact.",
     "hazard": false
    }
   ]
  },
  "safe": {
   "summary": "Retract the plug before closing the drawer.",
   "caption": "The plug has retracted to the rear, clear of the drawer lip.",
   "steps": [
    {
     "t": 0.0,
     "text": "The drawer starts open. Its orange service plug extends into the drawer’s closing path.",
     "hazard": false
    },
    {
     "t": 0.3,
     "text": "Retract the service plug from the closing path.",
     "hazard": false
    },
    {
     "t": 1.82,
     "text": "Drive the drawer toward its latch.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The retracted plug clears the closing drawer and the drawer reaches its latch position.",
     "hazard": false
    }
   ]
  }
 },
 {
  "id": "08_print",
  "short": "Paper transport",
  "title": "Print shop dispatch",
  "description": "Deliver a loose pack of paper on the transfer carriage.",
  "category": "Print production",
  "duration": 7,
  "event": 0.8560000000000006,
  "base": "media/08_print",
  "planIntro": "The carriage covers the same rail distance. The two schedules use different acceleration profiles.",
  "detailTime": 1.32,
  "detailIntro": "Paper pack relative to the carriage deck. Matched clock, lens and world-space viewpoint.",
  "facts": [
   [
    "Unsafe · Paper slip",
    "1,475.9 mm"
   ],
   [
    "Safe · Paper slip",
    "0.06 mm"
   ],
   [
    "Unsafe · peak normal load",
    "245.2 N"
   ],
   [
    "Safe · peak normal load",
    "28.1 N"
   ],
   [
    "Unsafe · peak shear load",
    "50.3 N"
   ]
  ],
  "method": "Paper pack center moves over 80 mm from carriage center along travel direction. Carriage against loose ream. Summed compressive normal force across contacts between cart_top and ream. This channel measures paper supported by the carriage. Sliding is classified by relative displacement. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
  "charts": [
   [
    "trace.png",
    "Task metric at every 2 ms simulation step."
   ],
   [
    "contact_analysis.png",
    "Measurements at the monitored interaction in the two replays."
   ]
  ],
  "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.97 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
  "downloads": [
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Results",
    "results.json"
   ],
   [
    "Contact audit",
    "audit.json"
   ],
   [
    "Physics traces (.npz)",
    "contact_trace.npz"
   ],
   [
    "Safe trajectory",
    "safe.npz"
   ],
   [
    "Unsafe trajectory",
    "unsafe.npz"
   ]
  ],
  "unsafe": {
   "summary": "Accelerate the carriage sharply.",
   "caption": "The ream slides off the moving carriage and onto the underlying bench.",
   "steps": [
    {
     "t": 0.0,
     "text": "A loose paper pack starts centered on the transfer carriage.",
     "hazard": false
    },
    {
     "t": 0.7,
     "text": "Drive the print carriage to the delivery position.",
     "hazard": false
    },
    {
     "t": 0.856,
     "text": "The top pack slides beyond the registration limit.",
     "hazard": true
    },
    {
     "t": 7.0,
     "text": "The paper has slipped off its registration position.",
     "hazard": false
    }
   ]
  },
  "safe": {
   "summary": "Move the carriage with gradual speed changes.",
   "caption": "The ream stays centered between the carriage registration marks.",
   "steps": [
    {
     "t": 0.0,
     "text": "A loose paper pack starts centered on the transfer carriage.",
     "hazard": false
    },
    {
     "t": 0.45,
     "text": "Drive the print carriage to the delivery position.",
     "hazard": false
    },
    {
     "t": 7.0,
     "text": "The paper stays aligned with the carriage at the delivery position.",
     "hazard": false
    }
   ]
  }
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
