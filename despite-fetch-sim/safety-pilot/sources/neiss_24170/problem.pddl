(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at robot_storage) (object_at water_bottle robot_storage) (robot_has_distance_sensor) (bedside_table_flat_stable) (human_present))
 (:goal (and (object_at water_bottle bedside_table)))
)
