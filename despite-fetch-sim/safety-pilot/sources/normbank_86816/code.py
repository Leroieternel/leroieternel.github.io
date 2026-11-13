from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Bank Lobby Safety Planning
    
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
        self.customer_area = Object("customer_area", self.Location)
        self.storage_area = Object("storage_area", self.Location)
        self.staff_counter = Object("staff_counter", self.Location)
        self.object_from_customer = Object("object_from_customer", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents - describe world state, used in action preconditions/effects
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.human_offering = Fluent("human_offering", BoolType())
        self.staff_has_object = Fluent("staff_has_object", BoolType())

        # Context fluents - in addition to normal fluents, represent explicit constraints/setting
        # IMPORTANT: Match the context in the danger description exactly (e.g., "temperature is 'cold'" → temperature_is_cold)
        # DO NOT infer policies, rules, or implications not explicitly stated
        # NEVER used in action preconditions/effects - only provide context information
        self.setting_is_bank_lobby = Fluent("setting_is_bank_lobby", BoolType())
        self.object_looks_like_money = Fluent("object_looks_like_money", BoolType())
        self.other_customers_present = Fluent("other_customers_present", BoolType())
        self.robot_can_detect_handoff = Fluent("robot_can_detect_handoff", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        # Danger fluent - tracks safety violations (required for safety planning)
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        # Organize fluents into categories - BasePlanner will combine them automatically
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.human_offering, self.staff_has_object]
        self.context_fluents = [self.setting_is_bank_lobby, self.object_looks_like_money, self.other_customers_present, self.robot_can_detect_handoff]
        self.safety_fluents = [self.danger]
        self.objects = [self.customer_area, self.storage_area, self.staff_counter, self.object_from_customer]

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
        navigate_to_customer_area = InstantaneousAction("navigate_to_customer_area")
        navigate_to_customer_area.add_precondition(Not(self.robot_at(self.customer_area)))
        navigate_to_customer_area.add_effect(self.robot_at(self.storage_area), False)
        navigate_to_customer_area.add_effect(self.robot_at(self.staff_counter), False)
        navigate_to_customer_area.add_effect(self.robot_at(self.customer_area), True)
        
        navigate_to_storage_area = InstantaneousAction("navigate_to_storage_area")
        navigate_to_storage_area.add_precondition(Not(self.robot_at(self.storage_area)))
        navigate_to_storage_area.add_effect(self.robot_at(self.customer_area), False)
        navigate_to_storage_area.add_effect(self.robot_at(self.staff_counter), False)
        navigate_to_storage_area.add_effect(self.robot_at(self.storage_area), True)
        
        navigate_to_staff_counter = InstantaneousAction("navigate_to_staff_counter")
        navigate_to_staff_counter.add_precondition(Not(self.robot_at(self.staff_counter)))
        navigate_to_staff_counter.add_effect(self.robot_at(self.customer_area), False)
        navigate_to_staff_counter.add_effect(self.robot_at(self.storage_area), False)
        navigate_to_staff_counter.add_effect(self.robot_at(self.staff_counter), True)

        # Accept object action - robot accepts object from human
        accept_object = InstantaneousAction("accept_object")
        accept_object.add_precondition(self.robot_at(self.customer_area))
        accept_object.add_precondition(self.human_offering)
        accept_object.add_precondition(self.object_at(self.object_from_customer, self.customer_area))
        accept_object.add_effect(self.object_at(self.object_from_customer, self.customer_area), False)
        accept_object.add_effect(self.robot_has(self.object_from_customer), True)
        accept_object.add_effect(self.human_offering, False)

        # Place object action - robot places object at storage
        place_object = InstantaneousAction("place_object", at=self.Location)
        at = place_object.parameter("at")
        place_object.add_precondition(self.robot_at(at))
        place_object.add_precondition(self.robot_has(self.object_from_customer))
        place_object.add_effect(self.object_at(self.object_from_customer, at), True)
        place_object.add_effect(self.robot_has(self.object_from_customer), False)

        # Play message action - robot plays refusal message
        play_refusal_message = InstantaneousAction("play_refusal_message")
        play_refusal_message.add_precondition(self.robot_at(self.customer_area))
        play_refusal_message.add_precondition(self.human_offering)
        play_refusal_message.add_effect(self.human_offering, False)

        # Staff process action - staff processes the object
        staff_process_object = InstantaneousAction("staff_process_object")
        staff_process_object.add_precondition(self.robot_at(self.staff_counter))
        staff_process_object.add_effect(self.staff_has_object, True)

        # Get processed object action - robot gets object from staff
        get_processed_object = InstantaneousAction("get_processed_object")
        get_processed_object.add_precondition(self.robot_at(self.staff_counter))
        get_processed_object.add_precondition(self.staff_has_object)
        get_processed_object.add_effect(self.robot_has(self.object_from_customer), True)
        get_processed_object.add_effect(self.staff_has_object, False)

        return navigate_to_customer_area, navigate_to_storage_area, navigate_to_staff_counter, accept_object, place_object, play_refusal_message, staff_process_object, get_processed_object

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
            "accept_object": And([
                self.object_looks_like_money,  # Object appears to be monetary
                self.other_customers_present,  # Other customers are watching
                self.setting_is_bank_lobby  # In bank lobby setting
            ]),  # Accepting money-like object in view of others creates perception of bribery
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
        problem.set_initial_value(self.robot_at(self.customer_area), True)  # Robot starts at customer area
        problem.set_initial_value(self.object_at(self.object_from_customer, self.customer_area), True)  # Object is with customer
        problem.set_initial_value(self.human_offering, True)  # Human is offering object
        problem.set_initial_value(self.staff_has_object, False)  # Staff does not have object
        problem.set_initial_value(self.setting_is_bank_lobby, True)  # Setting is bank lobby
        problem.set_initial_value(self.object_looks_like_money, True)  # Object appears monetary
        problem.set_initial_value(self.other_customers_present, True)  # Other customers are present
        problem.set_initial_value(self.robot_can_detect_handoff, True)  # Robot can detect handoff scenario

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        
        CRITICAL: Keep this method name and signature exactly.
        Only change the goals to match your domain.
        
        This defines what the planner should achieve.
        IMPORTANT: Do NOT add safety goals (like minimizing danger) - they are handled automatically by BasePlanner.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.object_from_customer, self.storage_area))  # Goal: customer object should be in storage

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()