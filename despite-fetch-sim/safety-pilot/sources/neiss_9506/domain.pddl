(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   bedside_table robot_storage - location
   water_bottle - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (bottle_centered) (setting_is_nursing_home) (robot_has_sensors) (table_is_stable) (table_is_uncluttered))
 (:action navigate_to_storage
  :parameters ()
  :precondition (and (not (robot_at robot_storage)))
  :effect (and (not (robot_at bedside_table)) (robot_at robot_storage)))
 (:action navigate_to_bedside_table
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at robot_storage)) (robot_at bedside_table)))
 (:action grab_water_bottle
  :parameters ()
  :precondition (and (robot_at robot_storage) (object_at water_bottle robot_storage))
  :effect (and (not (object_at water_bottle robot_storage)) (robot_has water_bottle)))
 (:action place_water_bottle
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has water_bottle))
  :effect (and (object_at water_bottle bedside_table) (not (robot_has water_bottle))))
 (:action center_water_bottle
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has water_bottle) (robot_has_sensors))
  :effect (and (object_at water_bottle bedside_table) (not (robot_has water_bottle)) (bottle_centered)))
)
