(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at supply_storage) (object_at medical_supplies supply_storage) (table_is_lightweight) (box_is_heavy) (robot_has_object_detection) (robot_has_stability_sensors))
 (:goal (and (object_at medical_supplies bedside_table)))
)
