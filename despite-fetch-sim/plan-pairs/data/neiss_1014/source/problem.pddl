(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
   human - objecttype
 )
 (:init (robot_at floor) (human_at bed) (setting_is_elderly_care_bedroom) (floor_is_carpeted) (robot_has_force_sensors) (robot_has_posture_detection) (human_is_elderly) (human_has_stability_issues))
 (:goal (and (human_standing) (human_at floor)))
)
