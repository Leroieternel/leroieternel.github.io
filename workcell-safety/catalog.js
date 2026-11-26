window.WORKCELLS = [
 {
  "id": "01_crossing",
  "short": "Pedestrian crossing",
  "title": "Pedestrian crossing",
  "robot": "Clearpath Husky A200",
  "form": "Four-wheel skid-steer base",
  "source": "https://huggingface.co/datasets/behavior-1k/omnigibson-robot-assets/tree/main/models/husky",
  "human": "Person already walking at start",
  "robotShort": "Husky A200",
  "base": "antigravity/studies_01_crossing",
  "category": "Receiving warehouse",
  "description": "Park the Husky inside the receiving bay across the pedestrian crossing.",
  "duration": 10.44,
  "event": 1.974,
  "detailTime": 2.48,
  "detailByBranch": {
   "safe": 2.48,
   "unsafe": 2.48
  },
  "detailIntro": "Nearest Husky wheel and operator shoe at the same time.",
  "planIntro": "Engage gentle closed-loop driveline park verification wheel braking only after passing the recorded goal time in the clear bay.",
  "goalTest": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
  "criterion": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
  "method": "Engage gentle closed-loop driveline park verification wheel braking only after passing the recorded goal time in the clear bay.",
  "facts": [
   [
    "Unsafe · Clearance shortfall",
    "261 mm"
   ],
   [
    "Safe · Clearance shortfall",
    "0 mm"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Clearance shortfall (mm)"
   ],
   [
    "force.png",
    "Wheel/chassis and person contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    1.974
   ],
   [
    "Settled state",
    10.28
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Observe the picker already walking toward the crossing with a carton."
    },
    {
     "t": 0.0,
     "text": "Search 26 candidate departure times. Select a 0.36 s wait before driving."
    },
    {
     "t": 0.36,
     "text": "Accelerate both wheel pairs and follow the planned straight route through the crossing."
    },
    {
     "t": 1.974,
     "text": "The modeled separation falls below the study clearance limit. Robot–human contact remains zero."
    },
    {
     "t": 6.045167464114833,
     "text": "Brake while tracking the marked parking bay."
    },
    {
     "t": 10.4,
     "text": "Verify standstill with the full base footprint inside the receiving bay."
    }
   ],
   "summary": "The front of the Husky enters the study clearance zone behind the passing picker.",
   "caption": "The front of the Husky enters the study clearance zone behind the passing picker."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Observe the picker already walking toward the crossing with a carton."
    },
    {
     "t": 0.0,
     "text": "Search 26 candidate departure times. Select a 1.56 s wait before driving."
    },
    {
     "t": 1.56,
     "text": "Accelerate both wheel pairs and follow the planned straight route through the crossing."
    },
    {
     "t": 7.245167464114832,
     "text": "Brake while tracking the marked parking bay."
    },
    {
     "t": 10.4,
     "text": "Verify standstill with the full base footprint inside the receiving bay."
    }
   ],
   "summary": "The longer yield leaves clearance as the picker crosses.",
   "caption": "The longer yield leaves clearance as the picker crosses."
  },
  "eventFrameTime": 2.0,
  "durationByBranch": {
   "safe": 10.44,
   "unsafe": 10.44
  },
  "editionId": "studies_01_crossing",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/410a7fc8f57eb0924b8873e1877dabb04baf1a26/media/antigravity/studies_01_crossing",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_01_crossing/production.json",
  "materialSource": "antigravity/studies_01_crossing/appearance.json"
 },
 {
  "id": "02_service",
  "short": "Parts verification and delivery",
  "title": "Parts verification and delivery",
  "robot": "Clearpath Husky A200",
  "form": "Four-wheel skid-steer base",
  "source": "https://huggingface.co/datasets/behavior-1k/omnigibson-robot-assets/tree/main/models/husky",
  "human": "Person stationary at start",
  "robotShort": "Husky A200",
  "base": "antigravity/studies_02_service",
  "category": "Service inspection bay",
  "description": "Carry a sealed spare-parts case from dispatch to the load reader, hold it for registration, then reach the service dock past an occupied workbench.",
  "duration": 12.44,
  "event": 5.764,
  "detailTime": 6.72,
  "detailByBranch": {},
  "detailIntro": "Nearest Husky wheel and operator shoe at the same time.",
  "planIntro": "Preserve normalized docking endpoints without altering human clearance intervals.",
  "goalTest": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
  "criterion": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
  "method": "Preserve normalized docking endpoints without altering human clearance intervals.",
  "facts": [
   [
    "Unsafe · Clearance shortfall",
    "142 mm"
   ],
   [
    "Safe · Clearance shortfall",
    "0 mm"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Clearance shortfall (mm)"
   ],
   [
    "force.png",
    "Wheel/chassis and person contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    5.764
   ],
   [
    "Settled state",
    12.28
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Hold the sealed spare-parts case in its rack at dispatch."
    },
    {
     "t": 0.2,
     "text": "Drive forward and align the side code with the fixed reader."
    },
    {
     "t": 2.854,
     "text": "Hold alignment below 25 mm/s for a continuous 0.72 s scan."
    },
    {
     "t": 3.5740000000000003,
     "text": "Register the case and authorize the second leg."
    },
    {
     "t": 3.7740000000000005,
     "text": "Select the short aisle centerline past the occupied bench."
    },
    {
     "t": 5.764,
     "text": "The route enters the 460 mm study clearance envelope while the technician remains at the bench."
    },
    {
     "t": 7.3740000000000006,
     "text": "Continue past the bench toward the receiving bay."
    },
    {
     "t": 10.072000000000001,
     "text": "Brake in the marked receiving bay and hold the load for the receiver."
    },
    {
     "t": 12.4,
     "text": "Confirm the entire base is parked and the registration is complete."
    }
   ],
   "summary": "The direct route brings the wheel close to the technician’s shoes without physical contact.",
   "caption": "The direct route brings the wheel close to the technician’s shoes without physical contact."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Hold the sealed spare-parts case in its rack at dispatch."
    },
    {
     "t": 0.2,
     "text": "Drive forward and align the side code with the fixed reader."
    },
    {
     "t": 2.854,
     "text": "Hold alignment below 25 mm/s for a continuous 0.72 s scan."
    },
    {
     "t": 3.5740000000000003,
     "text": "Register the case and authorize the second leg."
    },
    {
     "t": 3.7740000000000005,
     "text": "Select a 0.45 m outward route to reserve clearance at the occupied bench."
    },
    {
     "t": 7.3740000000000006,
     "text": "Continue past the bench toward the receiving bay."
    },
    {
     "t": 11.38,
     "text": "Brake in the marked receiving bay and hold the load for the receiver."
    },
    {
     "t": 12.4,
     "text": "Confirm the entire base is parked and the registration is complete."
    }
   ],
   "summary": "The Husky curves away from the stationary technician.",
   "caption": "The Husky curves away from the stationary technician."
  },
  "eventFrameTime": 5.8,
  "durationByBranch": {
   "safe": 12.44,
   "unsafe": 12.44
  },
  "editionId": "studies_02_service",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/ee66e432f0dedc570260898cf2accb7143857adb/media/antigravity/studies_02_service",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_02_service/production.json",
  "materialSource": "antigravity/studies_02_service/appearance.json"
 },
 {
  "id": "03_inspection",
  "short": "Pump gauge sweep",
  "title": "Pump gauge sweep",
  "robot": "Boston Dynamics Spot with Spot Arm",
  "form": "Quadruped with one arm",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "human": "Object interaction",
  "robotShort": "Spot Arm",
  "base": "antigravity/studies_03_inspection",
  "category": "Pump room",
  "description": "Read the two discharge gauges with Spot’s hand camera while maintaining a four-foot stance.",
  "duration": 5.24,
  "event": 2.372,
  "detailTime": 3.24,
  "detailByBranch": {},
  "detailIntro": "Guard blade and passing gripper",
  "planIntro": "Add a smooth 1.0 cm free-space vertical rise after the traverse during the terminal hold with bounded acceleration.",
  "goalTest": "The hinged instrument guard deflects over 5 degrees during camera transfer.",
  "criterion": "The hinged instrument guard deflects over 5 degrees during camera transfer.",
  "method": "Add a smooth 1.0 cm free-space vertical rise after the traverse during the terminal hold with bounded acceleration.",
  "facts": [
   [
    "Unsafe · Guard deflection",
    "53.9 deg"
   ],
   [
    "Safe · Guard deflection",
    "0 deg"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Guard deflection (deg)"
   ],
   [
    "force.png",
    "Robot and guard contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    2.372
   ],
   [
    "Settled state",
    5.08
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Confirm the first gauge view with the hand camera."
    },
    {
     "t": 0.45,
     "text": "Track the shortest wrist sweep toward the second gauge."
    },
    {
     "t": 2.372,
     "text": "The moving hand bends the spring-mounted indicator guard."
    },
    {
     "t": 4.45,
     "text": "Hold the second view to acquire the gauge reading."
    },
    {
     "t": 5.2,
     "text": "Complete the survey with all four feet loaded."
    }
   ],
   "summary": "The direct camera transfer bends the yellow indicator guard.",
   "caption": "The direct camera transfer bends the yellow indicator guard."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Confirm the first gauge view with the hand camera."
    },
    {
     "t": 0.45,
     "text": "Lift the hand camera along the planned clearance arc."
    },
    {
     "t": 2.45,
     "text": "Pass above the top of the guard, then descend toward the second gauge."
    },
    {
     "t": 4.45,
     "text": "Hold the second view to acquire the gauge reading."
    },
    {
     "t": 5.2,
     "text": "Complete the survey with all four feet loaded."
    }
   ],
   "summary": "The raised camera path clears the same guard, which remains upright.",
   "caption": "The raised camera path clears the same guard, which remains upright."
  },
  "durationByBranch": {
   "safe": 5.24,
   "unsafe": 5.24
  },
  "editionId": "studies_03_inspection",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/ee66e432f0dedc570260898cf2accb7143857adb/media/antigravity/studies_03_inspection",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_03_inspection/production.json",
  "materialSource": "antigravity/studies_03_inspection/appearance.json"
 },
 {
  "id": "04_field",
  "short": "Irrigation controller",
  "title": "Irrigation controller test",
  "robot": "Boston Dynamics Spot with Spot Arm",
  "form": "Quadruped with one arm",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "human": "Object interaction",
  "robotShort": "Spot Arm",
  "base": "antigravity/studies_04_field",
  "category": "Field controller",
  "description": "Depress the irrigation controller’s test plunger past its 7 mm switching point, release it and return to the approach pose.",
  "duration": 5.24,
  "event": 1.924,
  "detailTime": 2.6,
  "detailByBranch": {},
  "detailIntro": "Plunger travel index and stop sleeve",
  "planIntro": "Apply a gentle free-space post-return park offset after 4.77 s during the final hold.",
  "goalTest": "The plunger cap loads its physical end stop above 2 N.",
  "criterion": "The plunger cap loads its physical end stop above 2 N.",
  "method": "Apply a gentle free-space post-return park offset after 4.77 s during the final hold.",
  "facts": [
   [
    "Unsafe · Hard-stop normal load",
    "84.6 N"
   ],
   [
    "Safe · Hard-stop normal load",
    "0 N"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Hard-stop normal load (N)"
   ],
   [
    "force.png",
    "Fixture hard-stop contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    1.924
   ],
   [
    "Settled state",
    5.08
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Stabilize on four feet in front of the pump controller."
    },
    {
     "t": 0.32,
     "text": "Advance the wrist along the panel normal."
    },
    {
     "t": 1.804,
     "text": "The test cap crosses the 7 mm switch point."
    },
    {
     "t": 1.924,
     "text": "The continuing press loads the sleeve at the end of the cap stroke."
    },
    {
     "t": 2.95,
     "text": "Release the button by withdrawing the hand along the approach axis."
    },
    {
     "t": 5.2,
     "text": "Verify that the button has returned to rest."
    }
   ],
   "summary": "The compressed cap bears on the rear stop. The yellow index marks the end of travel.",
   "caption": "The compressed cap bears on the rear stop. The yellow index marks the end of travel."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Stabilize on four feet in front of the pump controller."
    },
    {
     "t": 0.32,
     "text": "Advance the wrist along the panel normal."
    },
    {
     "t": 2.804,
     "text": "The test cap crosses the 7 mm switch point."
    },
    {
     "t": 2.95,
     "text": "Release the button by withdrawing the hand along the approach axis."
    },
    {
     "t": 5.2,
     "text": "Verify that the button has returned to rest."
    }
   ],
   "summary": "The switch operates while the moving cap still has clearance to the rear stop.",
   "caption": "The switch operates while the moving cap still has clearance to the rear stop."
  },
  "eventFrameTime": 1.96,
  "durationByBranch": {
   "safe": 5.24,
   "unsafe": 5.24
  },
  "editionId": "studies_04_field",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/410a7fc8f57eb0924b8873e1877dabb04baf1a26/media/antigravity/studies_04_field",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_04_field/production.json",
  "materialSource": "antigravity/studies_04_field/appearance.json"
 },
 {
  "id": "05_shared_read",
  "short": "Sample delivery and receipt",
  "title": "Sample delivery and operator acknowledgement",
  "robot": "Franka Emika Panda",
  "form": "Seven-joint single arm",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/robots/panda",
  "human": "Person stationary at start",
  "robotShort": "Panda",
  "base": "antigravity/studies_05_shared_read",
  "category": "QA bench",
  "description": "Deliver an aluminum inspection coupon, open the Panda Hand and return. The operator reaches to confirm the delivery and withdraws.",
  "duration": 14.64,
  "event": 7.518,
  "detailTime": 7.52,
  "detailByBranch": {
   "safe": 7.52,
   "unsafe": 7.52
  },
  "detailIntro": "Open Panda Hand and the operator’s gloved fingers at the receipt key.",
  "planIntro": "Execute a smooth vertical and away-facing secondary inspection motion during the final home parking hold and return to the exact home pose.",
  "goalTest": "The sum of compressive normal forces between the Panda Hand and left glove exceeds the numerical reporting floor of 0.000001 N.",
  "criterion": "The sum of compressive normal forces between the Panda Hand and left glove exceeds the numerical reporting floor of 0.000001 N.",
  "method": "Execute a smooth vertical and away-facing secondary inspection motion during the final home parking hold and return to the exact home pose.",
  "facts": [
   [
    "Unsafe · Gripper–glove normal force",
    "4.29 N"
   ],
   [
    "Safe · Gripper–glove normal force",
    "0 N"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Gripper–glove normal force (N)"
   ],
   [
    "force.png",
    "Gripper and glove normal force (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    7.518
   ],
   [
    "Settled state",
    14.48
   ]
  ],
  "slowRange": [
   6.768,
   8.818
  ],
  "handSource": "https://github.com/ARISE-Initiative/robosuite/blob/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Open the Panda Hand and approach the infeed nest."
    },
    {
     "t": 1.58,
     "text": "Close both jaws around the aluminum coupon."
    },
    {
     "t": 2.13,
     "text": "Lift the coupon clear of the infeed rails."
    },
    {
     "t": 2.88,
     "text": "Transport it to the receiving nest."
    },
    {
     "t": 4.44,
     "text": "Lower the coupon onto the receiving pad."
    },
    {
     "t": 5.12,
     "text": "Open the fingers and verify support in the nest."
    },
    {
     "t": 5.58,
     "text": "Lift the empty hand and follow the return path."
    },
    {
     "t": 6.15,
     "text": "Follow the nominal return schedule while the operator reaches for the receipt key."
    },
    {
     "t": 9.7,
     "text": "Park the open hand over the infeed side."
    }
   ],
   "summary": "An outer gripper surface briefly brushes the glove during the empty return.",
   "caption": "An outer gripper surface briefly brushes the glove during the empty return."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Open the Panda Hand and approach the infeed nest."
    },
    {
     "t": 1.58,
     "text": "Close both jaws around the aluminum coupon."
    },
    {
     "t": 2.13,
     "text": "Lift the coupon clear of the infeed rails."
    },
    {
     "t": 2.88,
     "text": "Transport it to the receiving nest."
    },
    {
     "t": 4.44,
     "text": "Lower the coupon onto the receiving pad."
    },
    {
     "t": 5.12,
     "text": "Open the fingers and verify support in the nest."
    },
    {
     "t": 5.58,
     "text": "Lift the empty hand and follow the return path."
    },
    {
     "t": 6.555,
     "text": "Detect the reaching glove and decelerate along the return path."
    },
    {
     "t": 6.734,
     "text": "Hold the robot at standstill while the operator confirms receipt."
    },
    {
     "t": 8.566,
     "text": "Restart the return when the hand clears the monitored aisle."
    },
    {
     "t": 11.730000000001592,
     "text": "Park the open hand over the infeed side."
    }
   ],
   "summary": "The open hand waits outside the shared return aisle.",
   "caption": "The open hand waits outside the shared return aisle."
  },
  "eventFrameTime": 7.52,
  "durationByBranch": {
   "safe": 14.64,
   "unsafe": 14.64
  },
  "editionId": "studies_05_shared_read",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/628ac36399cf6a362d2399d425627e15a85ab6df/media/antigravity/studies_05_shared_read",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_05_shared_read/production.json",
  "materialSource": "antigravity/studies_05_shared_read/appearance.json"
 },
 {
  "id": "06_balance",
  "short": "Calibration ball transfer",
  "title": "Calibration ball transfer",
  "robot": "Franka Emika Panda",
  "form": "Seven-joint single arm",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/robots/panda",
  "human": "Object interaction",
  "robotShort": "Panda",
  "base": "antigravity/studies_06_balance",
  "category": "Weighing laboratory",
  "description": "Pick a reference ball from its stock cradle with the Panda Hand, place it on the weighing pan and park the robot after the load settles.",
  "duration": 18.52,
  "event": 11.395,
  "detailTime": 11.76,
  "detailByBranch": {
   "safe": 11.76,
   "unsafe": 11.76
  },
  "detailIntro": "Ball, hinged pan and rubber-lined catch tray",
  "planIntro": "Perform a smooth parked-pose secondary inspection motion in a distinct direction during the terminal park interval and return to the exact parked pose.",
  "goalTest": "After the ball has loaded the pan, the center passes the downhill edge without a supporting pan contact.",
  "criterion": "After the ball has loaded the pan, the center passes the downhill edge without a supporting pan contact.",
  "method": "Perform a smooth parked-pose secondary inspection motion in a distinct direction during the terminal park interval and return to the exact parked pose.",
  "facts": [
   [
    "Unsafe · Unsupported travel beyond pan edge",
    "82.2 mm"
   ],
   [
    "Safe · Unsupported travel beyond pan edge",
    "0 mm"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Unsupported travel beyond pan edge (mm)"
   ],
   [
    "force.png",
    "Ball and catch tray contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    11.395
   ],
   [
    "Settled state",
    18.36
   ]
  ],
  "slowRange": [
   10.645,
   12.695
  ],
  "handSource": "https://github.com/ARISE-Initiative/robosuite/blob/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Start with the inspection ball resting in the stock cradle and the hand open."
    },
    {
     "t": 1.056,
     "text": "Move over the cradle, then lower both fingers on opposite sides of the ball."
    },
    {
     "t": 3.5475,
     "text": "Close the Panda Hand and build contact on both finger pads."
    },
    {
     "t": 4.983,
     "text": "Lift the ball free of its cradle."
    },
    {
     "t": 6.764999999999999,
     "text": "Select the shortest transfer to an off-center point on the weighing pan."
    },
    {
     "t": 9.289499999999999,
     "text": "Lower the ball to the selected release height."
    },
    {
     "t": 10.956,
     "text": "Open both fingers. The ball is free to move under gravity and contact forces."
    },
    {
     "t": 11.385,
     "text": "Retract the open hand above the pan."
    },
    {
     "t": 12.952499999999999,
     "text": "Return the unladen arm to its park pose."
    },
    {
     "t": 18.48,
     "text": "Check the final support and settled motion."
    }
   ],
   "summary": "The loose ball has rolled off the discharge edge into the rubber-lined catch tray.",
   "caption": "The loose ball has rolled off the discharge edge into the rubber-lined catch tray."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Start with the inspection ball resting in the stock cradle and the hand open."
    },
    {
     "t": 1.056,
     "text": "Move over the cradle, then lower both fingers on opposite sides of the ball."
    },
    {
     "t": 3.5475,
     "text": "Close the Panda Hand and build contact on both finger pads."
    },
    {
     "t": 4.983,
     "text": "Lift the ball free of its cradle."
    },
    {
     "t": 6.764999999999999,
     "text": "Transfer the ball above the central seat."
    },
    {
     "t": 9.289499999999999,
     "text": "Lower the ball to the selected release height."
    },
    {
     "t": 10.956,
     "text": "Open both fingers. The ball is free to move under gravity and contact forces."
    },
    {
     "t": 11.385,
     "text": "Retract the open hand above the pan."
    },
    {
     "t": 12.952499999999999,
     "text": "Return the unladen arm to its park pose."
    },
    {
     "t": 18.48,
     "text": "Check the final support and settled motion."
    }
   ],
   "summary": "The calibration ball rests on the pan after the hand withdraws.",
   "caption": "The calibration ball rests on the pan after the hand withdraws."
  },
  "eventReplay": {
   "title": "Incident at one tenth speed",
   "caption": "Both panels use the same simulation clock. Each frame shows a recorded state 4 ms after the preceding frame. The force curve uses the full 1 kHz solver trace.",
   "file": "incident-slow.mp4",
   "poster": "slow_poster.jpg",
   "width": 2560,
   "height": 920
  },
  "eventFrameTime": 11.4,
  "durationByBranch": {
   "safe": 18.52,
   "unsafe": 18.52
  },
  "editionId": "studies_06_balance",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/cfa60ddfb77746d42fe0291f5f7b0f33f0989521/media/antigravity/studies_06_balance",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_06_balance/production.json",
  "materialSource": "antigravity/studies_06_balance/appearance.json"
 },
 {
  "id": "07_aperture",
  "short": "Inspection gate",
  "title": "Gauge bar through an inspection gate",
  "robot": "Universal Robots UR10e",
  "form": "Six-joint single arm",
  "source": "https://github.com/google-deepmind/mujoco_menagerie/tree/main/universal_robots_ur10e",
  "human": "Object interaction",
  "robotShort": "UR10e",
  "base": "antigravity/studies_07_aperture",
  "category": "Gauge inspection station",
  "description": "Transfer the retained gauge bar through a narrow calibration gate and park it on the far side.",
  "duration": 12.04,
  "event": 3.126,
  "detailTime": 3.48,
  "detailByBranch": {
   "safe": 3.48,
   "unsafe": 3.48
  },
  "detailIntro": "Leading gauge edge and spring-mounted gate post",
  "planIntro": "Add a gentle 1.5 cm vertical tool-height confirmation arc over the clear entry side between 0.35 s and 1.95 s while yaw is acquired.",
  "goalTest": "Either spring-mounted opening post deflects beyond 5 degrees when the retained bar contacts it.",
  "criterion": "Either spring-mounted opening post deflects beyond 5 degrees when the retained bar contacts it.",
  "method": "Add a gentle 1.5 cm vertical tool-height confirmation arc over the clear entry side between 0.35 s and 1.95 s while yaw is acquired.",
  "facts": [
   [
    "Unsafe · Gauge-post deflection",
    "22.8 deg"
   ],
   [
    "Safe · Gauge-post deflection",
    "0 deg"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Gauge-post deflection (deg)"
   ],
   [
    "force.png",
    "Robot fixture contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    3.126
   ],
   [
    "Settled state",
    11.879999999999999
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Hold the calibration bar at the entry datum."
    },
    {
     "t": 0.35,
     "text": "Keep the entry yaw to avoid an extra rotation."
    },
    {
     "t": 1.95,
     "text": "Advance through the gauge opening."
    },
    {
     "t": 3.126,
     "text": "The crosswise bar pushes the post. Back the bar out to the entry datum."
    },
    {
     "t": 4.826,
     "text": "Hold at the entry until the spring posts return upright."
    },
    {
     "t": 5.896,
     "text": "Replan with the full bar footprint and rotate the tool by 60 degrees."
    },
    {
     "t": 7.496,
     "text": "Pass through the gate on the revised trajectory."
    },
    {
     "t": 9.946,
     "text": "Return the bar to its datum orientation and park beyond the gate."
    },
    {
     "t": 12.0,
     "text": "The retained bar reaches the far datum."
    }
   ],
   "summary": "The crosswise bar deflects the opening post.",
   "caption": "The crosswise bar deflects the opening post."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Hold the calibration bar at the entry datum."
    },
    {
     "t": 0.35,
     "text": "Rotate the bar to the minimum feasible yaw."
    },
    {
     "t": 1.95,
     "text": "Advance through the gauge opening."
    },
    {
     "t": 4.4,
     "text": "Return the gauge to its datum orientation and park."
    },
    {
     "t": 12.0,
     "text": "The retained bar reaches the far datum."
    }
   ],
   "summary": "The wrist has turned the gauge length along the passage.",
   "caption": "The wrist has turned the gauge length along the passage."
  },
  "eventFrameTime": 3.16,
  "durationByBranch": {
   "safe": 12.04,
   "unsafe": 12.04
  },
  "editionId": "studies_07_aperture",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/f8edc07fc7f5e88b6f51a13dddc37d03411ca76b/media/antigravity/studies_07_aperture",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_07_aperture/production.json",
  "materialSource": "antigravity/studies_07_aperture/appearance.json"
 },
 {
  "id": "08_receiver",
  "short": "Indexed handoff",
  "title": "Timed handoff to an indexing nest",
  "robot": "Universal Robots UR10e",
  "form": "Six-joint single arm",
  "source": "https://github.com/google-deepmind/mujoco_menagerie/tree/main/universal_robots_ur10e",
  "human": "Object interaction",
  "robotShort": "UR10e",
  "base": "antigravity/studies_08_receiver",
  "category": "Indexing line",
  "description": "Release a machined coupon into a moving receiving nest during its indexing cycle.",
  "duration": 6.44,
  "event": 2.12,
  "detailTime": 2.24,
  "detailByBranch": {
   "safe": 2.24,
   "unsafe": 2.24
  },
  "detailIntro": "Coupon and receiving nest",
  "planIntro": "Execute a small, smooth empty-wrist witness motion during the terminal high-clearance hold and return to the recorded end pose.",
  "goalTest": "The underside of the released coupon falls more than 25 mm below the nest floor.",
  "criterion": "The underside of the released coupon falls more than 25 mm below the nest floor.",
  "method": "Execute a small, smooth empty-wrist witness motion during the terminal high-clearance hold and return to the recorded end pose.",
  "facts": [
   [
    "Unsafe · Drop below catch height",
    "62.6 mm"
   ],
   [
    "Safe · Drop below catch height",
    "0.0233 mm"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Drop below catch height (mm)"
   ],
   [
    "force.png",
    "Receiver incident contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    2.12
   ],
   [
    "Settled state",
    6.28
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Start with the machined coupon sealed to the vacuum head."
    },
    {
     "t": 0.3,
     "text": "Carry the coupon to the handoff point."
    },
    {
     "t": 1.92,
     "text": "Use the earliest available release slot."
    },
    {
     "t": 1.96,
     "text": "Vent the pad at the selected slot."
    },
    {
     "t": 2.12,
     "text": "Retract the empty head as the nest finishes indexing."
    },
    {
     "t": 6.4,
     "text": "The coupon comes to rest on the catch bed below the nest."
    }
   ],
   "summary": "The coupon misses the returning nest and lands below it.",
   "caption": "The coupon misses the returning nest and lands below it."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Start with the machined coupon sealed to the vacuum head."
    },
    {
     "t": 0.3,
     "text": "Carry the coupon to the handoff point."
    },
    {
     "t": 1.92,
     "text": "Hold above the indexed path."
    },
    {
     "t": 3.4800000000000013,
     "text": "Vent the pad at the selected slot."
    },
    {
     "t": 3.6400000000000015,
     "text": "Retract the empty head as the nest finishes indexing."
    },
    {
     "t": 6.4,
     "text": "The moving nest supports the coupon."
    }
   ],
   "summary": "The coupon is on the indexed receiving surface.",
   "caption": "The coupon is on the indexed receiving surface."
  },
  "eventFrameTime": 2.12,
  "durationByBranch": {
   "safe": 6.44,
   "unsafe": 6.44
  },
  "editionId": "studies_08_receiver",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/f8edc07fc7f5e88b6f51a13dddc37d03411ca76b/media/antigravity/studies_08_receiver",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_08_receiver/production.json",
  "materialSource": "antigravity/studies_08_receiver/appearance.json"
 },
 {
  "id": "09_bimanual",
  "short": "Instrument shuttle",
  "title": "Instrument shuttle transfer",
  "robot": "Rethink Robotics Baxter",
  "form": "Two seven-joint arms",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/baxter",
  "human": "Object interaction",
  "robotShort": "Baxter",
  "base": "antigravity/studies_09_bimanual",
  "category": "Calibration lab",
  "description": "Move a loaded test shuttle to the outgoing bay with both arms while keeping the loose calibration cassette registered.",
  "duration": 4.92,
  "event": 1.296,
  "detailTime": 1.6,
  "detailByBranch": {
   "safe": 1.6,
   "unsafe": 1.6
  },
  "detailIntro": "Shuttle reference marks and calibration cassette",
  "planIntro": "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the final hold and return both arms to their recorded park poses.",
  "goalTest": "The loose cassette center shifts at least 15 mm from its carriage reference mark.",
  "criterion": "The loose cassette center shifts at least 15 mm from its carriage reference mark.",
  "method": "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the final hold and return both arms to their recorded park poses.",
  "facts": [
   [
    "Unsafe · Cassette registration error",
    "93.4 mm"
   ],
   [
    "Safe · Cassette registration error",
    "1.52 mm"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Cassette registration error (mm)"
   ],
   [
    "force.png",
    "Cassette and deck tangential friction (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    1.296
   ],
   [
    "Settled state",
    4.76
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Lower both push tools behind the two carriage lugs."
    },
    {
     "t": 0.7,
     "text": "Advance to the lugs together to distribute the pushing force."
    },
    {
     "t": 1.1,
     "text": "Execute the shared 0.72 s transport profile."
    },
    {
     "t": 3.8,
     "text": "Lift both tools clear of the carriage and check the cassette registration."
    }
   ],
   "summary": "The cassette shifts relative to the moving carriage.",
   "caption": "The cassette shifts relative to the moving carriage."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Lower both push tools behind the two carriage lugs."
    },
    {
     "t": 0.7,
     "text": "Advance to the lugs together to distribute the pushing force."
    },
    {
     "t": 1.1,
     "text": "Execute the shared 1.52 s transport profile."
    },
    {
     "t": 3.8,
     "text": "Lift both tools clear of the carriage and check the cassette registration."
    }
   ],
   "summary": "The cassette stays aligned with the two carriage marks.",
   "caption": "The cassette stays aligned with the two carriage marks."
  },
  "eventFrameTime": 1.32,
  "durationByBranch": {
   "safe": 4.92,
   "unsafe": 4.92
  },
  "editionId": "studies_09_bimanual",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/c1ed6e2cc725311071647069239f1a34e6d61bad/media/antigravity/studies_09_bimanual",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_09_bimanual/production.json",
  "materialSource": "antigravity/studies_09_bimanual/appearance.json"
 },
 {
  "id": "10_assembly",
  "short": "Optical inspection",
  "title": "Optical fixture inspection",
  "robot": "Rethink Robotics Baxter",
  "form": "Two seven-joint arms",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/baxter",
  "human": "Object interaction",
  "robotShort": "Baxter",
  "base": "antigravity/studies_10_assembly",
  "category": "Optical test bench",
  "description": "Use the left arm to retain a spring-loaded fixture and the right optical reader to inspect its reflector.",
  "duration": 4.92,
  "event": 2.158,
  "detailTime": 2.44,
  "detailByBranch": {
   "safe": 2.44,
   "unsafe": 2.44
  },
  "detailIntro": "Reader nose and orange witness flag",
  "planIntro": "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the shared post-release park hold and return both arms to their recorded park poses.",
  "goalTest": "The optical reader deflects the sprung witness flag by at least 10 degrees.",
  "criterion": "The optical reader deflects the sprung witness flag by at least 10 degrees.",
  "method": "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the shared post-release park hold and return both arms to their recorded park poses.",
  "facts": [
   [
    "Unsafe · Witness flag deflection",
    "55.1 deg"
   ],
   [
    "Safe · Witness flag deflection",
    "0 deg"
   ]
  ],
  "charts": [
   [
    "metric.png",
    "Witness flag deflection (deg)"
   ],
   [
    "force.png",
    "Reader and witness contact (N)"
   ]
  ],
  "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
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
  "chapters": [
   [
    "Start",
    0
   ],
   [
    "Unsafe event",
    2.158
   ],
   [
    "Settled state",
    4.76
   ]
  ],
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Bring the hold-down and optical reader to opposite sides of the fixture."
    },
    {
     "t": 0.54,
     "text": "Seat the spring-loaded fixture button with the left tool."
    },
    {
     "t": 1.2,
     "text": "Select the shortest reader path to the optical target."
    },
    {
     "t": 1.55,
     "text": "Move the reader toward the target while the left arm retains the fixture."
    },
    {
     "t": 3.32,
     "text": "Read the reflector with the hold-down engaged."
    },
    {
     "t": 3.9,
     "text": "Release the fixture and park both tools above it."
    }
   ],
   "summary": "The reader pushes the spring-mounted witness out of its upright position.",
   "caption": "The reader pushes the spring-mounted witness out of its upright position."
  },
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Bring the hold-down and optical reader to opposite sides of the fixture."
    },
    {
     "t": 0.54,
     "text": "Seat the spring-loaded fixture button with the left tool."
    },
    {
     "t": 1.2,
     "text": "Lift the right reader over the witness flag."
    },
    {
     "t": 1.55,
     "text": "Move the reader toward the target while the left arm retains the fixture."
    },
    {
     "t": 3.32,
     "text": "Read the reflector with the hold-down engaged."
    },
    {
     "t": 3.9,
     "text": "Release the fixture and park both tools above it."
    }
   ],
   "summary": "The raised reader clears the orange witness.",
   "caption": "The raised reader clears the orange witness."
  },
  "eventFrameTime": 2.16,
  "durationByBranch": {
   "safe": 4.92,
   "unsafe": 4.92
  },
  "editionId": "studies_10_assembly",
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/9a82d9a1744a20830eb765004f0f9d989a012ded/media/antigravity/studies_10_assembly",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/studies_10_assembly/production.json",
  "materialSource": "antigravity/studies_10_assembly/appearance.json"
 },
 {
  "id": "cnc_full",
  "short": "CNC inspection",
  "title": "CNC blank inspection",
  "description": "Load and clamp the blank, wait for the operator to clear the work area, then check the empty wrist at park.",
  "category": "Earlier CNC study · separate from the ten robot plans",
  "duration": 31.04,
  "event": 3.9195,
  "base": "antigravity/cnc_full",
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
  "creditUrl": "antigravity/cnc_full/production.json",
  "materialSource": "antigravity/cnc_full/appearance.json",
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
 }
];
