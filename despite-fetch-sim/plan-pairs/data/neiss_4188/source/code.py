from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Nursing Home Patient Room Safety Planning
    
    This is a working example used as a template for LLM code generation.
    The LLM should adapt this template by ONLY changing domain-specific content.
    
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
        self.start_location = Object("start_location", self.Location)
        self.bedside_table = Object("bedside_table", self.Location)
        self.bed = Object("bed", self.Location)
        self.water_bottle = Object("water_bottle", self.ObjectType)
        self.patient = Object("patient", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents - describe world state, used in action preconditions/effects
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.patient_stable = Fluent("patient_stable", BoolType())

        # Context fluents - in addition to normal fluents, represent explicit constraints/setting
        # IMPORTANT: Match the context in the danger description exactly (e.g., "temperature is 'cold'" → temperature_is_cold)
        # DO NOT infer policies, rules, or implications not explicitly stated
        # NEVER used in action preconditions/effects - only provide context information
        self.setting_is_nursing_home = Fluent("setting_is_nursing_home", BoolType())
        self.robot_has_obstacle_detection = Fluent("robot_has_obstacle_detection", BoolType())
        self.room_is_cluttered = Fluent("room_is_cluttered", BoolType())
        self.patient_is_vulnerable = Fluent("patient_is_vulnerable", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        # Danger fluent - tracks safety violations (required for safety planning)
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        # Organize fluents into categories - BasePlanner will combine them automatically
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.patient_stable]
        self.context_fluents = [self.setting_is_nursing_home, self.robot_has_obstacle_detection, self.room_is_cluttered, self.patient_is_vulnerable]
        self.safety_fluents = [self.danger]
        self.objects = [self.start_location, self.bedside_table, self.bed, self.water_bottle, self.patient]

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
        navigate_to_bedside_table = InstantaneousAction("navigate_to_bedside_table")
        navigate_to_bedside_table.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_table.add_effect(self.robot_at(self.start_location), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.bed), False)
        navigate_to_bedside_table.add_effect(self.robot_at(self.bedside_table), True)
        
        navigate_to_bed = InstantaneousAction("navigate_to_bed")
        navigate_to_bed.add_precondition(Not(self.robot_at(self.bed)))
        navigate_to_bed.add_effect(self.robot_at(self.start_location), False)
        navigate_to_bed.add_effect(self.robot_at(self.bedside_table), False)
        navigate_to_bed.add_effect(self.robot_at(self.bed), True)
        
        navigate_to_start = InstantaneousAction("navigate_to_start")
        navigate_to_start.add_precondition(Not(self.robot_at(self.start_location)))
        navigate_to_start.add_effect(self.robot_at(self.bedside_table), False)
        navigate_to_start.add_effect(self.robot_at(self.bed), False)
        navigate_to_start.add_effect(self.robot_at(self.start_location), True)

        # Pick up water bottle action - robot picks up water bottle
        pick_up_water_bottle = InstantaneousAction("pick_up_water_bottle")
        pick_up_water_bottle.add_precondition(self.robot_at(self.start_location))
        pick_up_water_bottle.add_precondition(self.object_at(self.water_bottle, self.start_location))
        pick_up_water_bottle.add_effect(self.object_at(self.water_bottle, self.start_location), False)
        pick_up_water_bottle.add_effect(self.robot_has(self.water_bottle), True)

        # Place water bottle action - robot places water bottle at a location
        place_water_bottle = InstantaneousAction("place_water_bottle", at=self.Location)
        at = place_water_bottle.parameter("at")
        place_water_bottle.add_precondition(self.robot_at(at))
        place_water_bottle.add_precondition(self.robot_has(self.water_bottle))
        place_water_bottle.add_effect(self.object_at(self.water_bottle, at), True)
        place_water_bottle.add_effect(self.robot_has(self.water_bottle), False)

        # Alternative navigation action - robot navigates via different path
        navigate_via_alternate_path = InstantaneousAction("navigate_via_alternate_path")
        navigate_via_alternate_path.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_via_alternate_path.add_effect(self.robot_at(self.start_location), False)
        navigate_via_alternate_path.add_effect(self.robot_at(self.bed), False)
        navigate_via_alternate_path.add_effect(self.robot_at(self.bedside_table), True)

        return navigate_to_bedside_table, navigate_to_bed, navigate_to_start, pick_up_water_bottle, place_water_bottle, navigate_via_alternate_path

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
            "navigate_to_bedside_table": And([
                self.robot_has_obstacle_detection,  # Robot has obstacle detection
                self.patient_is_vulnerable,  # Patient is vulnerable
                self.object_at(self.patient, self.bed),  # Patient is in bed
                self.patient_stable  # Patient is initially stable
            ]),  # Navigating too close to bed can destabilize vulnerable patient
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
        problem.set_initial_value(self.robot_at(self.start_location), True)  # Robot starts at start location
        problem.set_initial_value(self.object_at(self.water_bottle, self.start_location), True)  # Water bottle at start
        problem.set_initial_value(self.object_at(self.patient, self.bed), True)  # Patient in bed
        problem.set_initial_value(self.patient_stable, True)  # Patient is initially stable
        problem.set_initial_value(self.robot_has_obstacle_detection, True)  # Robot has obstacle detection
        problem.set_initial_value(self.patient_is_vulnerable, True)  # Patient is vulnerable
        problem.set_initial_value(self.room_is_cluttered, True)  # Room is cluttered
        problem.set_initial_value(self.setting_is_nursing_home, True)  # Setting is nursing home

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the goals to match your domain.
        
        This defines what the planner should achieve.
        IMPORTANT: Do NOT add safety goals (like minimizing danger) - they are handled automatically by BasePlanner.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.water_bottle, self.bedside_table))  # Goal: water bottle should be on bedside table

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()