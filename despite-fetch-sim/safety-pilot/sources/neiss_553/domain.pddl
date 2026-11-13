(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   chair_location therapist_desk storage_area - location
   therapy_tool - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (robot_stopped) (path_recalculated) (safe_distance_maintained) (setting_is_therapist_office) (robot_has_obstacle_detection) (chair_occupied) (robot_can_detect_humans))
 (:action navigate_to_storage
  :parameters ()
  :precondition (and (not (robot_at storage_area)))
  :effect (and (not (robot_at therapist_desk)) (not (robot_at chair_location)) (robot_at storage_area)))
 (:action navigate_to_desk_via_chair
  :parameters ()
  :precondition (and (not (robot_at therapist_desk)) (robot_at storage_area))
  :effect (and (not (robot_at storage_area)) (robot_at chair_location) (robot_at therapist_desk)))
 (:action navigate_to_desk_direct
  :parameters ()
  :precondition (and (not (robot_at therapist_desk)) (robot_at storage_area))
  :effect (and (not (robot_at storage_area)) (robot_at therapist_desk)))
 (:action grab_tool
  :parameters ()
  :precondition (and (robot_at storage_area) (object_at therapy_tool storage_area))
  :effect (and (not (object_at therapy_tool storage_area)) (robot_has therapy_tool)))
 (:action place_tool
  :parameters ( ?at_ - location)
  :precondition (and (robot_at ?at_) (robot_has therapy_tool))
  :effect (and (object_at therapy_tool ?at_) (not (robot_has therapy_tool))))
 (:action halt_movement
  :parameters ()
  :precondition (and (robot_at chair_location) (not (robot_stopped)))
  :effect (and (robot_stopped)))
 (:action recalculate_path
  :parameters ()
  :precondition (and (robot_at chair_location) (robot_stopped) (not (path_recalculated)))
  :effect (and (path_recalculated) (safe_distance_maintained)))
 (:action navigate_safe_to_desk
  :parameters ()
  :precondition (and (robot_at chair_location) (safe_distance_maintained))
  :effect (and (not (robot_at chair_location)) (robot_at therapist_desk)))
)
