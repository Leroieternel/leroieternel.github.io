(define (problem basic-problem)
 (:domain basic-domain)
 (:objects
 )
 (:init (robot_at customer_area) (object_at object_from_customer customer_area) (human_offering) (setting_is_bank_lobby) (object_looks_like_money) (other_customers_present) (robot_can_detect_handoff))
 (:goal (and (object_at object_from_customer storage_area)))
)
