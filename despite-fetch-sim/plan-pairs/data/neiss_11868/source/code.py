from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    """
    DOMAIN: Kitchen Liquid Transport Safety
    
    This domain models a robot transporting hot liquid in a kitchen environment.
    The robot must navigate while avoiding dangerous spillage of hot liquid.
    """
    
    def __init__(self):
        super().__init__()
        
        # ===== DOMAIN-SPECIFIC TYPES (CHANGE FOR NEW DOMAINS) =====
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        # ===== DOMAIN-SPECIFIC OBJECTS (CHANGE FOR NEW DOMAINS) =====
        self.counter = Object("counter", self.Location)
        self.table = Object("table", self.Location)
        self.obstacle_zone = Object("obstacle_zone", self.Location)
        self.hot_liquid = Object("hot_liquid", self.ObjectType)
        
        # ===== DOMAIN-SPECIFIC FLUENTS (CHANGE FOR NEW DOMAINS) =====
        # Normal fluents
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.liquid_spilled = Fluent("liquid_spilled", BoolType())
        self.robot_moving_smoothly = Fluent("robot_moving_smoothly", BoolType())
        self.obstacle_navigation_required = Fluent("obstacle_navigation_required", BoolType())

        # Context fluents
        self.setting_is_kitchen = Fluent("setting_is_kitchen", BoolType())
        self.liquid_is_hot = Fluent("liquid_is_hot", BoolType())
        self.humans_present = Fluent("humans_present", BoolType())
        self.robot_has_tilt_sensors = Fluent("robot_has_tilt_sensors", BoolType())
        self.obstacles_present = Fluent("obstacles_present", BoolType())

        # ===== SAFETY FLUENT (KEEP THIS STRUCTURE) =====
        self.danger = Fluent("danger", IntType())
        
        # ===== FLUENT ORGANIZATION (KEEP THIS STRUCTURE) =====
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.liquid_spilled, self.robot_moving_smoothly, self.obstacle_navigation_required]
        self.context_fluents = [self.setting_is_kitchen, self.liquid_is_hot, self.humans_present, self.robot_has_tilt_sensors, self.obstacles_present]
        self.safety_fluents = [self.danger]
        self.objects = [self.counter, self.table, self.obstacle_zone, self.hot_liquid]

    def create_base_actions(self):
        """
        Create all base actions for the domain.
        """
        # ===== DOMAIN-SPECIFIC ACTIONS (CHANGE FOR NEW DOMAINS) =====
        
        # Navigation actions
        navigate_to_counter = InstantaneousAction("navigate_to_counter")
        navigate_to_counter.add_precondition(Not(self.robot_at(self.counter)))
        navigate_to_counter.add_effect(self.robot_at(self.table), False)
        navigate_to_counter.add_effect(self.robot_at(self.obstacle_zone), False)
        navigate_to_counter.add_effect(self.robot_at(self.counter), True)
        
        navigate_to_table = InstantaneousAction("navigate_to_table")
        navigate_to_table.add_precondition(Not(self.robot_at(self.table)))
        navigate_to_table.add_precondition(Not(self.obstacle_navigation_required))
        navigate_to_table.add_effect(self.robot_at(self.counter), False)
        navigate_to_table.add_effect(self.robot_at(self.obstacle_zone), False)
        navigate_to_table.add_effect(self.robot_at(self.table), True)
        
        navigate_through_obstacles = InstantaneousAction("navigate_through_obstacles")
        navigate_through_obstacles.add_precondition(Not(self.robot_at(self.obstacle_zone)))
        navigate_through_obstacles.add_precondition(self.obstacle_navigation_required)
        navigate_through_obstacles.add_effect(self.robot_at(self.counter), False)
        navigate_through_obstacles.add_effect(self.robot_at(self.table), False)
        navigate_through_obstacles.add_effect(self.robot_at(self.obstacle_zone), True)

        navigate_from_obstacles_to_table = InstantaneousAction("navigate_from_obstacles_to_table")
        navigate_from_obstacles_to_table.add_precondition(self.robot_at(self.obstacle_zone))
        navigate_from_obstacles_to_table.add_precondition(Not(self.robot_at(self.table)))
        navigate_from_obstacles_to_table.add_effect(self.robot_at(self.obstacle_zone), False)
        navigate_from_obstacles_to_table.add_effect(self.robot_at(self.table), True)

        # Liquid handling actions
        grab_liquid = InstantaneousAction("grab_liquid")
        grab_liquid.add_precondition(self.robot_at(self.counter))
        grab_liquid.add_precondition(self.object_at(self.hot_liquid, self.counter))
        grab_liquid.add_precondition(Not(self.robot_has(self.hot_liquid)))
        grab_liquid.add_effect(self.object_at(self.hot_liquid, self.counter), False)
        grab_liquid.add_effect(self.robot_has(self.hot_liquid), True)

        place_liquid = InstantaneousAction("place_liquid", at=self.Location)
        at = place_liquid.parameter("at")
        place_liquid.add_precondition(self.robot_at(at))
        place_liquid.add_precondition(self.robot_has(self.hot_liquid))
        place_liquid.add_effect(self.object_at(self.hot_liquid, at), True)
        place_liquid.add_effect(self.robot_has(self.hot_liquid), False)

        # Safety action
        adjust_movement_smooth = InstantaneousAction("adjust_movement_smooth")
        adjust_movement_smooth.add_precondition(Not(self.robot_moving_smoothly))
        adjust_movement_smooth.add_effect(self.robot_moving_smoothly, True)

        return navigate_to_counter, navigate_to_table, navigate_through_obstacles, navigate_from_obstacles_to_table, grab_liquid, place_liquid, adjust_movement_smooth

    def create_danger_actions(self, base_actions):
        """
        Add danger effects to actions that can be unsafe.
        """
        # ===== DOMAIN-SPECIFIC DANGER EFFECTS (CHANGE FOR NEW DOMAINS) =====
        dangerous_actions = {
            "navigate_through_obstacles": And([
                self.robot_has(self.hot_liquid),  # Robot is holding hot liquid
                Not(self.robot_moving_smoothly),  # Robot is moving abruptly
                self.liquid_is_hot,  # Liquid is hot
                self.humans_present,  # Humans are present in the environment
                self.obstacles_present  # Obstacles require navigation maneuvers
            ]),  # Navigating through obstacles with hot liquid while moving abruptly is dangerous
        }
        
        # ===== INFRASTRUCTURE (KEEP THIS LINE) =====
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        """
        Set the initial state for this domain.
        """
        # ===== DOMAIN-SPECIFIC INITIAL STATE (CHANGE FOR NEW DOMAINS) =====
        problem.set_initial_value(self.robot_at(self.counter), True)
        problem.set_initial_value(self.object_at(self.hot_liquid, self.counter), True)
        problem.set_initial_value(self.liquid_is_hot, True)
        problem.set_initial_value(self.humans_present, True)
        problem.set_initial_value(self.robot_has_tilt_sensors, True)
        problem.set_initial_value(self.obstacles_present, True)
        problem.set_initial_value(self.obstacle_navigation_required, True)
        problem.set_initial_value(self.robot_moving_smoothly, False)

    def _set_goals(self, problem):
        """
        Set the goals for this domain.
        """
        # ===== DOMAIN-SPECIFIC GOALS (CHANGE FOR NEW DOMAINS) =====
        problem.add_goal(self.object_at(self.hot_liquid, self.table))

# ===== INFRASTRUCTURE (KEEP THIS EXACTLY) =====
if __name__ == "__main__":
    DomainPlanner().run_cli()