(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at counter) (object_at hot_liquid counter) (liquid_is_hot) (humans_present) (robot_has_tilt_sensors) (obstacles_present) (obstacle_navigation_required))
 (:goal (and (object_at hot_liquid table)))
)
