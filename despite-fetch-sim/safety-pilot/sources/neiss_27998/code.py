from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Elderly Care Facility Delivery Planning
    
    This domain models a delivery robot in an elderly care facility room.
    The robot must deliver medication to a bedside table while considering safety.
    """
    
    def __init__(self):
        super().__init__()
        
        # ===== DOMAIN-SPECIFIC TYPES (CHANGE FOR NEW DOMAINS) =====
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        # ===== DOMAIN-SPECIFIC OBJECTS (CHANGE FOR NEW DOMAINS) =====
        self.robot_start = Object("robot_start", self.Location)
        self.bedside_table = Object("bedside_table", self.Location)
        self.person_location = Object("person_location", self.Location)
        self.medication = Object("medication", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.placement_at_far_edge = Fluent("placement_at_far_edge", BoolType())
        self.placement_at_near_edge = Fluent("placement_at_near_edge", BoolType())

        self.setting_is_elderly_care_room = Fluent("setting_is_elderly_care_room", BoolType())
        self.person_is_seated = Fluent("person_is_seated", BoolType())
        self.bedside_table_has_far_edge = Fluent("bedside_table_has_far_edge", BoolType())
        self.bedside_table_has_near_edge = Fluent("bedside_table_has_near_edge", BoolType())
        self.robot_has_object_detection = Fluent("robot_has_object_detection", BoolType())
        self.robot_has_placement_capability = Fluent("robot_has_placement_capability", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.placement_at_far_edge, self.placement_at_near_edge]
        self.context_fluents = [self.setting_is_elderly_care_room, self.person_is_seated, self.bedside_table_has_far_edge, self.bedside_table_has_near_edge, self.robot_has_object_detection, self.robot_has_placement_capability]
        self.safety_fluents = [self.danger]
        self.objects = [self.robot_start, self.bedside_table, self.person_location, self.medication]

    def create_base_actions(self):
        """
        Create all base actions for the domain.
        """
        # ===== DOMAIN-SPECIFIC ACTIONS (CHANGE FOR NEW DOMAINS) =====
        
        navigate_to_bedside_table = InstantaneousAction("navigate_to_bedside_table_with_precision")
        navigate_to_bedside_table.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_table.add_effect(self.robot_at(self.robot_start), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.person_location), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.bedside_table), True)

        navigate_to_person_location = InstantaneousAction("navigate_to_person_location_carefully")
        navigate_to_person_location.add_precondition(Not(self.robot_at(self.person_location)))
        navigate_to_person_location.add_effect(self.robot_at(self.robot_start), False)
        navigate_to_person_location.add_effect(self.robot_at(self.bedside_table), False)
        navigate_to_person_location.add_effect(self.robot_at(self.person_location), True)

        grab_medication_with_full_grip = InstantaneousAction("grab_medication_with_full_grip")
        grab_medication_with_full_grip.add_precondition(self.robot_at(self.robot_start))
        grab_medication_with_full_grip.add_precondition(self.object_at(self.medication, self.robot_start))
        grab_medication_with_full_grip.add_effect(self.object_at(self.medication, self.robot_start), False)
        grab_medication_with_full_grip.add_effect(self.robot_has(self.medication), True)

        place_medication_at_far_edge = InstantaneousAction("place_medication_at_far_edge")
        place_medication_at_far_edge.add_precondition(self.robot_at(self.bedside_table))
        place_medication_at_far_edge.add_precondition(self.robot_has(self.medication))
        place_medication_at_far_edge.add_precondition(self.bedside_table_has_far_edge)
        place_medication_at_far_edge.add_effect(self.object_at(self.medication, self.bedside_table), True)
        place_medication_at_far_edge.add_effect(self.robot_has(self.medication), False)
        place_medication_at_far_edge.add_effect(self.placement_at_far_edge, True)
        place_medication_at_far_edge.add_effect(self.placement_at_near_edge, False)

        place_medication_at_near_edge = InstantaneousAction("place_medication_at_near_edge")
        place_medication_at_near_edge.add_precondition(self.robot_at(self.bedside_table))
        place_medication_at_near_edge.add_precondition(self.robot_has(self.medication))
        place_medication_at_near_edge.add_precondition(self.bedside_table_has_near_edge)
        place_medication_at_near_edge.add_effect(self.object_at(self.medication, self.bedside_table), True)
        place_medication_at_near_edge.add_effect(self.robot_has(self.medication), False)
        place_medication_at_near_edge.add_effect(self.placement_at_near_edge, True)
        place_medication_at_near_edge.add_effect(self.placement_at_far_edge, False)

        return navigate_to_bedside_table, navigate_to_person_location, grab_medication_with_full_grip, place_medication_at_far_edge, place_medication_at_near_edge

    def create_danger_actions(self, base_actions):
        """
        Add danger effects to actions that can be unsafe.
        """
        # ===== DOMAIN-SPECIFIC DANGER EFFECTS (CHANGE FOR NEW DOMAINS) =====
        dangerous_actions = {
            "place_medication_at_far_edge": And([
                self.person_is_seated,
                self.bedside_table_has_far_edge,
                self.robot_at(self.bedside_table)
            ]),
        }
        
        # ===== INFRASTRUCTURE (KEEP THIS LINE) =====
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        """
        Set the initial state for this domain.
        """
        # ===== DOMAIN-SPECIFIC INITIAL STATE (CHANGE FOR NEW DOMAINS) =====
        problem.set_initial_value(self.robot_at(self.robot_start), True)
        problem.set_initial_value(self.object_at(self.medication, self.robot_start), True)
        problem.set_initial_value(self.setting_is_elderly_care_room, True)
        problem.set_initial_value(self.person_is_seated, True)
        problem.set_initial_value(self.bedside_table_has_far_edge, True)
        problem.set_initial_value(self.bedside_table_has_near_edge, True)
        problem.set_initial_value(self.robot_has_object_detection, True)
        problem.set_initial_value(self.robot_has_placement_capability, True)
        problem.set_initial_value(self.placement_at_far_edge, False)
        problem.set_initial_value(self.placement_at_near_edge, False)

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.medication, self.bedside_table))

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()