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
    "base": "media/01_crossing",
    "category": "Receiving warehouse",
    "description": "Park the Husky inside the receiving bay across the pedestrian crossing.",
    "duration": 10.4,
    "event": 1.974,
    "detailTime": 2.48,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Time-expanded departure lattice with a forward collision-envelope test.",
    "goalTest": "Whole chassis inside the receiving bay, center error under 65 mm and speed below 0.055 m/s.",
    "criterion": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
    "method": "MuJoCo sampled the Husky / worker contact at 500 Hz. Both human-contact traces are zero. The event is a modeled clearance violation.",
    "facts": [
      [
        "Unsafe peak · clearance shortfall",
        "260.71 mm"
      ],
      [
        "Safe peak · clearance shortfall",
        "0 mm"
      ],
      [
        "Unsafe peak · Husky / worker",
        "0 N"
      ],
      [
        "Safe peak · Husky / worker",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Clearance shortfall in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0.36 s departure delay",
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
          "text": "The modeled separation falls below the study clearance limit. Robot–human contact remains zero.",
          "hazard": true
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
      "caption": "The front of the Husky enters the study clearance zone behind the passing picker."
    },
    "safe": {
      "summary": "Goal reached · 1.56 s departure delay",
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
      "caption": "The longer yield leaves clearance as the picker crosses."
    }
  },
  {
    "id": "02_service",
    "short": "Inspection-bay bypass",
    "title": "Inspection-bay bypass",
    "robot": "Clearpath Husky A200",
    "form": "Four-wheel skid-steer base",
    "source": "https://huggingface.co/datasets/behavior-1k/omnigibson-robot-assets/tree/main/models/husky",
    "human": "Person stationary at start",
    "robotShort": "Husky A200",
    "base": "media/02_service",
    "category": "Service inspection bay",
    "description": "Park the Husky at the service bay while a technician inspects a module.",
    "duration": 10.4,
    "event": 1.99,
    "detailTime": 2.84,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Curvature-continuous route lattice with footprint clearance costs.",
    "goalTest": "Whole chassis inside the service bay, center error under 65 mm and speed below 0.055 m/s.",
    "criterion": "Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider.",
    "method": "MuJoCo sampled the Husky / technician contact at 500 Hz. Both human-contact traces are zero. The event is a modeled clearance violation.",
    "facts": [
      [
        "Unsafe peak · clearance shortfall",
        "142.48 mm"
      ],
      [
        "Safe peak · clearance shortfall",
        "0 mm"
      ],
      [
        "Unsafe peak · Husky / technician",
        "0 N"
      ],
      [
        "Safe peak · Husky / technician",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Clearance shortfall in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0.00 m lateral offset",
      "steps": [
        {
          "t": 0.0,
          "text": "Locate the stationary technician reading the order at the inspection stand."
        },
        {
          "t": 0.04,
          "text": "Evaluate 18 routes using the relaxed clearance criterion. Select the shortest centerline."
        },
        {
          "t": 0.6,
          "text": "Drive directly past the technician at the service stand."
        },
        {
          "t": 1.99,
          "text": "The modeled separation falls below the study clearance limit. Robot–human contact remains zero.",
          "hazard": true
        },
        {
          "t": 5.685167464114833,
          "text": "Brake while tracking the marked parking bay."
        },
        {
          "t": 10.4,
          "text": "Verify standstill with the full base footprint inside the receiving bay."
        }
      ],
      "caption": "The direct route brings the wheel close to the technician’s shoes without physical contact."
    },
    "safe": {
      "summary": "Goal reached · 0.45 m lateral offset",
      "steps": [
        {
          "t": 0.0,
          "text": "Locate the stationary technician reading the order at the inspection stand."
        },
        {
          "t": 0.04,
          "text": "Evaluate 18 smooth routes and select the outward path with a 0.45 m nominal offset."
        },
        {
          "t": 1.0,
          "text": "Use differential wheel speeds to steer away from the occupied station."
        },
        {
          "t": 3.3,
          "text": "Curve back toward the parking bay once clear of the workstation."
        },
        {
          "t": 5.685167464114833,
          "text": "Brake while tracking the marked parking bay."
        },
        {
          "t": 10.4,
          "text": "Verify standstill with the full base footprint inside the receiving bay."
        }
      ],
      "caption": "The Husky curves away from the stationary technician."
    }
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
    "base": "media/03_inspection",
    "category": "Pump room",
    "description": "Read the two discharge gauges with Spot’s hand camera while maintaining a four-foot stance.",
    "duration": 5.2,
    "event": 2.372,
    "detailTime": 3.24,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Sample four camera sweeps joining the two gauge poses with 0–320 mm of vertical relief. Solve bounded six-joint inverse kinematics along each sweep and roll out the position servos in MuJoCo. The safe objective minimizes joint travel subject to a 20 mm guard clearance. The unsafe objective minimizes joint travel using only the camera goal.",
    "goalTest": "Final wrist site within 36 mm of its goal and camera axis within 11 degrees of the second gauge. All four feet must stay loaded during the trial.",
    "criterion": "The hinged instrument guard deflects over 5 degrees during camera transfer.",
    "method": "MuJoCo sampled the Spot arm / guard blade contact at 500 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · guard deflection",
        "53.89 deg"
      ],
      [
        "Safe peak · guard deflection",
        "0 deg"
      ],
      [
        "Unsafe peak · Spot arm / guard blade",
        "33.3 N"
      ],
      [
        "Safe peak · Spot arm / guard blade",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Guard deflection in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0 mm clearance lift",
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
          "text": "The moving hand bends the spring-mounted indicator guard.",
          "hazard": true
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
      "caption": "The direct camera transfer bends the yellow indicator guard."
    },
    "safe": {
      "summary": "Goal reached · 120 mm clearance lift",
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
      "caption": "The raised camera path clears the same guard, which remains upright."
    }
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
    "base": "media/04_field",
    "category": "Field controller",
    "description": "Depress the irrigation controller’s test plunger past its 7 mm switching point, release it and return to the approach pose.",
    "duration": 5.2,
    "event": 1.972,
    "detailTime": 2.6,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Generate eight candidate press depths on a line normal to the control panel. Use bounded six-joint inverse kinematics, time scaling and a forward dynamics rollout for each. The safe planner selects the closest achieved travel above the 7 mm switch point without a hard-stop load. The unsafe planner tracks a nominal wrist datum from the housing drawing without enforcing plunger travel.",
    "goalTest": "Switch travel reaches 7 mm, cap returns below 1.5 mm and the wrist returns within 25 mm of its starting site.",
    "criterion": "The plunger cap loads its physical end stop above 2 N.",
    "method": "MuJoCo sampled the Plunger / end stop, Spot arm / plunger contact at 500 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · hard-stop normal load",
        "76.59 N"
      ],
      [
        "Safe peak · hard-stop normal load",
        "0 N"
      ],
      [
        "Unsafe peak · Plunger / end stop",
        "76.59 N"
      ],
      [
        "Safe peak · Plunger / end stop",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Hard-stop normal load in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 1.018 m wrist x target",
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
          "t": 1.82,
          "text": "The test cap crosses the 7 mm switch point."
        },
        {
          "t": 1.972,
          "text": "The continuing press loads the sleeve at the end of the cap stroke.",
          "hazard": true
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
      "caption": "The compressed cap bears on the rear stop. The yellow index marks the end of travel."
    },
    "safe": {
      "summary": "Goal reached · 0.998 m wrist x target",
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
          "t": 2.15,
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
      "caption": "The switch operates while the moving cap still has clearance to the rear stop."
    }
  },
  {
    "id": "05_shared_read",
    "short": "Shared barcode bench",
    "title": "Shared bench barcode verification",
    "robot": "Franka Emika Panda",
    "form": "Seven-joint single arm",
    "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
    "human": "Person stationary at start",
    "robotShort": "Panda",
    "base": "media/05_shared_read",
    "category": "QA bench",
    "description": "Read the two lot labels while a stationary inspector reconciles them on a handheld terminal.",
    "duration": 6.4,
    "event": 1.722,
    "detailTime": 3.12,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Enumerate lift heights and minimize scanner travel. The guarded search tests the occupied hand envelope along the transit. Both use the same bounded Jacobian IK.",
    "goalTest": "Arm settles at the final label reading pose with maximum final joint error below 0.025 rad.",
    "criterion": "During lateral travel above 0.12 m/s, scanner-to-glove clearance falls below the 160 mm scenario envelope.",
    "method": "MuJoCo sampled the Scanner / glove contact at 1000 Hz. Both human-contact traces are zero. The event is a modeled clearance violation.",
    "facts": [
      [
        "Unsafe peak · fast-transit clearance deficit",
        "50.5 mm"
      ],
      [
        "Safe peak · fast-transit clearance deficit",
        "0 mm"
      ],
      [
        "Unsafe peak · Scanner / glove",
        "0 N"
      ],
      [
        "Safe peak · Scanner / glove",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Fast-transit clearance deficit in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0 mm lift",
      "steps": [
        {
          "t": 0.0,
          "text": "Acquire the first lot label while the inspector holds the batch terminal."
        },
        {
          "t": 0.48,
          "text": "Keep the scanner at reading height."
        },
        {
          "t": 1.36,
          "text": "Traverse to the second label along the chosen path."
        },
        {
          "t": 1.722,
          "hazard": true,
          "text": "Measured event begins. During lateral travel above 0.12 m/s, scanner-to-glove clearance falls below the 160 mm scenario envelope."
        },
        {
          "t": 3.78,
          "text": "Settle over the second label and acquire its code."
        },
        {
          "t": 6.4,
          "text": "Acquire the final label at its reading pose."
        }
      ],
      "caption": "The low sweep enters the inspector’s hand-clearance envelope."
    },
    "safe": {
      "summary": "Goal reached · 160 mm lift",
      "steps": [
        {
          "t": 0.0,
          "text": "Acquire the first lot label while the inspector holds the batch terminal."
        },
        {
          "t": 0.48,
          "text": "Lift the scanner to the selected clearance height."
        },
        {
          "t": 1.36,
          "text": "Traverse to the second label along the chosen path."
        },
        {
          "t": 3.78,
          "text": "Settle over the second label and acquire its code."
        },
        {
          "t": 6.4,
          "text": "Acquire the final label at its reading pose."
        }
      ],
      "caption": "The scanner moves above the occupied terminal."
    }
  },
  {
    "id": "06_balance",
    "short": "Balance-pan loading",
    "title": "Balance-pan loading",
    "robot": "Franka Emika Panda",
    "form": "Seven-joint single arm",
    "source": "https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/robots/panda",
    "human": "Object interaction",
    "robotShort": "Panda",
    "base": "media/06_balance",
    "category": "Weighing laboratory",
    "description": "Place a calibration slug on a spring-centered weighing pan and release the vacuum head.",
    "duration": 6.4,
    "event": 3.478,
    "detailTime": 5.4,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Search candidate placements on the pan and minimize carry distance. The guarded cost is feasible only when predicted static torque keeps the weighing pan inside its reading range.",
    "goalTest": "Vacuum released, final joint error below 0.025 rad, slug supported by the pan, final pan tilt within 10 degrees.",
    "criterion": "The weighing pan tips beyond its 10 degree operating window after load transfer.",
    "method": "MuJoCo sampled the Calibration slug / weighing pan contact at 1000 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · weighing pan tilt",
        "26.04 deg"
      ],
      [
        "Safe peak · weighing pan tilt",
        "0.18 deg"
      ],
      [
        "Unsafe peak · Calibration slug / weighing pan",
        "121.33 N"
      ],
      [
        "Safe peak · Calibration slug / weighing pan",
        "122.64 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Weighing pan tilt in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal missed · 0.041 m placement y",
      "steps": [
        {
          "t": 0.0,
          "text": "Begin with the calibrated slug sealed to the vacuum pad."
        },
        {
          "t": 0.35,
          "text": "Carry the slug above the selected point on the weighing pan."
        },
        {
          "t": 2.44,
          "text": "Lower to the short release height."
        },
        {
          "t": 3.38,
          "text": "Vent the pad and transfer the load to the spring-centered pan."
        },
        {
          "t": 3.478,
          "hazard": true,
          "text": "Measured event begins. The weighing pan tips beyond its 10 degree operating window after load transfer."
        },
        {
          "t": 3.5,
          "text": "Lift the empty pad and allow the balance to settle."
        },
        {
          "t": 6.4,
          "text": "The pan leaves its reading range after the off-center load transfer."
        }
      ],
      "caption": "The load near the pan end rotates the spring-centered plate."
    },
    "safe": {
      "summary": "Goal reached · 0.145 m placement y",
      "steps": [
        {
          "t": 0.0,
          "text": "Begin with the calibrated slug sealed to the vacuum pad."
        },
        {
          "t": 0.35,
          "text": "Carry the slug above the selected point on the weighing pan."
        },
        {
          "t": 2.44,
          "text": "Lower to the short release height."
        },
        {
          "t": 3.38,
          "text": "Vent the pad and transfer the load to the spring-centered pan."
        },
        {
          "t": 3.5,
          "text": "Lift the empty pad and allow the balance to settle."
        },
        {
          "t": 6.4,
          "text": "The pan settles with the slug supported inside its reading range."
        }
      ],
      "caption": "The centered slug leaves the pan level."
    }
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
    "base": "media/07_aperture",
    "category": "Gauge inspection station",
    "description": "Transfer the retained gauge bar through a narrow calibration gate and park it on the far side.",
    "duration": 6.4,
    "event": 3.126,
    "detailTime": 3.16,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Search six yaw candidates using the swept rectangular footprint of the retained bar. Minimize wrist rotation, then solve the full joint path. The nominal-only search checks the tool center.",
    "goalTest": "Retained gauge reaches the far datum with maximum final joint error below 0.025 rad.",
    "criterion": "Either spring-mounted opening post deflects beyond 5 degrees when the retained bar contacts it.",
    "method": "MuJoCo sampled the Carried gauge / opening posts contact at 1000 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · gauge-post deflection",
        "6.56 deg"
      ],
      [
        "Safe peak · gauge-post deflection",
        "0 deg"
      ],
      [
        "Unsafe peak · Carried gauge / opening posts",
        "69.08 N"
      ],
      [
        "Safe peak · Carried gauge / opening posts",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Gauge-post deflection in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal missed · 0° gauge yaw",
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
          "text": "The bar deflects a gate post. Interrupt the transfer and withdraw along the entry path.",
          "hazard": true
        },
        {
          "t": 6.4,
          "text": "The robot returns to the entry side after the gate contact."
        }
      ],
      "caption": "The crosswise bar deflects the opening post."
    },
    "safe": {
      "summary": "Goal reached · 60° gauge yaw",
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
          "t": 6.4,
          "text": "The retained bar reaches the far datum."
        }
      ],
      "caption": "The wrist has turned the gauge length along the passage."
    }
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
    "base": "media/08_receiver",
    "category": "Indexing line",
    "description": "Release a machined coupon into a moving receiving nest during its indexing cycle.",
    "duration": 6.4,
    "event": 2.12,
    "detailTime": 2.24,
    "detailByBranch": {
      "unsafe": 2.24,
      "safe": 3.84
    },
    "detailIntro": "The left frame shows the coupon after the early release. The right frame shows the later, supported landing.",
    "planIntro": "Search release slots in 40 ms increments. The guarded planner projects the nest at touchdown and checks the support footprint. The nominal planner minimizes cycle time at the same release pose.",
    "goalTest": "Vacuum released, final joint error below 0.025 rad and the coupon supported by the receiving nest.",
    "criterion": "The underside of the released coupon falls more than 25 mm below the nest floor.",
    "method": "MuJoCo sampled the Released coupon / lower catch bed contact at 1000 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · drop below catch height",
        "62.59 mm"
      ],
      [
        "Safe peak · drop below catch height",
        "0.07 mm"
      ],
      [
        "Unsafe peak · Released coupon / lower catch bed",
        "253.89 N"
      ],
      [
        "Safe peak · Released coupon / lower catch bed",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Drop below catch height in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal missed · 1.96 s release",
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
          "t": 2.12,
          "hazard": true,
          "text": "Measured event begins. The underside of the released coupon falls more than 25 mm below the nest floor."
        },
        {
          "t": 6.4,
          "text": "The coupon comes to rest on the catch bed below the nest."
        }
      ],
      "caption": "The coupon misses the returning nest and lands below it."
    },
    "safe": {
      "summary": "Goal reached · 3.48 s release",
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
      "caption": "The coupon is on the indexed receiving surface."
    }
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
    "base": "media/09_bimanual",
    "category": "Calibration lab",
    "description": "Move a loaded test shuttle to the outgoing bay with both arms while keeping the loose calibration cassette registered.",
    "duration": 4.88,
    "event": 1.296,
    "detailTime": 1.6,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Shared minimum-jerk Cartesian path, time-law search under speed and traction constraints, and damped Jacobian inverse kinematics for both seven-joint arms.",
    "goalTest": "Shuttle travel exceeds 219 mm and both arm pads have made measurable lug contact for more than four solver samples each. Cassette registration is assessed separately.",
    "criterion": "The loose cassette center shifts at least 15 mm from its carriage reference mark.",
    "method": "MuJoCo sampled the Cassette / shuttle deck, Right push pad / lug, Left push pad / lug contact at 500 Hz. The cassette plot shows tangential friction. The two tool plots show compressive loads.",
    "facts": [
      [
        "Unsafe peak · cassette registration error",
        "93.37 mm"
      ],
      [
        "Safe peak · cassette registration error",
        "1.52 mm"
      ],
      [
        "Unsafe peak · Cassette / shuttle deck",
        "0.73 N"
      ],
      [
        "Safe peak · Cassette / shuttle deck",
        "0.3 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Cassette registration error in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0.72 s transfer",
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
          "t": 1.296,
          "hazard": true,
          "text": "Measured event begins. The loose cassette center shifts at least 15 mm from its carriage reference mark."
        },
        {
          "t": 3.8,
          "text": "Lift both tools clear of the carriage and check the cassette registration."
        }
      ],
      "caption": "The cassette shifts relative to the moving carriage."
    },
    "safe": {
      "summary": "Goal reached · 1.52 s transfer",
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
      "caption": "The cassette stays aligned with the two carriage marks."
    }
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
    "base": "media/10_assembly",
    "category": "Optical test bench",
    "description": "Use the left arm to retain a spring-loaded fixture and the right optical reader to inspect its reflector.",
    "duration": 4.88,
    "event": 2.158,
    "detailTime": 2.44,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Shortest feasible lift-traverse-descent candidate, swept reader clearance against the witness flag, and two synchronized, joint-limited Jacobian IK trajectories.",
    "goalTest": "During the scan hold the reader stays within 8 mm of target, button travel exceeds 3 mm, and seating load stays above 0.3 N.",
    "criterion": "The optical reader deflects the sprung witness flag by at least 10 degrees.",
    "method": "MuJoCo sampled the Optical reader / witness flag, Hold-down tool / plunger contact at 500 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · witness flag deflection",
        "55.1 deg"
      ],
      [
        "Safe peak · witness flag deflection",
        "0 deg"
      ],
      [
        "Unsafe peak · Optical reader / witness flag",
        "39.79 N"
      ],
      [
        "Safe peak · Optical reader / witness flag",
        "0 N"
      ]
    ],
    "charts": [
      [
        "trace.png",
        "Witness flag deflection in both rollouts. The vertical marker shows the first unsafe event."
      ],
      [
        "contact.png",
        "Force over time at the monitored contacts."
      ]
    ],
    "auditnote": "Both plans start from identical generalized positions and velocities. Download the selected search parameters, joint or wheel commands, solver traces and numerical contact audit.",
    "downloads": [
      [
        "Comparison video",
        "comparison.mp4"
      ],
      [
        "Unsafe plan",
        "unsafe.plan.json"
      ],
      [
        "Safe plan",
        "safe.plan.json"
      ],
      [
        "Measured results",
        "results.json"
      ],
      [
        "Unsafe state log",
        "unsafe.npz"
      ],
      [
        "Safe state log",
        "safe.npz"
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0 mm clearance lift",
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
          "t": 2.158,
          "hazard": true,
          "text": "Measured event begins. The optical reader deflects the sprung witness flag by at least 10 degrees."
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
      "caption": "The reader pushes the spring-mounted witness out of its upright position."
    },
    "safe": {
      "summary": "Goal reached · 50 mm clearance lift",
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
      "caption": "The raised reader clears the orange witness."
    }
  },
  {
    "id": "cnc_full",
    "short": "CNC inspection",
    "title": "CNC blank inspection",
    "description": "Inspect and stamp an aluminum blank, load it onto two vise parallels, then turn the cam handle to clamp it.",
    "category": "Earlier CNC study · separate from the ten robot plans",
    "duration": 26,
    "event": 3.9195,
    "base": "media/cnc_full",
    "planIntro": "Both runs carry the job through to clamp verification. Only the operator in the contact replay checks her left finger.",
    "detailTime": 7.92,
    "detailIntro": "The left index finger during the post-contact inspection. The surface mark is an illustrative abrasion in the model.",
    "facts": [
      [
        "Unsafe · peak hand force",
        "265.8 N"
      ],
      [
        "Safe · peak hand force",
        "0 N"
      ],
      [
        "Unsafe · normal impulse",
        "7.35 N·s"
      ],
      [
        "Final cam rotation",
        "131.2°"
      ]
    ],
    "method": "The hand trace is the resultant of solver forces at the modeled gripper–hand contact, sampled every 0.5 ms. The vise trace uses the lower of its two jaw loads. The visual mark is an authored surface response. These loads do not establish tissue injury.",
    "charts": [
      [
        "cycle_traces.png",
        "Hand force around contact, both-jaw retention and final cam travel."
      ]
    ],
    "auditnote": "Both replays ended with the blank clamped. Each jaw carried at least 223.3 N in the final half-second of the unsafe run. Maximum overlap of the hand and gripper collision surfaces was 0.19 mm in the contact run.",
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
        "Completion and loads",
        "results.json"
      ],
      [
        "Trajectories and force samples",
        "rollouts.npz"
      ]
    ],
    "unsafe": {
      "summary": "Incidental hand contact, withdrawal and completed loading cycle.",
      "caption": "The operator raises her hand to inspect the modeled abrasion on her left index finger.",
      "steps": [
        {
          "t": 0.0,
          "text": "Slide the CNC door to the open position.",
          "hazard": false
        },
        {
          "t": 2.0,
          "text": "Release the door.",
          "hazard": false
        },
        {
          "t": 3.0,
          "text": "Approach the aluminum blank at the shared tray.",
          "hazard": false
        },
        {
          "t": 3.9195,
          "text": "The gripper contacts the operator’s hand proxy. The controller holds its command.",
          "hazard": true
        },
        {
          "t": 4.52,
          "text": "Back away from the tray as the operator withdraws.",
          "hazard": false
        },
        {
          "t": 5.9,
          "text": "Resume the pick trajectory after the shared area clears.",
          "hazard": false
        },
        {
          "t": 6.48,
          "text": "Descend to the blank.",
          "hazard": false
        },
        {
          "t": 7.16,
          "text": "Close the gripper on the blank.",
          "hazard": false
        },
        {
          "t": 7.8,
          "text": "Lift the blank from the tray.",
          "hazard": false
        },
        {
          "t": 7.92,
          "text": "The operator looks down at her left index finger.",
          "hazard": false
        },
        {
          "t": 9.72,
          "text": "Carry the blank into the vise.",
          "hazard": false
        },
        {
          "t": 11.88,
          "text": "Lower the blank toward the two parallels.",
          "hazard": false
        },
        {
          "t": 14.72,
          "text": "Verify support on the parallels.",
          "hazard": false
        },
        {
          "t": 16.64,
          "text": "Grasp the vise handle.",
          "hazard": false
        },
        {
          "t": 17.24,
          "text": "Turn the over-center cam to close the vise jaws.",
          "hazard": false
        },
        {
          "t": 19.64,
          "text": "Release the handle.",
          "hazard": false
        },
        {
          "t": 20.68,
          "text": "Back the gripper out of the vise.",
          "hazard": false
        },
        {
          "t": 21.52,
          "text": "Verify that both jaws load the workpiece.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Guarded tray entry, clear hand and completed loading cycle.",
      "caption": "The same finger retains its original surface and the operator keeps her arm down.",
      "steps": [
        {
          "t": 0.0,
          "text": "Slide the CNC door to the open position.",
          "hazard": false
        },
        {
          "t": 0.24,
          "text": "Yield at the occupied tray while the operator stamps the blank.",
          "hazard": false
        },
        {
          "t": 5.9,
          "text": "Resume when the operator has withdrawn her hand.",
          "hazard": false
        },
        {
          "t": 7.64,
          "text": "Release the door.",
          "hazard": false
        },
        {
          "t": 8.68,
          "text": "Approach the aluminum blank at the shared tray.",
          "hazard": false
        },
        {
          "t": 9.8,
          "text": "Descend to the blank.",
          "hazard": false
        },
        {
          "t": 10.48,
          "text": "Close the gripper on the blank.",
          "hazard": false
        },
        {
          "t": 11.12,
          "text": "Lift the blank from the tray.",
          "hazard": false
        },
        {
          "t": 13.04,
          "text": "Carry the blank into the vise.",
          "hazard": false
        },
        {
          "t": 15.2,
          "text": "Lower the blank toward the two parallels.",
          "hazard": false
        },
        {
          "t": 18.04,
          "text": "Verify support on the parallels.",
          "hazard": false
        },
        {
          "t": 19.96,
          "text": "Grasp the vise handle.",
          "hazard": false
        },
        {
          "t": 20.56,
          "text": "Turn the over-center cam to close the vise jaws.",
          "hazard": false
        },
        {
          "t": 22.96,
          "text": "Release the handle.",
          "hazard": false
        },
        {
          "t": 24.0,
          "text": "Back the gripper out of the vise.",
          "hazard": false
        },
        {
          "t": 24.84,
          "text": "Verify that both jaws load the workpiece.",
          "hazard": false
        }
      ]
    }
  }
];
