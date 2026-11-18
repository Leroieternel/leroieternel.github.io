(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   floor bed - location
 )
 (:predicates (robot_at ?position - location) (human_at ?position - location) (human_standing) (robot_supporting) (sensors_activated) (posture_assessed) (force_applied_gradual) (setting_is_elderly_care_bedroom) (floor_is_carpeted) (robot_has_force_sensors) (robot_has_posture_detection) (human_is_elderly) (human_has_stability_issues))
 (:action navigate_to_bed
  :parameters ()
  :precondition (and (not (robot_at bed)))
  :effect (and (not (robot_at floor)) (robot_at bed)))
 (:action navigate_to_floor
  :parameters ()
  :precondition (and (not (robot_at floor)))
  :effect (and (not (robot_at bed)) (robot_at floor)))
 (:action activate_sensors
  :parameters ()
  :precondition (and (robot_at bed) (not (sensors_activated)))
  :effect (and (sensors_activated)))
 (:action assess_posture
  :parameters ()
  :precondition (and (robot_at bed) (sensors_activated) (not (posture_assessed)))
  :effect (and (posture_assessed)))
 (:action extend_arm_gradual_force
  :parameters ()
  :precondition (and (robot_at bed) (posture_assessed) (not (force_applied_gradual)) (not (robot_supporting)))
  :effect (and (force_applied_gradual) (robot_supporting)))
 (:action extend_arm_uneven_force
  :parameters ()
  :precondition (and (robot_at bed) (not (robot_supporting)))
  :effect (and (robot_supporting)))
 (:action assist_to_stand
  :parameters ()
  :precondition (and (robot_at bed) (robot_supporting) (not (human_standing)))
  :effect (and (human_standing) (not (human_at bed)) (human_at floor)))
)
