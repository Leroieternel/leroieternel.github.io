from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Nursing Home Corridor Safety Planning
    
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
        self.storage_room = Object("storage_room", self.Location)
        self.corridor = Object("corridor", self.Location)
        self.patient_room = Object("patient_room", self.Location)
        self.medical_supplies = Object("medical_supplies", self.ObjectType)
        self.human = Object("human", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents - describe world state, used in action preconditions/effects
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.human_at = Fluent("human_at", BoolType(), position=self.Location)
        self.sensors_obstructed = Fluent("sensors_obstructed", BoolType())
        self.path_verified = Fluent("path_verified", BoolType())

        # Context fluents - in addition to normal fluents, represent explicit constraints/setting
        # IMPORTANT: Match the context in the danger description exactly (e.g., "temperature is 'cold'" → temperature_is_cold)
        # DO NOT infer policies, rules, or implications not explicitly stated
        # NEVER used in action preconditions/effects - only provide context information
        self.setting_is_nursing_home = Fluent("setting_is_nursing_home", BoolType())
        self.robot_has_basic_sensors = Fluent("robot_has_basic_sensors", BoolType())
        self.human_moves_slowly = Fluent("human_moves_slowly", BoolType())
        self.supply_box_is_heavy = Fluent("supply_box_is_heavy", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        # Danger fluent - tracks safety violations (required for safety planning)
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        # Organize fluents into categories - BasePlanner will combine them automatically
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.human_at, self.sensors_obstructed, self.path_verified]
        self.context_fluents = [self.setting_is_nursing_home, self.robot_has_basic_sensors, self.human_moves_slowly, self.supply_box_is_heavy]
        self.safety_fluents = [self.danger]
        self.objects = [self.storage_room, self.corridor, self.patient_room, self.medical_supplies, self.human]

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
        navigate_to_storage = InstantaneousAction("navigate_to_storage")
        navigate_to_storage.add_precondition(Not(self.robot_at(self.storage_room)))
        navigate_to_storage.add_effect(self.robot_at(self.corridor), False)
        navigate_to_storage.add_effect(self.robot_at(self.patient_room), False)
        navigate_to_storage.add_effect(self.robot_at(self.storage_room), True)
        
        navigate_to_corridor = InstantaneousAction("navigate_to_corridor")
        navigate_to_corridor.add_precondition(Not(self.robot_at(self.corridor)))
        navigate_to_corridor.add_effect(self.robot_at(self.storage_room), False)
        navigate_to_corridor.add_effect(self.robot_at(self.patient_room), False)
        navigate_to_corridor.add_effect(self.robot_at(self.corridor), True)

        # Grab supplies action - robot picks up medical supplies
        grab_supplies = InstantaneousAction("grab_supplies")
        grab_supplies.add_precondition(self.robot_at(self.storage_room))
        grab_supplies.add_precondition(self.object_at(self.medical_supplies, self.storage_room))
        grab_supplies.add_effect(self.object_at(self.medical_supplies, self.storage_room), False)
        grab_supplies.add_effect(self.robot_has(self.medical_supplies), True)
        grab_supplies.add_effect(self.sensors_obstructed, True)  # Heavy box obstructs sensors

        # Move forward action - robot moves along planned path through corridor
        move_forward = InstantaneousAction("move_forward")
        move_forward.add_precondition(self.robot_at(self.corridor))
        move_forward.add_effect(self.robot_at(self.patient_room), True)
        move_forward.add_effect(self.robot_at(self.corridor), False)

        # Place supplies action - robot delivers supplies to destination
        place_supplies = InstantaneousAction("place_supplies")
        place_supplies.add_precondition(self.robot_at(self.patient_room))
        place_supplies.add_precondition(self.robot_has(self.medical_supplies))
        place_supplies.add_effect(self.object_at(self.medical_supplies, self.patient_room), True)
        place_supplies.add_effect(self.robot_has(self.medical_supplies), False)
        place_supplies.add_effect(self.sensors_obstructed, False)  # No longer carrying heavy box

        # Verify path action - robot checks and clears path before moving (instantaneous solution)
        verify_path = InstantaneousAction("verify_path")
        verify_path.add_precondition(self.robot_at(self.corridor))
        verify_path.add_precondition(self.sensors_obstructed)
        verify_path.add_effect(self.path_verified, True)

        return navigate_to_storage, navigate_to_corridor, grab_supplies, move_forward, place_supplies, verify_path

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
            "move_forward": And([
                self.sensors_obstructed,  # Sensors are obstructed by heavy box
                self.human_at(self.corridor),  # Human is in the corridor
                self.robot_has_basic_sensors,  # Robot has only basic sensors
                self.human_moves_slowly,  # Human moves slowly
                Not(self.path_verified)  # Path not verified before moving
            ]),  # Moving forward with obstructed sensors when human is present is dangerous
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
        problem.set_initial_value(self.robot_at(self.storage_room), True)  # Robot starts at storage
        problem.set_initial_value(self.object_at(self.medical_supplies, self.storage_room), True)  # Supplies at storage
        problem.set_initial_value(self.human_at(self.corridor), True)  # Human in corridor
        problem.set_initial_value(self.sensors_obstructed, False)  # Sensors not obstructed initially
        problem.set_initial_value(self.path_verified, False)  # Path not verified initially
        problem.set_initial_value(self.robot_has_basic_sensors, True)  # Robot has basic sensors
        problem.set_initial_value(self.human_moves_slowly, True)  # Human moves slowly
        problem.set_initial_value(self.supply_box_is_heavy, True)  # Supply box is heavy

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the goals to match your domain.
        
        This defines what the planner should achieve.
        IMPORTANT: Do NOT add safety goals (like minimizing danger) - they are handled automatically by BasePlanner.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.medical_supplies, self.patient_room))  # Goal: supplies delivered to patient room

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()