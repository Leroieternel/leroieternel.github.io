(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   toilet_tank pump_bottle_area sponge_storage - location
   sponge pump_bottle - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (pump_bottle_detected) (setting_is_bathroom) (pump_bottle_contains_liquid) (pump_bottle_unstable) (robot_has_sensors))
 (:action navigate_to_sponge_storage
  :parameters ()
  :precondition (and (not (robot_at sponge_storage)))
  :effect (and (not (robot_at toilet_tank)) (not (robot_at pump_bottle_area)) (robot_at sponge_storage)))
 (:action navigate_to_toilet_tank
  :parameters ()
  :precondition (and (not (robot_at toilet_tank)))
  :effect (and (not (robot_at sponge_storage)) (not (robot_at pump_bottle_area)) (robot_at toilet_tank)))
 (:action navigate_to_pump_bottle_area
  :parameters ()
  :precondition (and (not (robot_at pump_bottle_area)))
  :effect (and (not (robot_at sponge_storage)) (not (robot_at toilet_tank)) (robot_at pump_bottle_area)))
 (:action grab_sponge
  :parameters ()
  :precondition (and (robot_at sponge_storage) (object_at sponge sponge_storage))
  :effect (and (not (object_at sponge sponge_storage)) (robot_has sponge)))
 (:action place_sponge
  :parameters ( ?at_ - location)
  :precondition (and (robot_at ?at_) (robot_has sponge))
  :effect (and (object_at sponge ?at_) (not (robot_has sponge))))
 (:action detect_pump_bottle
  :parameters ()
  :precondition (and (robot_at pump_bottle_area) (robot_has_sensors) (object_at pump_bottle pump_bottle_area))
  :effect (and (pump_bottle_detected)))
)
