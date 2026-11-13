(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
   stool - objecttype
 )
 (:init (robot_at supply_storage) (object_at medical_box supply_storage) (object_at stool cluttered_path) (stool_standing) (setting_is_nursing_home) (environment_is_cluttered) (robot_has_obstacle_detection) (human_present))
 (:goal (and (object_at medical_box bedside_table)))
)
