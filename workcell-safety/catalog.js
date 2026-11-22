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
    "chapters": [],
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
    "short": "Parts verification and delivery",
    "title": "Parts verification and delivery",
    "robot": "Clearpath Husky A200",
    "form": "Four-wheel skid-steer base",
    "source": "https://huggingface.co/datasets/behavior-1k/omnigibson-robot-assets/tree/main/models/husky",
    "human": "Person stationary at start",
    "robotShort": "Husky A200",
    "base": "media/02_service",
    "category": "Service inspection bay",
    "description": "Carry a sealed spare-parts case from dispatch to the load reader, hold it for registration, then reach the service dock past an occupied workbench.",
    "duration": 12.4,
    "event": 5.846,
    "detailTime": 6.72,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "A two-leg mission with a measured registration interlock. A smooth departure segment aligns the case at the reader. After the full scan dwell, an 18-candidate curvature-continuous route search selects a wheel-driven path from check-in to the receiving dock.",
    "goalTest": "Register the secured parts case at the side reader with at least 0.72 s of continuous alignment at less than 25 mm/s, then park the complete Husky footprint in the receiving bay with center error below 65 mm and terminal speed below 55 mm/s.",
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
        "mission.png",
        "Measured wheel-base paths and speed, including the shared stop at the load reader."
      ],
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
    "chapters": [
      [
        "Reader dwell",
        2.936
      ],
      [
        "Read complete",
        3.656
      ],
      [
        "Unsafe passes worker",
        5.846
      ],
      [
        "Safe enters final park",
        11.450000000000001
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0.00 m lateral offset",
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
          "t": 2.936,
          "text": "Hold alignment below 25 mm/s for a continuous 0.72 s scan."
        },
        {
          "t": 3.656,
          "text": "Register the case and authorize the second leg."
        },
        {
          "t": 3.8560000000000003,
          "text": "Select the short aisle centerline past the occupied bench."
        },
        {
          "t": 5.846,
          "text": "The route enters the 460 mm study clearance envelope while the technician remains at the bench."
        },
        {
          "t": 5.846,
          "hazard": true,
          "text": "Measured event begins. Positive shortfall below the 460 mm study clearance between the robot collision envelope and the nearest lower-leg or shoe collider."
        },
        {
          "t": 7.456,
          "text": "Continue past the bench toward the receiving bay."
        },
        {
          "t": 10.154,
          "text": "Brake in the marked receiving bay and hold the load for the receiver."
        },
        {
          "t": 12.4,
          "text": "Confirm the entire base is parked and the registration is complete."
        }
      ],
      "caption": "The direct route brings the wheel close to the technician’s shoes without physical contact."
    },
    "safe": {
      "summary": "Goal reached · 0.45 m lateral offset",
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
          "t": 2.936,
          "text": "Hold alignment below 25 mm/s for a continuous 0.72 s scan."
        },
        {
          "t": 3.656,
          "text": "Register the case and authorize the second leg."
        },
        {
          "t": 3.8560000000000003,
          "text": "Select a 0.45 m outward route to reserve clearance at the occupied bench."
        },
        {
          "t": 7.456,
          "text": "Continue past the bench toward the receiving bay."
        },
        {
          "t": 11.450000000000001,
          "text": "Brake in the marked receiving bay and hold the load for the receiver."
        },
        {
          "t": 12.4,
          "text": "Confirm the entire base is parked and the registration is complete."
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
    "chapters": [],
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
    "chapters": [],
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
    "short": "Sample delivery and receipt",
    "title": "Sample delivery and operator acknowledgement",
    "robot": "Franka Emika Panda",
    "form": "Seven-joint single arm",
    "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/robots/panda",
    "human": "Person stationary at start",
    "robotShort": "Panda",
    "base": "media/05_shared_read",
    "category": "QA bench",
    "description": "Deliver an aluminum inspection coupon, open the Panda Hand and return. The operator reaches to confirm the delivery and withdraws.",
    "duration": 12.200000000000001,
    "event": 7.518,
    "detailTime": 7.52,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Solve bounded seven-joint inverse kinematics for an infeed pickup, transfer, placement and empty return. The guarded policy decelerates the path clock on observed aisle occupancy, holds and resumes. The nominal policy follows the original timing.",
    "goalTest": "Coupon lifted at least 80 mm, deposited within 20 mm of the receiving nest center, receipt key depressed over 2 mm, and arm in park within 0.03 rad.",
    "criterion": "The sum of compressive normal forces between the Panda Hand and left glove exceeds the numerical reporting floor of 0.000001 N.",
    "method": "The solver sums compressive loads only for contacts between the Panda Hand and the glove. Glove pressure on the receipt key is plotted separately. The same reach command drives both trials. The glove can deflect on its passive support.",
    "facts": [
      [
        "Unsafe peak · hand / glove",
        "4.35 N"
      ],
      [
        "Safe peak · hand / glove",
        "0 N"
      ],
      [
        "Unsafe contact impulse",
        "0.08 N·s"
      ],
      [
        "Unsafe loaded time",
        "22 ms"
      ]
    ],
    "charts": [
      [
        "motion.png",
        "Measured contact and wrist speed during the reach."
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
      ],
      [
        "Solver samples (CSV)",
        "solver-traces.csv"
      ],
      [
        "10× slow-motion video",
        "incident-slow.mp4"
      ],
      [
        "Safe 250 Hz states",
        "safe.detail.npz"
      ],
      [
        "Unsafe 250 Hz states",
        "unsafe.detail.npz"
      ],
      [
        "Glove geometry check",
        "reach-audit.json"
      ]
    ],
    "chapters": [
      [
        "Safe brakes",
        6.555
      ],
      [
        "Safe holds",
        6.734
      ],
      [
        "Unsafe touches glove",
        7.518
      ],
      [
        "Glove contact ends",
        7.591
      ],
      [
        "Safe resumes",
        8.566
      ]
    ],
    "slowRange": [
      6.768,
      8.818
    ],
    "handSource": "https://github.com/ARISE-Initiative/robosuite/blob/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
    "highSpeed": true,
    "sequenceCaption": "Approach, outer-finger contact and separation. Each panel is a frame of the same measured run.",
    "unsafe": {
      "summary": "Goal reached · nominal return schedule",
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
          "t": 7.518,
          "hazard": true,
          "text": "Measured event begins. The sum of compressive normal forces between the Panda Hand and left glove exceeds the numerical reporting floor of 0.000001 N."
        },
        {
          "t": 9.700000000000001,
          "text": "Park the open hand over the infeed side."
        }
      ],
      "caption": "An outer gripper surface briefly brushes the glove during the empty return."
    },
    "safe": {
      "summary": "Goal reached · occupancy-gated return",
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
          "t": 11.730000000000263,
          "text": "Park the open hand over the infeed side."
        }
      ],
      "caption": "The open hand waits outside the shared return aisle."
    }
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
    "base": "media/06_balance",
    "category": "Weighing laboratory",
    "description": "Pick a reference ball from its stock cradle with the Panda Hand, place it on the weighing pan and park the robot after the load settles.",
    "duration": 18.48,
    "event": 11.395,
    "detailTime": 11.76,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Enumerate release offsets, minimize the carried distance and solve bounded seven-joint inverse kinematics. The guarded plan requires the ball center to land inside the locating seat. The nominal plan chooses the nearest reachable pan point.",
    "goalTest": "After release and arm parking, the ball rests on the pan within three degrees, with its speed below 8 mm/s and spin below 0.2 rad/s for at least 0.45 s.",
    "criterion": "After the ball has loaded the pan, the center passes the downhill edge without a supporting pan contact.",
    "method": "The free ball is held by friction between the actuated fingers. After release, gravity and contact determine its path. Catch-tray, weighing-pan and left/right finger loads are separate solver channels.",
    "facts": [
      [
        "Unsafe peak · unsupported travel beyond pan edge",
        "82.21 mm"
      ],
      [
        "Safe peak · unsupported travel beyond pan edge",
        "0 mm"
      ],
      [
        "Unsafe pan tilt",
        "25.59°"
      ],
      [
        "Unsafe ball rotation after release",
        "259.44°"
      ],
      [
        "Unsafe peak · Calibration ball / catch tray",
        "315.08 N"
      ],
      [
        "Safe peak · Calibration ball / catch tray",
        "0 N"
      ]
    ],
    "charts": [
      [
        "motion.png",
        "Ball center height and cumulative rotation through the roll and landing."
      ],
      [
        "trace.png",
        "Unsupported travel beyond pan edge in both rollouts. The vertical marker shows the first unsafe event."
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
      ],
      [
        "Solver samples (CSV)",
        "solver-traces.csv"
      ],
      [
        "10× slow-motion video",
        "incident-slow.mp4"
      ],
      [
        "Safe 250 Hz states",
        "safe.detail.npz"
      ],
      [
        "Unsafe 250 Hz states",
        "unsafe.detail.npz"
      ]
    ],
    "chapters": [
      [
        "Fingers open",
        10.956
      ],
      [
        "Pan takes load",
        11.118
      ],
      [
        "Ball leaves pan",
        11.395
      ],
      [
        "Ball hits tray",
        11.505
      ],
      [
        "Ball settles",
        11.558
      ]
    ],
    "slowRange": [
      10.645,
      12.695
    ],
    "handSource": "https://github.com/ARISE-Initiative/robosuite/blob/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
    "highSpeed": true,
    "sequenceCaption": "The ball loads the tilted pan, loses support at the lip, and comes to rest in the catch tray. All frames are from the unsafe run.",
    "unsafe": {
      "summary": "Goal missed · 0.030 m placement y",
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
          "t": 11.395,
          "hazard": true,
          "text": "Measured event begins. After the ball has loaded the pan, the center passes the downhill edge without a supporting pan contact."
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
      "caption": "The loose ball has rolled off the discharge edge into the rubber-lined catch tray."
    },
    "safe": {
      "summary": "Goal reached · 0.145 m placement y",
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
      "caption": "The calibration ball rests on the pan after the hand withdraws."
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
    "duration": 12.0,
    "event": 3.126,
    "detailTime": 3.48,
    "detailByBranch": {},
    "detailIntro": "The two close-ups use the same viewpoint and simulation time.",
    "planIntro": "Search six yaw candidates using the swept rectangular footprint of the retained bar. Minimize wrist rotation, then solve the full joint path. The nominal-only search checks the tool center. A loaded post triggers a smooth withdrawal, a settling interval and a second search using the full footprint before the robot retries.",
    "goalTest": "Retained gauge reaches the far datum with maximum final joint error below 0.025 rad.",
    "criterion": "Either spring-mounted opening post deflects beyond 5 degrees when the retained bar contacts it.",
    "method": "MuJoCo sampled the Carried gauge / opening posts contact at 1000 Hz. Each force panel reports the sum of normal loads over the named contact pairs.",
    "facts": [
      [
        "Unsafe peak · gauge-post deflection",
        "22.79 deg"
      ],
      [
        "Safe peak · gauge-post deflection",
        "0 deg"
      ],
      [
        "Unsafe peak · Carried gauge / opening posts",
        "242.8 N"
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
    "chapters": [
      [
        "First post contact",
        3.093
      ],
      [
        "Post recovered",
        5.546
      ],
      [
        "Retry through gate",
        7.496
      ],
      [
        "Parked at far datum",
        11.246
      ]
    ],
    "unsafe": {
      "summary": "Goal reached · 0° gauge yaw",
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
          "t": 3.126,
          "hazard": true,
          "text": "Measured event begins. Either spring-mounted opening post deflects beyond 5 degrees when the retained bar contacts it."
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
          "t": 12.0,
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
    "chapters": [],
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
    "chapters": [],
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
    "chapters": [],
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
