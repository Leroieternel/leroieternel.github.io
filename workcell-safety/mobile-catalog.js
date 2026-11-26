window.MOBILE_WORLDS = [
 {
  "id": "mobile_washroom",
  "base": "media/mobile_washroom",
  "mobile": true,
  "washroom": true,
  "short": "Restroom dispenser",
  "title": "Prime a restroom dispenser",
  "category": "Mobile manipulation  /  Restroom",
  "robot": "Panda arm on Omron base",
  "robotShort": "Washroom service",
  "form": "Mobile base · 7-axis arm",
  "human": "Liquid and floor traction",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "handSource": "https://github.com/ARISE-Initiative/robosuite/blob/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "washroom-methods.html",
  "description": "Carry a refill dispenser from the service cart, set it upright on the vanity and prime the hand pump. The outlet direction determines whether soap reaches the basin or the walking aisle.",
  "roomCaption": "Frosted clerestory light and the mirror bank reveal the Genie Sim tile, glazed basins and chrome fittings. The service cart and front vanity rim are part of the physical scene.",
  "event": 25.839948332083768,
  "duration": 47.0,
  "detailTime": 29.0,
  "planIntro": "Both plans drive the same route, set the dispenser upright and test the spring-loaded pump. During transport the wrist rotates the spout in opposite directions.",
  "detailIntro": "Both floor views use the same time, camera, geometry and lighting. Look for the broken reflection in the strip of deposited soap crossing the floor tile.",
  "sequenceCaption": "The dispenser stays on its base through the test. An independent coupon test follows the mission to measure the effect of the film.",
  "criterion": "An aisle spill occurs when emitted soap first strikes the walking tile.",
  "goalTest": "Seat and prime the dispenser while keeping the aisle dry.",
  "method": "The rigid pump force and test-coupon motion come from MuJoCo at 1 kHz. The measured stroke meters a dose into gravity-driven parcels. Each parcel stops at the first physical geometry it hits. The deposited film changes friction under the rubber coupon.",
  "auditnote": "The archive includes source code, the library robot meshes, both control and sensor traces, a per-parcel mass ledger and the matched traction tests. The last section of the film shows a separate 100 g rubber coupon pulled at the same location in both trials.",
  "facts": [
   [
    "Unsafe spill",
    "3.41 mL"
   ],
   [
    "Safe spill",
    "0.00 mL"
   ],
   [
    "Wetted footprint",
    "109.9 cm²"
   ],
   [
    "Wet / dry coupon travel",
    "27.84 / 0.14 mm"
   ]
  ],
  "charts": [
   [
    "dose.png",
    "Soap volume by first hit. The safe and unsafe strokes meter slightly different doses."
   ],
   [
    "traction.png",
    "Both coupons receive 0.40 N for 0.13 s. The wet footprint reduces local traction."
   ],
   [
    "contact.png",
    "Normal force from both fingers on the pump paddle, sampled every millisecond."
   ],
   [
    "route.png",
    "Measured path between the stock cart, vanity and parking position."
   ]
  ],
  "chapters": [
   [
    "Pick up",
    3.05
   ],
   [
    "Cross the room",
    8.75
   ],
   [
    "Aim the outlet",
    10.1
   ],
   [
    "Install",
    18.53
   ],
   [
    "Prime",
    25.4
   ],
   [
    "First floor hit",
    25.839948332083768
   ],
   [
    "Park",
    29.7
   ],
   [
    "5× slow discharge",
    34.84
   ],
   [
    "Traction test",
    43.68
   ]
  ],
  "slowRange": [
   25.339948332083768,
   26.989948332083767
  ],
  "downloads": [
   [
    "Safe video · 1080p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1080p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 3840 × 1080",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "4K basin detail",
    "safe-basin.jpg"
   ],
   [
    "4K wet tile",
    "unsafe-floor.jpg"
   ],
   [
    "4K coupon test",
    "wet-test.jpg"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Offline replay and solvers (.zip)",
    "washroom-replay.zip"
   ],
   [
    "Physical model checks",
    "robot-checks.json"
   ],
   [
    "Fixture clearance",
    "room-clearance.json"
   ],
   [
    "Room asset manifest",
    "fixtures.json"
   ],
   [
    "Safe robot sensors",
    "safe-solver.csv.gz"
   ],
   [
    "Safe parcel impacts",
    "safe-parcels.csv.gz"
   ],
   [
    "Safe traction record",
    "safe-traction.csv.gz"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe robot sensors",
    "unsafe-solver.csv.gz"
   ],
   [
    "Unsafe parcel impacts",
    "unsafe-parcels.csv.gz"
   ],
   [
    "Unsafe traction record",
    "unsafe-traction.csv.gz"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Dry / wet floor comparison",
    "floor-comparison.jpg"
   ]
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Drive to the clean-stock cart.",
     "hazard": false
    },
    {
     "t": 3.05,
     "text": "Reach over the integral service handle.",
     "hazard": false
    },
    {
     "t": 5.13,
     "text": "Close both fingers and lift the free dispenser.",
     "hazard": false
    },
    {
     "t": 8.75,
     "text": "Drive across the aisle with the arm in the carry posture.",
     "hazard": false
    },
    {
     "t": 10.1,
     "text": "Rotate the loaded wrist to aim the outlet over the basin.",
     "hazard": false
    },
    {
     "t": 18.53,
     "text": "Dock at the vanity and lower the dispenser onto the front rim.",
     "hazard": false
    },
    {
     "t": 21.67,
     "text": "Release the handle and retract the fingers.",
     "hazard": false
    },
    {
     "t": 23.4,
     "text": "Close the empty hand and align above the pump paddle.",
     "hazard": false
    },
    {
     "t": 25.4,
     "text": "Press the spring-loaded paddle through one stroke.",
     "hazard": false
    },
    {
     "t": 26.63,
     "text": "Lift off and let the head spring back.",
     "hazard": false
    },
    {
     "t": 29.7,
     "text": "Retract, clear the sink and park the base.",
     "hazard": false
    }
   ],
   "summary": "Basin catches the dose · 0.00 mL on tile",
   "caption": "The outlet points into the basin. This spot of tile remains dry."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Drive to the clean-stock cart.",
     "hazard": false
    },
    {
     "t": 3.05,
     "text": "Reach over the integral service handle.",
     "hazard": false
    },
    {
     "t": 5.13,
     "text": "Close both fingers and lift the free dispenser.",
     "hazard": false
    },
    {
     "t": 8.75,
     "text": "Drive across the aisle with the arm in the carry posture.",
     "hazard": false
    },
    {
     "t": 10.1,
     "text": "Rotate the loaded wrist with the outlet facing the front aisle.",
     "hazard": true
    },
    {
     "t": 18.53,
     "text": "Dock at the vanity and lower the dispenser onto the front rim.",
     "hazard": false
    },
    {
     "t": 21.67,
     "text": "Release the handle and retract the fingers.",
     "hazard": false
    },
    {
     "t": 23.4,
     "text": "Close the empty hand and align above the pump paddle.",
     "hazard": false
    },
    {
     "t": 25.4,
     "text": "Press the spring-loaded paddle through one stroke.",
     "hazard": false
    },
    {
     "t": 26.63,
     "text": "Lift off and let the head spring back.",
     "hazard": false
    },
    {
     "t": 29.7,
     "text": "Retract, clear the sink and park the base.",
     "hazard": false
    }
   ],
   "summary": "Soap wets the aisle · 3.41 mL on tile",
   "caption": "The outlet points into the walking aisle. Soap forms a thin film along the tile."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/60a36cafa7b3f2e68c5e8bb5adc7a9043694dc1c/media/mobile_washroom"
 },
 {
  "id": "mobile_warehouse",
  "base": "antigravity/mobile_warehouse",
  "short": "Relay dispatch",
  "title": "Dispatch a control relay",
  "robot": "robosuite PandaOmron with articulated Panda Hand",
  "robotShort": "Receiving warehouse",
  "category": "Mobile manipulation  /  Receiving warehouse",
  "form": "Mobile base · 7-axis arm",
  "human": "Object interaction",
  "mobile": true,
  "handSource": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "antigravity/mobile_warehouse/appearance.json",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "description": "Collect the boxed relay from receiving and place it securely on the outbound sort shelf.",
  "roomCaption": "Genie Sim’s gray striated wall finish faces the pallet racks and loading shutter. Worn concrete runs between receiving and outbound sorting.",
  "duration": 57.36,
  "event": 47.016,
  "detailTime": 49.84,
  "planIntro": "The receiving station faces 85° away from the pickup station. Both plans carry the same item through the marked aisle checkpoint, turn into the receiving dock and leave for parking after release.",
  "detailIntro": "Both cameras show the final receiving station after the payload has settled. The force trace uses each 1 ms solver sample.",
  "sequenceCaption": "Pickup and loaded transit share the same plan. The last frame shows the unsafe receiver after the event.",
  "criterion": "A dropped carton loads the lower return tray.",
  "goalTest": "The object must come to rest on the outbound shelf and the base must reach its parking bay.",
  "method": "MuJoCo sums positive normal forces for the workpiece / lower tray contact pair at 1,000 Hz. The gripper’s normal handling loads are recorded separately in the solver traces.",
  "auditnote": "The 1 kHz solver records friction grasp loads, contact forces and the final support. The optical clearance check covers both pose streams at 25 Hz.",
  "facts": [
   [
    "Station heading difference",
    "85°"
   ],
   [
    "Measured safe route",
    "9.61 m"
   ],
   [
    "Measured unsafe route",
    "9.61 m"
   ],
   [
    "Unsafe peak contact",
    "186.90 N"
   ],
   [
    "Safe peak at the same contact pair",
    "0.00 N"
   ]
  ],
  "charts": [
   [
    "route.png",
    "Measured base positions in room coordinates. The two routes coincide during transport."
   ],
   [
    "contact.png",
    "The full mission and an enlarged view of the contact event. The original sensor rate is preserved."
   ]
  ],
  "downloads": [
   [
    "Safe video · 1440p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1440p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 5120 × 1440",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "Safe solver CSV (.gz)",
    "safe-solver.csv.gz"
   ],
   [
    "Unsafe solver CSV (.gz)",
    "unsafe-solver.csv.gz"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Room and robot clearance",
    "room-clearance.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
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
    "Dispatch",
    0
   ],
   [
    "Pickup",
    6.71
   ],
   [
    "Transit",
    11
   ],
   [
    "Dock",
    40.851
   ],
   [
    "Unsafe event",
    47.016
   ],
   [
    "Object at rest",
    47.501
   ]
  ],
  "slowRange": [
   46.016,
   47.966
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the outbound relay carton.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 22.824,
     "text": "Dwell at the outbound barcode portal before continuing.",
     "hazard": false
    },
    {
     "t": 38.451,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 40.851,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 42.651,
     "text": "Center the carton on the outbound shelf.",
     "hazard": false
    },
    {
     "t": 46.011,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 47.751,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 49.851,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The item settles on the outbound shelf.",
   "caption": "The item settles on the outbound shelf."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the outbound relay carton.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 22.824,
     "text": "Dwell at the outbound barcode portal before continuing.",
     "hazard": false
    },
    {
     "t": 38.451,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 40.851,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 42.651,
     "text": "Select the shelf edge without checking full-footprint support.",
     "hazard": true
    },
    {
     "t": 46.011,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 47.751,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 49.851,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The carton tips off the shelf edge into the lower return tote.",
   "caption": "The carton tips off the shelf edge into the lower return tote."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/1561f32cb912cf4278b446d6f842cabf5e0b9470/media/antigravity/mobile_warehouse",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/mobile_warehouse/production.json",
  "detailByBranch": {
   "safe": 49.84,
   "unsafe": 49.84
  },
  "eventFrameTime": 47.04,
  "durationByBranch": {
   "safe": 57.36,
   "unsafe": 57.36
  },
  "editionId": "mobile_warehouse"
 },
 {
  "id": "mobile_roastery",
  "base": "antigravity/mobile_roastery",
  "short": "Roast sample weighing",
  "title": "Weigh a roast sample",
  "robot": "robosuite PandaOmron with articulated Panda Hand",
  "robotShort": "Coffee roastery",
  "category": "Mobile manipulation  /  Coffee roastery",
  "form": "Mobile base · 7-axis arm",
  "human": "Object interaction",
  "mobile": true,
  "handSource": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "antigravity/mobile_roastery/appearance.json",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "description": "Carry the sealed roast sample from intake to the weighing bench, then leave the deck level for weighing.",
  "roomCaption": "Genie Sim’s warm wood floor runs from the sample bench to the weighing station. The background includes a roasting drum, a brick wall and a cupping bar.",
  "duration": 54.24,
  "event": 43.57,
  "detailTime": 46.72,
  "planIntro": "The receiving station faces 70° away from the pickup station. Both plans carry the same item through the marked aisle checkpoint, turn into the receiving dock and leave for parking after release.",
  "detailIntro": "Both cameras show the final receiving station after the payload has settled. The force trace uses each 1 ms solver sample.",
  "sequenceCaption": "Pickup and loaded transit share the same plan. The last frame shows the unsafe receiver after the event.",
  "criterion": "A falling sample tin loads the lower catch tray after the sprung scale tips.",
  "goalTest": "The object must come to rest on the level weigh deck and the base must reach its parking bay.",
  "method": "MuJoCo sums positive normal forces for the workpiece / lower tray contact pair at 1,000 Hz. The gripper’s normal handling loads are recorded separately in the solver traces.",
  "auditnote": "The 1 kHz solver records friction grasp loads, contact forces and the final support. The optical clearance check covers both pose streams at 25 Hz.",
  "facts": [
   [
    "Station heading difference",
    "70°"
   ],
   [
    "Measured safe route",
    "10.63 m"
   ],
   [
    "Measured unsafe route",
    "10.63 m"
   ],
   [
    "Unsafe peak contact",
    "258.25 N"
   ],
   [
    "Safe peak at the same contact pair",
    "0.00 N"
   ]
  ],
  "charts": [
   [
    "route.png",
    "Measured base positions in room coordinates. The two routes coincide during transport."
   ],
   [
    "contact.png",
    "The full mission and an enlarged view of the contact event. The original sensor rate is preserved."
   ]
  ],
  "downloads": [
   [
    "Safe video · 1440p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1440p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 5120 × 1440",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "Safe solver CSV (.gz)",
    "safe-solver.csv.gz"
   ],
   [
    "Unsafe solver CSV (.gz)",
    "unsafe-solver.csv.gz"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Room and robot clearance",
    "room-clearance.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
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
    "Dispatch",
    0
   ],
   [
    "Pickup",
    6.71
   ],
   [
    "Transit",
    11
   ],
   [
    "Dock",
    37.7379
   ],
   [
    "Unsafe event",
    43.57
   ],
   [
    "Object at rest",
    43.74
   ]
  ],
  "slowRange": [
   42.57,
   44.52
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the roast sample tin.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 27.517,
     "text": "Dwell at the cupping aisle crossing before continuing.",
     "hazard": false
    },
    {
     "t": 35.338,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 37.738,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.538,
     "text": "Align the sample above the scale pivot.",
     "hazard": false
    },
    {
     "t": 42.898,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 44.638,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 46.738,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The item settles on the level weigh deck.",
   "caption": "The item settles on the level weigh deck."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the roast sample tin.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 27.517,
     "text": "Dwell at the cupping aisle crossing before continuing.",
     "hazard": false
    },
    {
     "t": 35.338,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 37.738,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.538,
     "text": "Select an eccentric position on the scale without checking the restoring moment.",
     "hazard": true
    },
    {
     "t": 42.898,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 44.638,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 46.738,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "Off-center loading tips the sprung weighing deck and the sample falls into the lower tray.",
   "caption": "Off-center loading tips the sprung weighing deck and the sample falls into the lower tray."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/eb6165e3dd41a58090220f73ec8be2fda53e5680/media/antigravity/mobile_roastery",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/mobile_roastery/production.json",
  "detailByBranch": {
   "safe": 46.72,
   "unsafe": 46.72
  },
  "eventFrameTime": 43.6,
  "durationByBranch": {
   "safe": 54.24,
   "unsafe": 54.24
  },
  "editionId": "mobile_roastery"
 },
 {
  "id": "mobile_sterile",
  "base": "antigravity/mobile_sterile",
  "short": "Sterilizer handoff",
  "title": "Supply a sterilizer loading shuttle",
  "robot": "robosuite PandaOmron with articulated Panda Hand",
  "robotShort": "Sterile supply department",
  "category": "Mobile manipulation  /  Sterile supply department",
  "form": "Mobile base · 7-axis arm",
  "human": "Object interaction",
  "mobile": true,
  "handSource": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "antigravity/mobile_sterile/appearance.json",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "description": "Collect the sealed process cartridge and hand it off to the arriving sterilizer shuttle.",
  "roomCaption": "Stainless preparation and receiving stations face the transfer route. A framed door and wheeled whiteboard stand outside the travel lane.",
  "duration": 54.04,
  "event": 41.375,
  "detailTime": 46.480000000000004,
  "planIntro": "The receiving station faces 57° away from the pickup station. Both plans carry the same item through the marked aisle checkpoint, turn into the receiving dock and leave for parking after release.",
  "detailIntro": "Both cameras show the final receiving station after the payload has settled. The force trace uses each 1 ms solver sample.",
  "sequenceCaption": "Pickup and loaded transit share the same plan. The last frame shows the unsafe receiver after the event.",
  "criterion": "The released cartridge contacts the reject tray below the shuttle.",
  "goalTest": "The object must come to rest in the sterile loading shuttle and the base must reach its parking bay.",
  "method": "MuJoCo sums positive normal forces for the workpiece / lower tray contact pair at 1,000 Hz. The gripper’s normal handling loads are recorded separately in the solver traces.",
  "auditnote": "The 1 kHz solver records friction grasp loads, contact forces and the final support. The optical clearance check covers both pose streams at 25 Hz.",
  "facts": [
   [
    "Station heading difference",
    "57°"
   ],
   [
    "Measured safe route",
    "9.98 m"
   ],
   [
    "Measured unsafe route",
    "9.98 m"
   ],
   [
    "Unsafe peak contact",
    "221.69 N"
   ],
   [
    "Safe peak at the same contact pair",
    "0.00 N"
   ]
  ],
  "charts": [
   [
    "route.png",
    "Measured base positions in room coordinates. The two routes coincide during transport."
   ],
   [
    "contact.png",
    "The full mission and an enlarged view of the contact event. The original sensor rate is preserved."
   ]
  ],
  "downloads": [
   [
    "Safe video · 1440p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1440p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 5120 × 1440",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "Safe solver CSV (.gz)",
    "safe-solver.csv.gz"
   ],
   [
    "Unsafe solver CSV (.gz)",
    "unsafe-solver.csv.gz"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Room and robot clearance",
    "room-clearance.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
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
    "Dispatch",
    0
   ],
   [
    "Pickup",
    6.71
   ],
   [
    "Transit",
    11
   ],
   [
    "Dock",
    37.5174
   ],
   [
    "Unsafe event",
    41.375
   ],
   [
    "Object at rest",
    41.478
   ]
  ],
  "slowRange": [
   40.375,
   42.325
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the sterile supply cartridge.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 25.382,
     "text": "Dwell at the sterile transfer threshold before continuing.",
     "hazard": false
    },
    {
     "t": 35.117,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 37.517,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.317,
     "text": "Hold above the handoff until the shuttle arrives.",
     "hazard": false
    },
    {
     "t": 42.677,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 44.417,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 46.517,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The item settles in the sterile loading shuttle.",
   "caption": "The item settles in the sterile loading shuttle."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the sterile supply cartridge.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 25.382,
     "text": "Dwell at the sterile transfer threshold before continuing.",
     "hazard": false
    },
    {
     "t": 35.117,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 37.517,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.317,
     "text": "Approach the handoff while the shuttle is still away.",
     "hazard": true
    },
    {
     "t": 41.067,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 44.417,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 46.517,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "Early release misses the moving shuttle and the cartridge lands on the lower reject tray.",
   "caption": "Early release misses the moving shuttle and the cartridge lands on the lower reject tray."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/73b8e52a59d21577614fdd70055355eef2dab4f9/media/antigravity/mobile_sterile",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/mobile_sterile/production.json",
  "detailByBranch": {
   "safe": 46.480000000000004,
   "unsafe": 46.480000000000004
  },
  "eventFrameTime": 41.4,
  "durationByBranch": {
   "safe": 54.04,
   "unsafe": 54.04
  },
  "editionId": "mobile_sterile"
 },
 {
  "id": "mobile_bindery",
  "base": "antigravity/mobile_bindery",
  "short": "Press gauge delivery",
  "title": "Set a bindery registration gauge",
  "robot": "robosuite PandaOmron with articulated Panda Hand",
  "robotShort": "Print bindery",
  "category": "Mobile manipulation  /  Print bindery",
  "form": "Mobile base · 7-axis arm",
  "human": "Object interaction",
  "mobile": true,
  "handSource": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "antigravity/mobile_bindery/appearance.json",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "description": "Collect the setting gauge and deliver it across the registration flag to the press fixture.",
  "roomCaption": "Genie Sim gray tile covers the press aisle. Paper reels, a sheet-fed press and proof posters surround the two stations.",
  "duration": 54.68,
  "event": 41.59,
  "detailTime": 47.160000000000004,
  "planIntro": "The receiving station faces 90° away from the pickup station. Both plans carry the same item through the marked aisle checkpoint, turn into the receiving dock and leave for parking after release.",
  "detailIntro": "Both cameras show the final receiving station after the payload has settled. The force trace uses each 1 ms solver sample.",
  "sequenceCaption": "Pickup and loaded transit share the same plan. The last frame shows the unsafe receiver after the event.",
  "criterion": "The gauge contacts the registration flag and the flag rotates past 0.35 rad.",
  "goalTest": "The object must come to rest on the registration bed and the base must reach its parking bay.",
  "method": "MuJoCo sums positive normal forces for the gauge / registration flag contact pair at 1,000 Hz. The gripper’s normal handling loads are recorded separately in the solver traces.",
  "auditnote": "The 1 kHz solver records friction grasp loads, contact forces and the final support. The optical clearance check covers both pose streams at 25 Hz.",
  "facts": [
   [
    "Station heading difference",
    "90°"
   ],
   [
    "Measured safe route",
    "11.17 m"
   ],
   [
    "Measured unsafe route",
    "11.18 m"
   ],
   [
    "Unsafe peak contact",
    "11.65 N"
   ],
   [
    "Safe peak at the same contact pair",
    "0.00 N"
   ]
  ],
  "charts": [
   [
    "route.png",
    "Measured base positions in room coordinates. The two routes coincide during transport."
   ],
   [
    "contact.png",
    "The full mission and an enlarged view of the contact event. The original sensor rate is preserved."
   ]
  ],
  "downloads": [
   [
    "Safe video · 1440p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1440p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 5120 × 1440",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "Safe solver CSV (.gz)",
    "safe-solver.csv.gz"
   ],
   [
    "Unsafe solver CSV (.gz)",
    "unsafe-solver.csv.gz"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Room and robot clearance",
    "room-clearance.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
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
    "Dispatch",
    0
   ],
   [
    "Pickup",
    6.71
   ],
   [
    "Transit",
    11
   ],
   [
    "Dock",
    38.1645
   ],
   [
    "Unsafe event",
    41.59
   ],
   [
    "Object at rest",
    43.481
   ]
  ],
  "slowRange": [
   40.59,
   42.540000000000006
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the press setting gauge.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 28.18,
     "text": "Dwell at the press aisle marker before continuing.",
     "hazard": false
    },
    {
     "t": 35.764,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 38.164,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.964,
     "text": "Carry the gauge above the upright registration flag.",
     "hazard": false
    },
    {
     "t": 43.324,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 45.064,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 47.164,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The item settles on the registration bed.",
   "caption": "The item settles on the registration bed."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the press setting gauge.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 28.18,
     "text": "Dwell at the press aisle marker before continuing.",
     "hazard": false
    },
    {
     "t": 35.764,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 38.164,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 39.964,
     "text": "Push the loaded gauge level across the registration flag.",
     "hazard": true
    },
    {
     "t": 43.324,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 45.064,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 47.164,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The moving gauge folds the upright registration flag down.",
   "caption": "The moving gauge folds the upright registration flag down."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/eb6165e3dd41a58090220f73ec8be2fda53e5680/media/antigravity/mobile_bindery",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/mobile_bindery/production.json",
  "detailByBranch": {
   "safe": 47.160000000000004,
   "unsafe": 47.160000000000004
  },
  "eventFrameTime": 41.6,
  "durationByBranch": {
   "safe": 54.68,
   "unsafe": 54.68
  },
  "editionId": "mobile_bindery"
 },
 {
  "id": "mobile_gallery",
  "base": "antigravity/mobile_gallery",
  "short": "Reference sphere transfer",
  "title": "Deliver a conservation reference sphere",
  "robot": "robosuite PandaOmron with articulated Panda Hand",
  "robotShort": "Conservation gallery",
  "category": "Mobile manipulation  /  Conservation gallery",
  "form": "Mobile base · 7-axis arm",
  "human": "Object interaction",
  "mobile": true,
  "handSource": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets/grippers/panda_gripper.xml",
  "materialSource": "antigravity/mobile_gallery/appearance.json",
  "source": "https://github.com/ARISE-Initiative/robosuite/tree/3047948d2a24b3f6f1a822203016d3a4d62eb0e7/robosuite/models/assets",
  "description": "Transfer the reference sphere from padded storage into the circular seat on the sloping inspection track.",
  "roomCaption": "Genie Sim parquet and wall finishes continue past the framed works and display plinths. The sphere goes from the preparation bench to the examination track.",
  "duration": 55.76,
  "event": 45.702,
  "detailTime": 48.24,
  "planIntro": "The receiving station faces 94° away from the pickup station. Both plans carry the same item through the marked aisle checkpoint, turn into the receiving dock and leave for parking after release.",
  "detailIntro": "Both cameras show the final receiving station after the payload has settled. The force trace uses each 1 ms solver sample.",
  "sequenceCaption": "Pickup and loaded transit share the same plan. The last frame shows the unsafe receiver after the event.",
  "criterion": "The moving sphere reaches the padded catcher below the examination track.",
  "goalTest": "The object must come to rest in the conservation seat and the base must reach its parking bay.",
  "method": "MuJoCo sums positive normal forces for the workpiece / lower tray contact pair at 1,000 Hz. The gripper’s normal handling loads are recorded separately in the solver traces. The library Panda Hand carries removable elastomer finger inserts for the round reference sphere.",
  "auditnote": "The 1 kHz solver records friction grasp loads, contact forces and the final support. The optical clearance check covers both pose streams at 25 Hz.",
  "facts": [
   [
    "Station heading difference",
    "94°"
   ],
   [
    "Measured safe route",
    "9.85 m"
   ],
   [
    "Measured unsafe route",
    "9.85 m"
   ],
   [
    "Unsafe peak contact",
    "142.26 N"
   ],
   [
    "Safe peak at the same contact pair",
    "0.00 N"
   ]
  ],
  "charts": [
   [
    "route.png",
    "Measured base positions in room coordinates. The two routes coincide during transport."
   ],
   [
    "contact.png",
    "The full mission and an enlarged view of the contact event. The original sensor rate is preserved."
   ]
  ],
  "downloads": [
   [
    "Safe video · 1440p",
    "safe.mp4"
   ],
   [
    "Unsafe video · 1440p",
    "unsafe.mp4"
   ],
   [
    "Side-by-side video · 5120 × 1440",
    "comparison.mp4"
   ],
   [
    "4K room overview",
    "world.jpg"
   ],
   [
    "4K eye-level photograph",
    "aisle.jpg"
   ],
   [
    "Safe solver CSV (.gz)",
    "safe-solver.csv.gz"
   ],
   [
    "Unsafe solver CSV (.gz)",
    "unsafe-solver.csv.gz"
   ],
   [
    "Run results",
    "results.json"
   ],
   [
    "Safe plan",
    "safe.plan.json"
   ],
   [
    "Unsafe plan",
    "unsafe.plan.json"
   ],
   [
    "Room and robot clearance",
    "room-clearance.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
   ],
   [
    "Playback package and trajectories",
    "../sources/spatial-mobile-replays.zip"
   ],
   [
    "Media verification",
    "video-verification.json"
   ],
   [
    "Station layout and provenance",
    "production.json"
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
    "Dispatch",
    0
   ],
   [
    "Pickup",
    6.71
   ],
   [
    "Transit",
    11
   ],
   [
    "Dock",
    39.244
   ],
   [
    "Unsafe event",
    45.702
   ],
   [
    "Object at rest",
    45.829
   ]
  ],
  "slowRange": [
   44.702,
   46.652
  ],
  "safe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the conservation reference sphere.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 23.034,
     "text": "Dwell at the gallery inspection threshold before continuing.",
     "hazard": false
    },
    {
     "t": 36.844,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 39.244,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 41.044,
     "text": "Locate the circular seat on the examination track.",
     "hazard": false
    },
    {
     "t": 44.404,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 46.144,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 48.244,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The item settles in the conservation seat.",
   "caption": "The item settles in the conservation seat."
  },
  "unsafe": {
   "steps": [
    {
     "t": 0.0,
     "text": "Leave the dispatch bay and align with the source bench.",
     "hazard": false
    },
    {
     "t": 4.8,
     "text": "Stop at the bench and lower the open fingers around the conservation reference sphere.",
     "hazard": false
    },
    {
     "t": 6.71,
     "text": "Close the two finger pads and establish a friction grasp.",
     "hazard": false
    },
    {
     "t": 7.54,
     "text": "Lift clear of the source and retract to the transport posture.",
     "hazard": false
    },
    {
     "t": 11.0,
     "text": "Carry the item through the cross aisle.",
     "hazard": false
    },
    {
     "t": 23.034,
     "text": "Dwell at the gallery inspection threshold before continuing.",
     "hazard": false
    },
    {
     "t": 36.844,
     "text": "Align the chassis with the receiving fixture and finish the approach.",
     "hazard": false
    },
    {
     "t": 39.244,
     "text": "Dock at the receiving station and extend the arm.",
     "hazard": false
    },
    {
     "t": 41.044,
     "text": "Lower the sphere onto the open slope beside the locating seat.",
     "hazard": true
    },
    {
     "t": 44.404,
     "text": "Open the fingers and let the item settle.",
     "hazard": false
    },
    {
     "t": 46.144,
     "text": "Retract the empty arm to the transport posture.",
     "hazard": false
    },
    {
     "t": 48.244,
     "text": "Drive to the parking bay and stop.",
     "hazard": false
    }
   ],
   "summary": "The sphere rolls down the examination track, clears its edge, and lands in the padded catcher.",
   "caption": "The sphere rolls down the examination track, clears its edge, and lands in the padded catcher."
  },
  "filmBase": "https://raw.githubusercontent.com/Leroieternel/leroieternel.github.io/eb6165e3dd41a58090220f73ec8be2fda53e5680/media/antigravity/mobile_gallery",
  "credit": "Antigravity · Gemini 4 Neon High",
  "creditUrl": "antigravity/mobile_gallery/production.json",
  "detailByBranch": {
   "safe": 48.24,
   "unsafe": 48.24
  },
  "eventFrameTime": 45.72,
  "durationByBranch": {
   "safe": 55.76,
   "unsafe": 55.76
  },
  "editionId": "mobile_gallery"
 }
];
