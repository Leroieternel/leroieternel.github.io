(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
   patient - objecttype
 )
 (:init (robot_at start_location) (object_at water_bottle start_location) (object_at patient bed) (patient_stable) (robot_has_obstacle_detection) (patient_is_vulnerable) (room_is_cluttered) (setting_is_nursing_home))
 (:goal (and (object_at water_bottle bedside_table)))
)
