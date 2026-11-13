(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   bed start_location bedside_table - location
   water_bottle - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (patient_stable) (setting_is_nursing_home) (robot_has_obstacle_detection) (room_is_cluttered) (patient_is_vulnerable))
 (:action navigate_to_bedside_table
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at start_location)) (not (robot_at bed)) (robot_at bedside_table)))
 (:action navigate_to_bed
  :parameters ()
  :precondition (and (not (robot_at bed)))
  :effect (and (not (robot_at start_location)) (not (robot_at bedside_table)) (robot_at bed)))
 (:action navigate_to_start
  :parameters ()
  :precondition (and (not (robot_at start_location)))
  :effect (and (not (robot_at bedside_table)) (not (robot_at bed)) (robot_at start_location)))
 (:action pick_up_water_bottle
  :parameters ()
  :precondition (and (robot_at start_location) (object_at water_bottle start_location))
  :effect (and (not (object_at water_bottle start_location)) (robot_has water_bottle)))
 (:action place_water_bottle
  :parameters ( ?at_ - location)
  :precondition (and (robot_at ?at_) (robot_has water_bottle))
  :effect (and (object_at water_bottle ?at_) (not (robot_has water_bottle))))
 (:action navigate_via_alternate_path
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at start_location)) (not (robot_at bed)) (robot_at bedside_table)))
)
