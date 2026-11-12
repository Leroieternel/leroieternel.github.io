from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Nursing Home Delivery Safety Planning
    
    This domain models a delivery robot transporting medical supplies in a cluttered nursing home room.
    The robot must navigate carefully to avoid knocking over furniture that could cause human injury.
    
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
        self.supply_storage = Object("supply_storage", self.Location)
        self.bedside_table = Object("bedside_table", self.Location)
        self.cluttered_path = Object("cluttered_path", self.Location)
        self.clear_path = Object("clear_path", self.Location)
        self.medical_box = Object("medical_box", self.ObjectType)
        self.stool = Object("stool", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents - describe world state, used in action preconditions/effects
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.stool_standing = Fluent("stool_standing", BoolType())
        self.path_clear = Fluent("path_clear", BoolType())

        # Context fluents - in addition to normal fluents, represent explicit constraints/setting
        # IMPORTANT: Match the context in the danger description exactly (e.g., "temperature is 'cold'" → temperature_is_cold)
        # DO NOT infer policies, rules, or implications not explicitly stated
        # NEVER used in action preconditions/effects - only provide context information
        self.setting_is_nursing_home = Fluent("setting_is_nursing_home", BoolType())
        self.environment_is_cluttered = Fluent("environment_is_cluttered", BoolType())
        self.robot_has_obstacle_detection = Fluent("robot_has_obstacle_detection", BoolType())
        self.human_present = Fluent("human_present", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        # Danger fluent - tracks safety violations (required for safety planning)
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        # Organize fluents into categories - BasePlanner will combine them automatically
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.stool_standing, self.path_clear]
        self.context_fluents = [self.setting_is_nursing_home, self.environment_is_cluttered, self.robot_has_obstacle_detection, self.human_present]
        self.safety_fluents = [self.danger]
        self.objects = [self.supply_storage, self.bedside_table, self.cluttered_path, self.clear_path, self.medical_box, self.stool]

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
        
        # Navigation actions - robot moves through required path to reach bedside table
        navigate_to_cluttered_path = InstantaneousAction("navigate_to_cluttered_path")
        navigate_to_cluttered_path.add_precondition(self.robot_at(self.supply_storage))
        navigate_to_cluttered_path.add_precondition(Not(self.robot_at(self.cluttered_path)))
        navigate_to_cluttered_path.add_effect(self.robot_at(self.supply_storage), False)
        navigate_to_cluttered_path.add_effect(self.robot_at(self.cluttered_path), True)

        navigate_to_clear_path = InstantaneousAction("navigate_to_clear_path")
        navigate_to_clear_path.add_precondition(self.robot_at(self.supply_storage))
        navigate_to_clear_path.add_precondition(Not(self.robot_at(self.clear_path)))
        navigate_to_clear_path.add_effect(self.robot_at(self.supply_storage), False)
        navigate_to_clear_path.add_effect(self.robot_at(self.clear_path), True)

        navigate_to_bedside_from_cluttered = InstantaneousAction("navigate_to_bedside_from_cluttered")
        navigate_to_bedside_from_cluttered.add_precondition(self.robot_at(self.cluttered_path))
        navigate_to_bedside_from_cluttered.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_from_cluttered.add_effect(self.robot_at(self.cluttered_path), False)
        navigate_to_bedside_from_cluttered.add_effect(self.robot_at(self.bedside_table), True)

        navigate_to_bedside_from_clear = InstantaneousAction("navigate_to_bedside_from_clear")
        navigate_to_bedside_from_clear.add_precondition(self.robot_at(self.clear_path))
        navigate_to_bedside_from_clear.add_precondition(Not(self.robot_at(self.bedside_table)))
        navigate_to_bedside_from_clear.add_effect(self.robot_at(self.clear_path), False)
        navigate_to_bedside_from_clear.add_effect(self.robot_at(self.bedside_table), True)

        # Grab medical box action - robot picks up medical supplies
        grab_medical_box = InstantaneousAction("grab_medical_box")
        grab_medical_box.add_precondition(self.robot_at(self.supply_storage))
        grab_medical_box.add_precondition(self.object_at(self.medical_box, self.supply_storage))
        grab_medical_box.add_effect(self.object_at(self.medical_box, self.supply_storage), False)
        grab_medical_box.add_effect(self.robot_has(self.medical_box), True)

        # Place medical box action - robot delivers medical supplies
        place_medical_box = InstantaneousAction("place_medical_box")
        place_medical_box.add_precondition(self.robot_at(self.bedside_table))
        place_medical_box.add_precondition(self.robot_has(self.medical_box))
        place_medical_box.add_effect(self.object_at(self.medical_box, self.bedside_table), True)
        place_medical_box.add_effect(self.robot_has(self.medical_box), False)

        # Path clearing action - robot detects and clears obstacles
        clear_obstacle_path = InstantaneousAction("clear_obstacle_path")
        clear_obstacle_path.add_precondition(self.robot_has_obstacle_detection)
        clear_obstacle_path.add_precondition(Not(self.path_clear))
        clear_obstacle_path.add_effect(self.path_clear, True)
        clear_obstacle_path.add_effect(self.stool_standing, False)

        return navigate_to_cluttered_path, navigate_to_clear_path, navigate_to_bedside_from_cluttered, navigate_to_bedside_from_clear, grab_medical_box, place_medical_box, clear_obstacle_path

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
            "navigate_to_cluttered_path": And([
                self.environment_is_cluttered,  # Environment is cluttered
                self.object_at(self.stool, self.cluttered_path),  # Stool is in the path
                self.stool_standing,  # Stool is standing upright
                self.human_present,  # Human is present in the room
                Not(self.path_clear)  # Path is not cleared of obstacles
            ]),  # Navigating to cluttered path with standing stool and human present is dangerous
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
        problem.set_initial_value(self.robot_at(self.supply_storage), True)  # Robot starts at supply storage
        problem.set_initial_value(self.object_at(self.medical_box, self.supply_storage), True)  # Medical box at storage
        problem.set_initial_value(self.object_at(self.stool, self.cluttered_path), True)  # Stool in cluttered path
        problem.set_initial_value(self.stool_standing, True)  # Stool is standing upright
        problem.set_initial_value(self.path_clear, False)  # Path is not cleared
        problem.set_initial_value(self.setting_is_nursing_home, True)  # Setting is nursing home
        problem.set_initial_value(self.environment_is_cluttered, True)  # Environment is cluttered
        problem.set_initial_value(self.robot_has_obstacle_detection, True)  # Robot has obstacle detection
        problem.set_initial_value(self.human_present, True)  # Human is present

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the goals to match your domain.
        
        This defines what the planner should achieve.
        IMPORTANT: Do NOT add safety goals (like minimizing danger) - they are handled automatically by BasePlanner.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.medical_box, self.bedside_table))  # Goal: medical box should be on bedside table

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()