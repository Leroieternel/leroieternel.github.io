(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at sponge_storage) (object_at sponge sponge_storage) (object_at pump_bottle pump_bottle_area) (pump_bottle_contains_liquid) (pump_bottle_unstable) (robot_has_sensors))
 (:goal (and (object_at sponge toilet_tank)))
)
