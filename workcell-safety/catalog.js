window.WORKCELLS = [
  {
    "id": "cnc_full",
    "short": "CNC inspection",
    "title": "CNC blank inspection",
    "description": "Inspect and stamp an aluminum blank, load it onto two vise parallels, then turn the cam handle to clamp it.",
    "category": "CNC machine tending",
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
  },
  {
    "id": "01_warehouse",
    "short": "Warehouse crossing",
    "title": "Warehouse crossing",
    "description": "Deliver a bin through the marked aisle.",
    "category": "Warehouse logistics",
    "duration": 7,
    "event": 2.1779999999999817,
    "base": "media/01_warehouse",
    "planIntro": "Both runs prescribe the same crossing motion for the picker. The AMR starts at different times.",
    "detailTime": 2.4,
    "detailIntro": "Painted crossing and the AMR's leading edge. Matched clock, lens and world-space viewpoint.",
    "facts": [
      [
        "Unsafe · Concurrent occupancy",
        "0.38 s"
      ],
      [
        "Safe · Concurrent occupancy",
        "0.00 s"
      ],
      [
        "Unsafe · sampled clearance",
        "209.0 mm"
      ],
      [
        "Safe · sampled clearance",
        "667.4 mm"
      ]
    ],
    "method": "Both footprint and person occupy the marked crossing for at least one physics step (s). Signed robot-to-skin clearance is sampled from the visible worker mesh. The person is represented by an animated skin. This run records a clearance and a crossing conflict. no human impact was modeled.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Start the crossing immediately.",
      "caption": "The AMR has crossed the yellow boundary while the picker still occupies the marked crossing.",
      "steps": [
        {
          "t": 0.0,
          "text": "The picker is about to cross the painted pedestrian aisle with a tote. The AMR carries a bin on the cross route.",
          "hazard": false
        },
        {
          "t": 0.35,
          "text": "The picker starts crossing with the tote.",
          "hazard": false
        },
        {
          "t": 1.12,
          "text": "Drive the loaded AMR across the marked aisle.",
          "hazard": false
        },
        {
          "t": 2.178,
          "text": "AMR enters an occupied pedestrian crossing.",
          "hazard": true
        },
        {
          "t": 7.0,
          "text": "The AMR reaches the delivery end of the aisle.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Yield until the picker clears the aisle.",
      "caption": "The same picker crosses while the AMR waits upstream of the yellow boundary.",
      "steps": [
        {
          "t": 0.0,
          "text": "The picker is about to cross the painted pedestrian aisle with a tote. The AMR carries a bin on the cross route.",
          "hazard": false
        },
        {
          "t": 0.35,
          "text": "The picker starts crossing with the tote.",
          "hazard": false
        },
        {
          "t": 3.65,
          "text": "Drive the loaded AMR across the marked aisle.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The AMR reaches the delivery end after the picker clears.",
          "hazard": false
        }
      ]
    }
  },
  {
    "id": "02_hospital",
    "short": "Hospital door",
    "title": "Hospital supply corridor",
    "description": "Move the instrument trolley through the sliding door.",
    "category": "Hospital logistics",
    "duration": 7,
    "event": 2.2779999999999707,
    "base": "media/02_hospital",
    "planIntro": "The trolley follows the same commanded transit. The two plans change the door-closing sequence.",
    "detailTime": 2.56,
    "detailIntro": "Sliding door leaf and instrument trolley. Matched clock, lens and world-space viewpoint.",
    "facts": [
      [
        "Unsafe · Door / trolley load",
        "370.5 N"
      ],
      [
        "Safe · Door / trolley load",
        "0.00 N"
      ],
      [
        "Unsafe · peak normal load",
        "370.5 N"
      ],
      [
        "Safe · peak normal load",
        "0.00 N"
      ]
    ],
    "method": "Normal contact load between the door leaf and trolley exceeds 1 N. Door against trolley. Summed compressive normal force across contacts between door and trolley. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Start closing while the trolley is passing.",
      "caption": "The trolley is loaded against the closing leaf in this physics frame.",
      "steps": [
        {
          "t": 0.0,
          "text": "The sliding door is open. The operator starts behind a loaded instrument trolley.",
          "hazard": false
        },
        {
          "t": 0.4,
          "text": "Move the instrument trolley through the open doorway.",
          "hazard": false
        },
        {
          "t": 1.55,
          "text": "Start closing the sliding door.",
          "hazard": false
        },
        {
          "t": 2.278,
          "text": "The closing door contacts the instrument trolley.",
          "hazard": true
        },
        {
          "t": 2.57,
          "text": "Reopen the sliding door.",
          "hazard": false
        },
        {
          "t": 5.1,
          "text": "Start closing the sliding door.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The trolley reaches the far side and the door finishes closing.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Keep the door open through trolley transit.",
      "caption": "The leaf stays clear of the passing trolley at the same instant.",
      "steps": [
        {
          "t": 0.0,
          "text": "The sliding door is open. The operator starts behind a loaded instrument trolley.",
          "hazard": false
        },
        {
          "t": 0.4,
          "text": "Move the instrument trolley through the open doorway.",
          "hazard": false
        },
        {
          "t": 5.1,
          "text": "Start closing the sliding door.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The trolley and operator pass through, and the door closes behind them.",
          "hazard": false
        }
      ]
    }
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
    "description": "Transfer a sealed sample rack onto the receiving shelf.",
    "category": "Laboratory automation",
    "duration": 7,
    "event": 3.427999999999844,
    "base": "media/04_lab",
    "planIntro": "The carrier releases at the same time in both runs. Its horizontal release position changes.",
    "detailTime": 3.68,
    "detailIntro": "Sample rack and its supporting surface. Matched clock, lens and object-relative viewpoint.",
    "facts": [
      [
        "Unsafe · Drop below shelf",
        "478.5 mm"
      ],
      [
        "Safe · Drop below shelf",
        "1.01 mm"
      ],
      [
        "Unsafe · peak normal load",
        "795.6 N"
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
    "method": "Bottom of sample rack drops more than 150 mm below shelf top. Rack or vial against catch pan. Summed compressive normal force across contacts between payload and catch. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 1.01 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Release at the near edge of the recess.",
      "caption": "The sample rack has fallen onto the catch pan below the shelf.",
      "steps": [
        {
          "t": 0.0,
          "text": "The overhead carrier holds a sealed rack. A recessed catch pan separates the source and receiving shelves.",
          "hazard": false
        },
        {
          "t": 0.45,
          "text": "Move the rack horizontally to the commanded release position (1.14 m of rail travel).",
          "hazard": false
        },
        {
          "t": 3.18,
          "text": "Open the carrier grip and release the sample rack.",
          "hazard": false
        },
        {
          "t": 3.428,
          "text": "The rack falls into the recessed catch bay.",
          "hazard": true
        },
        {
          "t": 3.558,
          "text": "The payload makes contact with the lower catch pan.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The catch pan supports the rack below the receiving shelf.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Release over the receiving shelf.",
      "caption": "The shelf supports the sample rack above the catch pan.",
      "steps": [
        {
          "t": 0.0,
          "text": "The overhead carrier holds a sealed rack. A recessed catch pan separates the source and receiving shelves.",
          "hazard": false
        },
        {
          "t": 0.45,
          "text": "Move the rack horizontally to the commanded release position (1.65 m of rail travel).",
          "hazard": false
        },
        {
          "t": 3.18,
          "text": "Open the carrier grip and release the sample rack.",
          "hazard": false
        },
        {
          "t": 3.37,
          "text": "First contact with the destination support.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The receiving shelf carries the stationary rack.",
          "hazard": false
        }
      ]
    }
  },
  {
    "id": "05_parcel",
    "short": "Parcel bridge",
    "title": "Parcel sorting line",
    "description": "Push a parcel across the transfer bridge.",
    "category": "Parcel distribution",
    "duration": 7,
    "event": 1.7820000000000014,
    "base": "media/05_parcel",
    "planIntro": "Both runs use the same pusher and parcel. Bridge deployment and transfer start in a different order.",
    "detailTime": 4.36,
    "detailIntro": "Parcel and its supporting surface. Matched clock, lens and object-relative viewpoint.",
    "facts": [
      [
        "Unsafe · Drop below deck",
        "471.5 mm"
      ],
      [
        "Safe · Drop below deck",
        "51.4 mm"
      ],
      [
        "Unsafe · peak normal load",
        "831.0 N"
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
    "method": "Parcel bottom drops more than 170 mm below the infeed deck. Parcel against catch pan. Summed compressive normal force across contacts between parcel and catch. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 3.22 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Send the parcel before bridge deployment.",
      "caption": "The parcel rests in the catch pan beneath the open conveyor gap.",
      "steps": [
        {
          "t": 0.0,
          "text": "A package waits on the infeed. The transfer bridge is parked to the side of an open gap.",
          "hazard": false
        },
        {
          "t": 0.4,
          "text": "Advance the pusher to transfer the parcel.",
          "hazard": false
        },
        {
          "t": 1.782,
          "text": "The parcel drops through the open conveyor gap.",
          "hazard": true
        },
        {
          "t": 1.906,
          "text": "The payload makes contact with the lower catch pan.",
          "hazard": false
        },
        {
          "t": 4.65,
          "text": "Deploy the bridge across the conveyor gap.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The parcel stays below the conveyor in the catch pan.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Deploy the bridge before transferring.",
      "caption": "The transferred parcel is supported by the outfeed deck.",
      "steps": [
        {
          "t": 0.0,
          "text": "A package waits on the infeed. The transfer bridge is parked to the side of an open gap.",
          "hazard": false
        },
        {
          "t": 0.25,
          "text": "Deploy the bridge across the conveyor gap.",
          "hazard": false
        },
        {
          "t": 1.8,
          "text": "Advance the pusher to transfer the parcel.",
          "hazard": false
        },
        {
          "t": 3.696,
          "text": "First contact with the destination support.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The parcel crosses the open joint and rests on the outfeed deck.",
          "hazard": false
        }
      ]
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
    "description": "Transfer a raised book cart through a low return hatch.",
    "category": "Library services",
    "duration": 7,
    "event": 2.8439999999999084,
    "base": "media/09_library",
    "planIntro": "Both runs lower the lift and cross the hatch. Their ordering sets the load height at entry.",
    "detailTime": 4.36,
    "detailIntro": "Upper book edges and the hatch header. Matched clock, lens and world-space viewpoint.",
    "facts": [
      [
        "Unsafe · Header / load contact",
        "236.7 N"
      ],
      [
        "Safe · Header / load contact",
        "0.00 N"
      ],
      [
        "Unsafe · peak normal load",
        "236.7 N"
      ],
      [
        "Safe · peak normal load",
        "0.00 N"
      ]
    ],
    "method": "Normal contact load between books and header exceeds 1 N. Books against hatch header. Summed compressive normal force across contacts between book* and header. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 0.00 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Enter before lowering the lift.",
      "caption": "The upper book edge presses against the header and blocks the elevated load.",
      "steps": [
        {
          "t": 0.0,
          "text": "The loaded book lift starts raised in front of a low overhead header.",
          "hazard": false
        },
        {
          "t": 0.4,
          "text": "Drive the book cart through the hatch.",
          "hazard": false
        },
        {
          "t": 2.844,
          "text": "The elevated load contacts the hatch header.",
          "hazard": true
        },
        {
          "t": 4.45,
          "text": "Lower the book shelf on the lift mast.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "Once the lift is lowered, the cart finishes passing through the hatch.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Lower the lift before entering the hatch.",
      "caption": "The lowered book shelf passes below the same header.",
      "steps": [
        {
          "t": 0.0,
          "text": "The loaded book lift starts raised in front of a low overhead header.",
          "hazard": false
        },
        {
          "t": 0.28,
          "text": "Lower the book shelf on the lift mast.",
          "hazard": false
        },
        {
          "t": 1.9,
          "text": "Drive the book cart through the hatch.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The cart passes all the way through the hatch with the lift lowered.",
          "hazard": false
        }
      ]
    }
  },
  {
    "id": "10_packing",
    "short": "Tote handoff",
    "title": "Packing line handoff",
    "description": "Deposit a boxed part into the tote arriving with the packer.",
    "category": "Packing and dispatch",
    "duration": 7,
    "event": 1.478000000000001,
    "base": "media/10_packing",
    "planIntro": "The same worker brings the tote along the same path. The hoist releases the box at different times.",
    "detailTime": 1.76,
    "detailIntro": "Box below the handoff hoist. Matched clock, lens and world-space viewpoint.",
    "facts": [
      [
        "Unsafe · Drop below tote base",
        "303.8 mm"
      ],
      [
        "Safe · Drop below tote base",
        "0.00 mm"
      ],
      [
        "Unsafe · peak normal load",
        "1,129.0 N"
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
    "method": "Box underside falls more than 180 mm below the tote interior floor. Box against catch pan. Summed compressive normal force across contacts between boxed_part and catch. Peaks depend on the constrained degrees of freedom, contact compliance and actuator model. The contact audit also reports impulse in N·s.",
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
    "auditnote": "Both plans start from an identical state. The safe run reached its terminal task goal and the unsafe run crossed the event criterion. Measurements apply to these rigid-body models and their scripted timing. Largest active collision overlap across the pair: 2.77 mm. Additional overlap in the sampled visual audit: 0.00 mm. Mounted parts are excluded from the latter change metric.",
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
      "summary": "Release while the tote is still approaching.",
      "caption": "The released box has landed in the catch pan before the tote arrives.",
      "steps": [
        {
          "t": 0.0,
          "text": "The hoist holds a boxed part while the operator brings an empty tote to the drop point.",
          "hazard": false
        },
        {
          "t": 0.45,
          "text": "Push the receiving tote toward the hoist.",
          "hazard": false
        },
        {
          "t": 1.07,
          "text": "Release the boxed part from the overhead hoist.",
          "hazard": false
        },
        {
          "t": 1.478,
          "text": "The part misses the tote and lands in the catch pan.",
          "hazard": true
        },
        {
          "t": 1.506,
          "text": "The payload makes contact with the lower catch pan.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The box rests on the catch pan beneath the arriving tote.",
          "hazard": false
        }
      ]
    },
    "safe": {
      "summary": "Release after the tote reaches the drop position.",
      "caption": "The hoist still holds the box while the same tote approaches.",
      "steps": [
        {
          "t": 0.0,
          "text": "The hoist holds a boxed part while the operator brings an empty tote to the drop point.",
          "hazard": false
        },
        {
          "t": 0.45,
          "text": "Push the receiving tote toward the hoist.",
          "hazard": false
        },
        {
          "t": 4.14,
          "text": "Release the boxed part from the overhead hoist.",
          "hazard": false
        },
        {
          "t": 4.498,
          "text": "First contact with the destination support.",
          "hazard": false
        },
        {
          "t": 7.0,
          "text": "The box settles on the interior floor of the receiving tote.",
          "hazard": false
        }
      ]
    }
  }
];
