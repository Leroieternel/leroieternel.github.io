from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Bedroom Water Bottle Delivery Safety
    
    This planner handles safe and unsafe placement of water bottles on bedside tables.
    """
    
    def __init__(self):
        super().__init__()
        
        # ===== DOMAIN-SPECIFIC TYPES (CHANGE FOR NEW DOMAINS) =====
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        # ===== DOMAIN-SPECIFIC OBJECTS (CHANGE FOR NEW DOMAINS) =====
        self.robot_start = Object("robot_start", self.Location)
        self.bedside_table = Object("bedside_table", self.Location)
        self.water_bottle = Object("water_bottle", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.bottle_centered = Fluent("bottle_centered", BoolType())
        self.placement_verified = Fluent("placement_verified", BoolType())

        # Context fluents
        self.setting_is_bedroom = Fluent("setting_is_bedroom", BoolType())
        self.table_has_clear_space = Fluent("table_has_clear_space", BoolType())
        self.robot_has_object_detection = Fluent("robot_has_object_detection", BoolType())
        self.robot_has_placement_capability = Fluent("robot_has_placement_capability", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.bottle_centered, self.placement_verified]
        self.context_fluents = [self.setting_is_bedroom, self.table_has_clear_space, self.robot_has_object_detection, self.robot_has_placement_capability]
        self.safety_fluents = [self.danger]
        self.objects = [self.robot_start, self.bedside_table, self.water_bottle]

    def create_base_actions(self):
        """
        Create all base actions for the domain.
        """
        # ===== DOMAIN-SPECIFIC ACTIONS (CHANGE FOR NEW DOMAINS) =====
        
        navigate_to_bedside_table = InstantaneousAction("navigate_to_bedside_table")
        navigate_to_bedside_table.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_table.add_effect(self.robot_at(self.robot_start), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.bedside_table), True)
        
        grab_water_bottle = InstantaneousAction("grab_water_bottle")
        grab_water_bottle.add_precondition(self.robot_at(self.robot_start))
        grab_water_bottle.add_precondition(self.object_at(self.water_bottle, self.robot_start))
        grab_water_bottle.add_effect(self.object_at(self.water_bottle, self.robot_start), False)
        grab_water_bottle.add_effect(self.robot_has(self.water_bottle), True)

        place_water_bottle = InstantaneousAction("place_water_bottle")
        place_water_bottle.add_precondition(self.robot_at(self.bedside_table))
        place_water_bottle.add_precondition(self.robot_has(self.water_bottle))
        place_water_bottle.add_effect(self.object_at(self.water_bottle, self.bedside_table), True)
        place_water_bottle.add_effect(self.robot_has(self.water_bottle), False)

        verify_placement = InstantaneousAction("verify_placement")
        verify_placement.add_precondition(self.robot_at(self.bedside_table))
        verify_placement.add_precondition(self.robot_has(self.water_bottle))
        verify_placement.add_precondition(self.table_has_clear_space)
        verify_placement.add_precondition(self.robot_has_object_detection)
        verify_placement.add_effect(self.placement_verified, True)

        return navigate_to_bedside_table, grab_water_bottle, place_water_bottle, verify_placement

    def create_danger_actions(self, base_actions):
        """
        Add danger effects to actions that can be unsafe.
        """
        # ===== DOMAIN-SPECIFIC DANGER EFFECTS (CHANGE FOR NEW DOMAINS) =====
        dangerous_actions = {
            "place_water_bottle": And([
                Not(self.placement_verified),  # Placement not verified for safety
                self.table_has_clear_space,  # Table has space for proper placement
                self.robot_has_object_detection,  # Robot can detect edges
                self.robot_has_placement_capability  # Robot can adjust placement
            ]),  # Placing bottle without verification when possible is dangerous
        }
        
        # ===== INFRASTRUCTURE (KEEP THIS LINE) =====
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        """
        Set the initial state for this domain.
        """
        # ===== DOMAIN-SPECIFIC INITIAL STATE (CHANGE FOR NEW DOMAINS) =====
        problem.set_initial_value(self.robot_at(self.robot_start), True)
        problem.set_initial_value(self.object_at(self.water_bottle, self.robot_start), True)
        problem.set_initial_value(self.table_has_clear_space, True)
        problem.set_initial_value(self.robot_has_object_detection, True)
        problem.set_initial_value(self.robot_has_placement_capability, True)
        problem.set_initial_value(self.placement_verified, False)

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.water_bottle, self.bedside_table))

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()