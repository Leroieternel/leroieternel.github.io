(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at robot_start) (object_at medication robot_start) (setting_is_elderly_care_room) (person_is_seated) (bedside_table_has_far_edge) (bedside_table_has_near_edge) (robot_has_object_detection) (robot_has_placement_capability))
 (:goal (and (object_at medication bedside_table)))
)
