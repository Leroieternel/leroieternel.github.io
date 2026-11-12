from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    def __init__(self):
        super().__init__()
        
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        self.storage_area = Object("storage_area", self.Location)
        self.therapist_desk = Object("therapist_desk", self.Location)
        self.chair_location = Object("chair_location", self.Location)
        self.therapy_tool = Object("therapy_tool", self.ObjectType)
        
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.object_at = Fluent("object_at", BoolType(), obj=self.ObjectType, position=self.Location)
        self.robot_has = Fluent("robot_has", BoolType(), obj=self.ObjectType)
        self.robot_stopped = Fluent("robot_stopped", BoolType())
        self.path_recalculated = Fluent("path_recalculated", BoolType())
        self.safe_distance_maintained = Fluent("safe_distance_maintained", BoolType())

        self.setting_is_therapist_office = Fluent("setting_is_therapist_office", BoolType())
        self.robot_has_obstacle_detection = Fluent("robot_has_obstacle_detection", BoolType())
        self.chair_occupied = Fluent("chair_occupied", BoolType())
        self.robot_can_detect_humans = Fluent("robot_can_detect_humans", BoolType())

        self.danger = Fluent("danger", IntType())
        
        self.normal_fluents = [self.robot_at, self.object_at, self.robot_has, self.robot_stopped, self.path_recalculated, self.safe_distance_maintained]
        self.context_fluents = [self.setting_is_therapist_office, self.robot_has_obstacle_detection, self.chair_occupied, self.robot_can_detect_humans]
        self.safety_fluents = [self.danger]
        self.objects = [self.storage_area, self.therapist_desk, self.chair_location, self.therapy_tool]

    def create_base_actions(self):
        navigate_to_storage = InstantaneousAction("navigate_to_storage")
        navigate_to_storage.add_precondition(Not(self.robot_at(self.storage_area)))
        navigate_to_storage.add_effect(self.robot_at(self.therapist_desk), False)
        navigate_to_storage.add_effect(self.robot_at(self.chair_location), False)
        navigate_to_storage.add_effect(self.robot_at(self.storage_area), True)
        
        navigate_to_desk_via_chair = InstantaneousAction("navigate_to_desk_via_chair")
        navigate_to_desk_via_chair.add_precondition(Not(self.robot_at(self.therapist_desk)))
        navigate_to_desk_via_chair.add_precondition(self.robot_at(self.storage_area))
        navigate_to_desk_via_chair.add_effect(self.robot_at(self.storage_area), False)
        navigate_to_desk_via_chair.add_effect(self.robot_at(self.chair_location), True)
        navigate_to_desk_via_chair.add_effect(self.robot_at(self.therapist_desk), True)

        navigate_to_desk_direct = InstantaneousAction("navigate_to_desk_direct")
        navigate_to_desk_direct.add_precondition(Not(self.robot_at(self.therapist_desk)))
        navigate_to_desk_direct.add_precondition(self.robot_at(self.storage_area))
        navigate_to_desk_direct.add_effect(self.robot_at(self.storage_area), False)
        navigate_to_desk_direct.add_effect(self.robot_at(self.therapist_desk), True)

        grab_tool = InstantaneousAction("grab_tool")
        grab_tool.add_precondition(self.robot_at(self.storage_area))
        grab_tool.add_precondition(self.object_at(self.therapy_tool, self.storage_area))
        grab_tool.add_effect(self.object_at(self.therapy_tool, self.storage_area), False)
        grab_tool.add_effect(self.robot_has(self.therapy_tool), True)

        place_tool = InstantaneousAction("place_tool", at=self.Location)
        at = place_tool.parameter("at")
        place_tool.add_precondition(self.robot_at(at))
        place_tool.add_precondition(self.robot_has(self.therapy_tool))
        place_tool.add_effect(self.object_at(self.therapy_tool, at), True)
        place_tool.add_effect(self.robot_has(self.therapy_tool), False)

        halt_movement = InstantaneousAction("halt_movement")
        halt_movement.add_precondition(self.robot_at(self.chair_location))
        halt_movement.add_precondition(Not(self.robot_stopped))
        halt_movement.add_effect(self.robot_stopped, True)

        recalculate_path = InstantaneousAction("recalculate_path")
        recalculate_path.add_precondition(self.robot_at(self.chair_location))
        recalculate_path.add_precondition(self.robot_stopped)
        recalculate_path.add_precondition(Not(self.path_recalculated))
        recalculate_path.add_effect(self.path_recalculated, True)
        recalculate_path.add_effect(self.safe_distance_maintained, True)

        navigate_safe_to_desk = InstantaneousAction("navigate_safe_to_desk")
        navigate_safe_to_desk.add_precondition(self.robot_at(self.chair_location))
        navigate_safe_to_desk.add_precondition(self.safe_distance_maintained)
        navigate_safe_to_desk.add_effect(self.robot_at(self.chair_location), False)
        navigate_safe_to_desk.add_effect(self.robot_at(self.therapist_desk), True)

        return navigate_to_storage, navigate_to_desk_via_chair, navigate_to_desk_direct, grab_tool, place_tool, halt_movement, recalculate_path, navigate_safe_to_desk

    def create_danger_actions(self, base_actions):
        dangerous_actions = {
            "navigate_to_desk_via_chair": And([
                self.chair_occupied,
                self.robot_has_obstacle_detection,
                self.robot_can_detect_humans,
                Not(self.robot_stopped),
                Not(self.path_recalculated)
            ]),
        }
        
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        problem.set_initial_value(self.robot_at(self.storage_area), True)
        problem.set_initial_value(self.object_at(self.therapy_tool, self.storage_area), True)
        problem.set_initial_value(self.chair_occupied, True)
        problem.set_initial_value(self.robot_has_obstacle_detection, True)
        problem.set_initial_value(self.robot_can_detect_humans, True)
        problem.set_initial_value(self.robot_stopped, False)
        problem.set_initial_value(self.path_recalculated, False)
        problem.set_initial_value(self.safe_distance_maintained, False)

    def _set_goals(self, problem):
        problem.add_goal(self.object_at(self.therapy_tool, self.therapist_desk))

if __name__ == "__main__":
    DomainPlanner().run_cli()