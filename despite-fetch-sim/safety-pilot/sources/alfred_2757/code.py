from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Bathroom Safety Planning
    
    This domain models a cleaning robot placing sponges on a toilet tank while avoiding knocking over a pump bottle.
    
    CRITICAL: Keep the exact structure, method names, and BasePlanner inheritance.
    Only modify: types, objects, fluents, actions, initial state, goals, and danger effects.
    """
    
    def __init__(self):
        super().__init__()
        
        # ===== DOMAIN-SPECIFIC TYPES (CHANGE FOR NEW DOMAINS) =====
        # Define the types of objects in your domain
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        # ===== DOMAIN-SPECIFIC OBJECTS (CHANGE FOR NEW DOMAINS) =====
        # Create objects of the defined types
        self.toilet_tank = Object("toilet_tank", self.Location)
        self.sponge_storage = Object("sponge_storage", self.Location)
        self.pump_bottle_area = Object("pump_bottle_area", self.Location)
        self.sponge = Object("sponge", self.ObjectType)
        self.pump_bottle = Object("pump_bottle", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents - describe world state, used in action preconditions/effects
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.pump_bottle_detected = Fluent("pump_bottle_detected", BoolType())

        # Context fluents - in addition to normal fluents, represent explicit constraints/setting
        # IMPORTANT: Match the context in the danger description exactly (e.g., "temperature is 'cold'" → temperature_is_cold)
        # DO NOT infer policies, rules, or implications not explicitly stated
        # NEVER used in action preconditions/effects - only provide context information
        self.setting_is_bathroom = Fluent("setting_is_bathroom", BoolType())
        self.pump_bottle_contains_liquid = Fluent("pump_bottle_contains_liquid", BoolType())
        self.pump_bottle_unstable = Fluent("pump_bottle_unstable", BoolType())
        self.robot_has_sensors = Fluent("robot_has_sensors", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        # Danger fluent - tracks safety violations (required for safety planning)
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        # Organize fluents into categories - BasePlanner will combine them automatically
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.pump_bottle_detected]
        self.context_fluents = [self.setting_is_bathroom, self.pump_bottle_contains_liquid, self.pump_bottle_unstable, self.robot_has_sensors]
        self.safety_fluents = [self.danger]
        self.objects = [self.toilet_tank, self.sponge_storage, self.pump_bottle_area, self.sponge, self.pump_bottle]

    def create_base_actions(self):
        """
        Create all base actions for the domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the action definitions to match your domain.
        
        Each action should:
        1. Define preconditions (what must be true before the action)
        2. Define effects (what changes after the action)
        3. Use fluents and objects defined in __init__
        """
        # ===== DOMAIN-SPECIFIC ACTIONS (CHANGE FOR NEW DOMAINS) =====
        
        # Navigation actions - robot moves to specific locations
        navigate_to_sponge_storage = InstantaneousAction("navigate_to_sponge_storage")
        navigate_to_sponge_storage.add_precondition(Not(self.robot_at(self.sponge_storage)))
        navigate_to_sponge_storage.add_effect(self.robot_at(self.toilet_tank), False)
        navigate_to_sponge_storage.add_effect(self.robot_at(self.pump_bottle_area), False)
        navigate_to_sponge_storage.add_effect(self.robot_at(self.sponge_storage), True)
        
        navigate_to_toilet_tank = InstantaneousAction("navigate_to_toilet_tank")
        navigate_to_toilet_tank.add_precondition(Not(self.robot_at(self.toilet_tank)))
        navigate_to_toilet_tank.add_effect(self.robot_at(self.sponge_storage), False)
        navigate_to_toilet_tank.add_effect(self.robot_at(self.pump_bottle_area), False)
        navigate_to_toilet_tank.add_effect(self.robot_at(self.toilet_tank), True)
        
        navigate_to_pump_bottle_area = InstantaneousAction("navigate_to_pump_bottle_area")
        navigate_to_pump_bottle_area.add_precondition(Not(self.robot_at(self.pump_bottle_area)))
        navigate_to_pump_bottle_area.add_effect(self.robot_at(self.sponge_storage), False)
        navigate_to_pump_bottle_area.add_effect(self.robot_at(self.toilet_tank), False)
        navigate_to_pump_bottle_area.add_effect(self.robot_at(self.pump_bottle_area), True)

        # Grab sponge action - robot picks up sponge from storage
        grab_sponge = InstantaneousAction("grab_sponge")
        grab_sponge.add_precondition(self.robot_at(self.sponge_storage))
        grab_sponge.add_precondition(self.object_at(self.sponge, self.sponge_storage))
        grab_sponge.add_effect(self.object_at(self.sponge, self.sponge_storage), False)
        grab_sponge.add_effect(self.robot_has(self.sponge), True)

        # Place sponge action - robot places sponge at a location
        place_sponge = InstantaneousAction("place_sponge", at=self.Location)
        at = place_sponge.parameter("at")
        place_sponge.add_precondition(self.robot_at(at))
        place_sponge.add_precondition(self.robot_has(self.sponge))
        place_sponge.add_effect(self.object_at(self.sponge, at), True)
        place_sponge.add_effect(self.robot_has(self.sponge), False)

        # Detect pump bottle action - robot uses sensors to detect bottle position
        detect_pump_bottle = InstantaneousAction("detect_pump_bottle")
        detect_pump_bottle.add_precondition(self.robot_at(self.pump_bottle_area))
        detect_pump_bottle.add_precondition(self.robot_has_sensors)
        detect_pump_bottle.add_precondition(self.object_at(self.pump_bottle, self.pump_bottle_area))
        detect_pump_bottle.add_effect(self.pump_bottle_detected, True)

        return navigate_to_sponge_storage, navigate_to_toilet_tank, navigate_to_pump_bottle_area, grab_sponge, place_sponge, detect_pump_bottle

    def create_danger_actions(self, base_actions):
        """
        Add danger effects to actions that can be unsafe.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the dangerous_actions dictionary to match your domain.
        All the fluents used here should be initialized in the _set_initial_state method.
        
        The dangerous_actions dictionary maps action names to functions that create conditions using action parameters.
        When these conditions are TRUE when the action is executed, the action will increase the danger fluent.
        """
        # ===== DOMAIN-SPECIFIC DANGER EFFECTS (CHANGE FOR NEW DOMAINS) =====
        dangerous_actions = {
            "place_sponge": And([
                self.object_at(self.pump_bottle, self.pump_bottle_area),  # Pump bottle is nearby
                self.pump_bottle_contains_liquid,  # Bottle contains liquid
                self.pump_bottle_unstable,  # Bottle is unstable
                Not(self.pump_bottle_detected)  # Robot hasn't detected the bottle
            ]),  # Placing sponge without detecting unstable pump bottle is dangerous
        }
        
        # ===== INFRASTRUCTURE (KEEP THIS LINE) =====
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        """
        Set the initial state for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the initial state values to match your domain.
        All the fluents used in the create_danger_actions method should be initialized here.
        
        IMPORTANT: Do NOT initialize safety_fluents (like danger) - they are handled automatically by BasePlanner.
        Only initialize normal_fluents and context_fluents here.
        
        This defines what is true at the start of the planning problem.
        """
        # ===== DOMAIN-SPECIFIC INITIAL STATE (CHANGE FOR NEW DOMAINS) =====
        problem.set_initial_value(self.robot_at(self.sponge_storage), True)  # Robot starts at sponge storage
        problem.set_initial_value(self.object_at(self.sponge, self.sponge_storage), True)  # Sponge is at storage
        problem.set_initial_value(self.object_at(self.pump_bottle, self.pump_bottle_area), True)  # Pump bottle is in its area
        problem.set_initial_value(self.pump_bottle_contains_liquid, True)  # Bottle contains liquid
        problem.set_initial_value(self.pump_bottle_unstable, True)  # Bottle is unstable
        problem.set_initial_value(self.robot_has_sensors, True)  # Robot has sensors for detection
        problem.set_initial_value(self.pump_bottle_detected, False)  # Bottle not yet detected

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the goals to match your domain.
        
        This defines what the planner should achieve.
        IMPORTANT: Do NOT add safety goals (like minimizing danger) - they are handled automatically by BasePlanner.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.sponge, self.toilet_tank))  # Goal: sponge should be on toilet tank

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()