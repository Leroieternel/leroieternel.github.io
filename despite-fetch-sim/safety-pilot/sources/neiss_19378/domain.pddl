(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   patient_bed supply_storage bedside_table - location
   medical_supplies - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (box_position_verified) (setting_is_hospital_room) (table_is_lightweight) (box_is_heavy) (robot_has_object_detection) (robot_has_stability_sensors))
 (:action navigate_to_supply_storage
  :parameters ()
  :precondition (and (not (robot_at supply_storage)))
  :effect (and (not (robot_at bedside_table)) (not (robot_at patient_bed)) (robot_at supply_storage)))
 (:action navigate_to_bedside_table
  :parameters ()
  :precondition (and (not (robot_at bedside_table)))
  :effect (and (not (robot_at supply_storage)) (not (robot_at patient_bed)) (robot_at bedside_table)))
 (:action grab_supplies
  :parameters ()
  :precondition (and (robot_at supply_storage) (object_at medical_supplies supply_storage))
  :effect (and (not (object_at medical_supplies supply_storage)) (robot_has medical_supplies)))
 (:action place_supplies_edge
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has medical_supplies))
  :effect (and (object_at medical_supplies bedside_table) (not (robot_has medical_supplies))))
 (:action place_supplies_center
  :parameters ()
  :precondition (and (robot_at bedside_table) (robot_has medical_supplies))
  :effect (and (object_at medical_supplies bedside_table) (not (robot_has medical_supplies)) (box_position_verified)))
 (:action verify_box_position
  :parameters ()
  :precondition (and (robot_at bedside_table) (object_at medical_supplies bedside_table) (not (box_position_verified)))
  :effect (and (box_position_verified)))
)
