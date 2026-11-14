(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at robot_start) (object_at water_bottle robot_start) (table_has_clear_space) (robot_has_object_detection) (robot_has_placement_capability))
 (:goal (and (object_at water_bottle bedside_table)))
)
