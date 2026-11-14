(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at robot_storage) (object_at water_bottle robot_storage) (setting_is_nursing_home) (robot_has_sensors) (table_is_stable) (table_is_uncluttered))
 (:goal (and (object_at water_bottle bedside_table)))
)
