(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at storage_area) (object_at therapy_tool storage_area) (chair_occupied) (robot_has_obstacle_detection) (robot_can_detect_humans))
 (:goal (and (object_at therapy_tool therapist_desk)))
)
