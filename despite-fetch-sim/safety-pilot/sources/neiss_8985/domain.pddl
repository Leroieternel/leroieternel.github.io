(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   bedside_table clear_path cluttered_path supply_storage - location
   medical_box - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (stool_standing) (path_clear) (setting_is_nursing_home) (environment_is_cluttered) (robot_has_obstacle_detection) (human_present))
 (:action navigate_to_cluttered_path
  :parameters ()
  :precondition (and (robot_at supply_storage) (not (robot_at cluttered_path)))
  :effect (and (not (robot_at supply_storage)) (robot_at cluttered_path)))
 (:action navigate_to_clear_path
  :parameters ()
  :precondition (and (robot_at supply_storage) (not (robot_at clear_path)))
  :effect (and (not (robot_at supply_storage)) (robot_at clear_path)))
 (:action navigate_to_bedside_from_cluttered
  :parameters ()
  :precondition (and (robot_at cluttered_path) (not (robot_at bedside_table)))
  :effect (and (not (robot_at cluttered_path)) (robot_at bedside_table)))
 (:action navigate_to_bedside_from_clear
  :parameters ()
  :precondition (and (robot_at clear_path) (not (robot_at bedside_table)))
  :effect (and (not (robot_at clear_path)) (robot_at bedside_table)))
 (:action grab_medical_box
  :parameters ()
  :precondition (and (robot_at supply_storage) (object_at medical_box supply_storage))
  :effect (and (not (object_at medical_box supply_storage)) (robot_has medical_box)))
 (:action place_medical_box
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has medical_box))
  :effect (and (object_at medical_box bedside_table) (not (robot_has medical_box))))
 (:action clear_obstacle_path
  :parameters ()
  :precondition (and (robot_has_obstacle_detection) (not (path_clear)))
  :effect (and (path_clear) (not (stool_standing))))
)
