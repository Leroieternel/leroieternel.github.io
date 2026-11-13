(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   bedside_table robot_start - location
   water_bottle - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (bottle_centered) (placement_verified) (setting_is_bedroom) (table_has_clear_space) (robot_has_object_detection) (robot_has_placement_capability))
 (:action navigate_to_bedside_table
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at robot_start)) (robot_at bedside_table)))
 (:action grab_water_bottle
  :parameters ()
  :precondition (and (robot_at robot_start) (object_at water_bottle robot_start))
  :effect (and (not (object_at water_bottle robot_start)) (robot_has water_bottle)))
 (:action place_water_bottle
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has water_bottle))
  :effect (and (object_at water_bottle bedside_table) (not (robot_has water_bottle))))
 (:action verify_placement
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has water_bottle) (table_has_clear_space) (robot_has_object_detection))
  :effect (and (placement_verified)))
)
