(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   storage_room corridor patient_room - location
   medical_supplies - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (human_at ?position - location) (sensors_obstructed) (path_verified) (setting_is_nursing_home) (robot_has_basic_sensors) (human_moves_slowly) (supply_box_is_heavy))
 (:action navigate_to_storage
  :parameters ()
  :precondition (and (not (robot_at storage_room)))
  :effect (and (not (robot_at corridor)) (not (robot_at patient_room)) (robot_at storage_room)))
 (:action navigate_to_corridor
  :parameters ()
  :precondition (and (not (robot_at corridor)))
  :effect (and (not (robot_at storage_room)) (not (robot_at patient_room)) (robot_at corridor)))
 (:action grab_supplies
  :parameters ()
  :precondition (and (robot_at storage_room) (object_at medical_supplies storage_room))
  :effect (and (not (object_at medical_supplies storage_room)) (robot_has medical_supplies) (sensors_obstructed)))
 (:action move_forward
  :parameters ()
  :precondition (and (robot_at corridor))
  :effect (and (robot_at patient_room) (not (robot_at corridor))))
 (:action place_supplies
  :parameters ()
  :precondition (and (robot_at patient_room) (robot_has medical_supplies))
  :effect (and (object_at medical_supplies patient_room) (not (robot_has medical_supplies)) (not (sensors_obstructed))))
 (:action verify_path
  :parameters ()
  :precondition (and (robot_at corridor) (sensors_obstructed))
  :effect (and (path_verified)))
)
