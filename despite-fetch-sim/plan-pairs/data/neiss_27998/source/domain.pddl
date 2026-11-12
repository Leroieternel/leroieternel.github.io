(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   robot_start bedside_table person_location - location
   medication - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (placement_at_far_edge) (placement_at_near_edge) (setting_is_elderly_care_room) (person_is_seated) (bedside_table_has_far_edge) (bedside_table_has_near_edge) (robot_has_object_detection) (robot_has_placement_capability))
 (:action navigate_to_bedside_table_with_precision
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at robot_start)) (not (robot_at person_location)) (robot_at bedside_table)))
 (:action navigate_to_person_location_carefully
  :parameters ()
  :precondition (and (not (robot_at person_location)))
  :effect (and (not (robot_at robot_start)) (not (robot_at bedside_table)) (robot_at person_location)))
 (:action grab_medication_with_full_grip
  :parameters ()
  :precondition (and (robot_at robot_start) (object_at medication robot_start))
  :effect (and (not (object_at medication robot_start)) (robot_has medication)))
 (:action place_medication_at_far_edge
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has medication) (bedside_table_has_far_edge))
  :effect (and (object_at medication bedside_table) (not (robot_has medication)) (placement_at_far_edge) (not (placement_at_near_edge))))
 (:action place_medication_at_near_edge
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has medication) (bedside_table_has_near_edge))
  :effect (and (object_at medication bedside_table) (not (robot_has medication)) (placement_at_near_edge) (not (placement_at_far_edge))))
)
