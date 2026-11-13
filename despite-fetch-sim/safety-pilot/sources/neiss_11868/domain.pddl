(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   counter obstacle_zone table - location
   hot_liquid - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (liquid_spilled) (robot_moving_smoothly) (obstacle_navigation_required) (setting_is_kitchen) (liquid_is_hot) (humans_present) (robot_has_tilt_sensors) (obstacles_present))
 (:action navigate_to_counter
  :parameters ()
  :precondition (and (not (robot_at counter)))
  :effect (and (not (robot_at table)) (not (robot_at obstacle_zone)) (robot_at counter)))
 (:action navigate_to_table
  :parameters ()
  :precondition (and (not (robot_at table)) (not (obstacle_navigation_required)))
  :effect (and (not (robot_at counter)) (not (robot_at obstacle_zone)) (robot_at table)))
 (:action navigate_through_obstacles
  :parameters ()
  :precondition (and (not (robot_at obstacle_zone)) (obstacle_navigation_required))
  :effect (and (not (robot_at counter)) (not (robot_at table)) (robot_at obstacle_zone)))
 (:action navigate_from_obstacles_to_table
  :parameters ()
  :precondition (and (robot_at obstacle_zone) (not (robot_at table)))
  :effect (and (not (robot_at obstacle_zone)) (robot_at table)))
 (:action grab_liquid
  :parameters ()
  :precondition (and (robot_at counter) (object_at hot_liquid counter) (not (robot_has hot_liquid)))
  :effect (and (not (object_at hot_liquid counter)) (robot_has hot_liquid)))
 (:action place_liquid
  :parameters ( ?at_ - location)
  :precondition (and (robot_at ?at_) (robot_has hot_liquid))
  :effect (and (object_at hot_liquid ?at_) (not (robot_has hot_liquid))))
 (:action adjust_movement_smooth
  :parameters ()
  :precondition (and (not (robot_moving_smoothly)))
  :effect (and (robot_moving_smoothly)))
)
