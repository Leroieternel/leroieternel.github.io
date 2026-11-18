(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
   human - objecttype
 )
 (:init (robot_at storage_room) (object_at medical_supplies storage_room) (human_at corridor) (robot_has_basic_sensors) (human_moves_slowly) (supply_box_is_heavy))
 (:goal (and (object_at medical_supplies patient_room)))
)
