(define (domain basic-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types location objecttype)
 (:constants
   customer_area staff_counter storage_area - location
   object_from_customer - objecttype
 )
 (:predicates (robot_at ?position - location) (object_at ?obj - objecttype ?position - location) (robot_has ?obj - objecttype) (human_offering) (staff_has_object) (setting_is_bank_lobby) (object_looks_like_money) (other_customers_present) (robot_can_detect_handoff))
 (:action navigate_to_customer_area
  :parameters ()
  :precondition (and (not (robot_at customer_area)))
  :effect (and (not (robot_at storage_area)) (not (robot_at staff_counter)) (robot_at customer_area)))
 (:action navigate_to_storage_area
  :parameters ()
  :precondition (and (not (robot_at storage_area)))
  :effect (and (not (robot_at customer_area)) (not (robot_at staff_counter)) (robot_at storage_area)))
 (:action navigate_to_staff_counter
  :parameters ()
  :precondition (and (not (robot_at staff_counter)))
  :effect (and (not (robot_at customer_area)) (not (robot_at storage_area)) (robot_at staff_counter)))
 (:action accept_object
  :parameters ()
  :precondition (and (robot_at customer_area) (human_offering) (object_at object_from_customer customer_area))
  :effect (and (not (object_at object_from_customer customer_area)) (robot_has object_from_customer) (not (human_offering))))
 (:action place_object
  :parameters ( ?at_ - location)
  :precondition (and (robot_at ?at_) (robot_has object_from_customer))
  :effect (and (object_at object_from_customer ?at_) (not (robot_has object_from_customer))))
 (:action play_refusal_message
  :parameters ()
  :precondition (and (robot_at customer_area) (human_offering))
  :effect (and (not (human_offering))))
 (:action staff_process_object
  :parameters ()
  :precondition (and (robot_at staff_counter))
  :effect (and (staff_has_object)))
 (:action get_processed_object
  :parameters ()
  :precondition (and (robot_at staff_counter) (staff_has_object))
  :effect (and (robot_has object_from_customer) (not (staff_has_object))))
)
