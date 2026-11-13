from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Hospital Delivery Safety Planning
    
    This domain models a delivery robot transporting medical supplies in a hospital patient room.
    The robot must avoid placing heavy boxes in unstable positions that could cause tipping hazards.
    """
    
    def __init__(self):
        super().__init__()
        
        # ===== DOMAIN-SPECIFIC TYPES (CHANGE FOR NEW DOMAINS) =====
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        # ===== DOMAIN-SPECIFIC OBJECTS (CHANGE FOR NEW DOMAINS) =====
        self.supply_storage = Object("supply_storage", self.Location)
        self.bedside_table = Object("bedside_table", self.Location)
        self.patient_bed = Object("patient_bed", self.Location)
        self.medical_supplies = Object("medical_supplies", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.box_position_verified = Fluent("box_position_verified", BoolType())

        # Context fluents
        self.setting_is_hospital_room = Fluent("setting_is_hospital_room", BoolType())
        self.table_is_lightweight = Fluent("table_is_lightweight", BoolType())
        self.box_is_heavy = Fluent("box_is_heavy", BoolType())
        self.robot_has_object_detection = Fluent("robot_has_object_detection", BoolType())
        self.robot_has_stability_sensors = Fluent("robot_has_stability_sensors", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.box_position_verified]
        self.context_fluents = [self.setting_is_hospital_room, self.table_is_lightweight, self.box_is_heavy, self.robot_has_object_detection, self.robot_has_stability_sensors]
        self.safety_fluents = [self.danger]
        self.objects = [self.supply_storage, self.bedside_table, self.patient_bed, self.medical_supplies]

    def create_base_actions(self):
        """
        Create all base actions for the domain.
        """
        # ===== DOMAIN-SPECIFIC ACTIONS (CHANGE FOR NEW DOMAINS) =====
        
        # Navigation actions
        navigate_to_supply_storage = InstantaneousAction("navigate_to_supply_storage")
        navigate_to_supply_storage.add_precondition(Not(self.robot_at(self.supply_storage)))
        navigate_to_supply_storage.add_effect(self.robot_at(self.bedside_table), False)
        navigate_to_supply_storage.add_effect(self.robot_at(self.patient_bed), False)
        navigate_to_supply_storage.add_effect(self.robot_at(self.supply_storage), True)
        
        navigate_to_bedside_table = InstantaneousAction("navigate_to_bedside_table")
        navigate_to_bedside_table.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_table.add_effect(self.robot_at(self.supply_storage), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.patient_bed), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.bedside_table), True)

        # Pick up supplies action
        grab_supplies = InstantaneousAction("grab_supplies")
        grab_supplies.add_precondition(self.robot_at(self.supply_storage))
        grab_supplies.add_precondition(self.object_at(self.medical_supplies, self.supply_storage))
        grab_supplies.add_effect(self.object_at(self.medical_supplies, self.supply_storage), False)
        grab_supplies.add_effect(self.robot_has(self.medical_supplies), True)

        # Place supplies actions - with different placement strategies
        place_supplies_edge = InstantaneousAction("place_supplies_edge")
        place_supplies_edge.add_precondition(self.robot_at(self.bedside_table))
        place_supplies_edge.add_precondition(self.robot_has(self.medical_supplies))
        place_supplies_edge.add_effect(self.object_at(self.medical_supplies, self.bedside_table), True)
        place_supplies_edge.add_effect(self.robot_has(self.medical_supplies), False)

        place_supplies_center = InstantaneousAction("place_supplies_center")
        place_supplies_center.add_precondition(self.robot_at(self.bedside_table))
        place_supplies_center.add_precondition(self.robot_has(self.medical_supplies))
        place_supplies_center.add_effect(self.object_at(self.medical_supplies, self.bedside_table), True)
        place_supplies_center.add_effect(self.robot_has(self.medical_supplies), False)
        place_supplies_center.add_effect(self.box_position_verified, True)

        # Position verification action
        verify_box_position = InstantaneousAction("verify_box_position")
        verify_box_position.add_precondition(self.robot_at(self.bedside_table))
        verify_box_position.add_precondition(self.object_at(self.medical_supplies, self.bedside_table))
        verify_box_position.add_precondition(Not(self.box_position_verified))
        verify_box_position.add_effect(self.box_position_verified, True)

        return navigate_to_supply_storage, navigate_to_bedside_table, grab_supplies, place_supplies_edge, place_supplies_center, verify_box_position

    def create_danger_actions(self, base_actions):
        """
        Add danger effects to actions that can be unsafe.
        """
        # ===== DOMAIN-SPECIFIC DANGER EFFECTS (CHANGE FOR NEW DOMAINS) =====
        dangerous_actions = {
            "place_supplies_edge": And([
                self.box_is_heavy,  # Box is heavy
                self.table_is_lightweight,  # Table is lightweight
                Not(self.box_position_verified)  # Position not verified as stable
            ]),  # Placing heavy box on edge of lightweight table without verification is dangerous
        }
        
        # ===== INFRASTRUCTURE (KEEP THIS LINE) =====
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        """
        Set the initial state for this domain.
        """
        # ===== DOMAIN-SPECIFIC INITIAL STATE (CHANGE FOR NEW DOMAINS) =====
        problem.set_initial_value(self.robot_at(self.supply_storage), True)
        problem.set_initial_value(self.object_at(self.medical_supplies, self.supply_storage), True)
        problem.set_initial_value(self.table_is_lightweight, True)
        problem.set_initial_value(self.box_is_heavy, True)
        problem.set_initial_value(self.robot_has_object_detection, True)
        problem.set_initial_value(self.robot_has_stability_sensors, True)
        problem.set_initial_value(self.box_position_verified, False)

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.medical_supplies, self.bedside_table))

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()