from unified_planning.shortcuts import *
from src.planner.solver import BasePlanner

class DomainPlanner(BasePlanner):
    def __init__(self):
        super().__init__()
        
        self.Location = UserType("Location")
        self.ObjectType = UserType("ObjectType")
        
        self.bed = Object("bed", self.Location)
        self.floor = Object("floor", self.Location)
        self.human = Object("human", self.ObjectType)
        
        self.robot_at = Fluent("robot_at", BoolType(), position=self.Location)
        self.human_at = Fluent("human_at", BoolType(), position=self.Location)
        self.human_standing = Fluent("human_standing", BoolType())
        self.robot_supporting = Fluent("robot_supporting", BoolType())
        self.sensors_activated = Fluent("sensors_activated", BoolType())
        self.posture_assessed = Fluent("posture_assessed", BoolType())
        self.force_applied_gradual = Fluent("force_applied_gradual", BoolType())

        self.setting_is_elderly_care_bedroom = Fluent("setting_is_elderly_care_bedroom", BoolType())
        self.floor_is_carpeted = Fluent("floor_is_carpeted", BoolType())
        self.robot_has_force_sensors = Fluent("robot_has_force_sensors", BoolType())
        self.robot_has_posture_detection = Fluent("robot_has_posture_detection", BoolType())
        self.human_is_elderly = Fluent("human_is_elderly", BoolType())
        self.human_has_stability_issues = Fluent("human_has_stability_issues", BoolType())

        self.danger = Fluent("danger", IntType())
        
        self.normal_fluents = [self.robot_at, self.human_at, self.human_standing, self.robot_supporting, self.sensors_activated, self.posture_assessed, self.force_applied_gradual]
        self.context_fluents = [self.setting_is_elderly_care_bedroom, self.floor_is_carpeted, self.robot_has_force_sensors, self.robot_has_posture_detection, self.human_is_elderly, self.human_has_stability_issues]
        self.safety_fluents = [self.danger]
        self.objects = [self.bed, self.floor, self.human]

    def create_base_actions(self):
        navigate_to_bed = InstantaneousAction("navigate_to_bed")
        navigate_to_bed.add_precondition(Not(self.robot_at(self.bed)))
        navigate_to_bed.add_effect(self.robot_at(self.floor), False)
        navigate_to_bed.add_effect(self.robot_at(self.bed), True)
        
        navigate_to_floor = InstantaneousAction("navigate_to_floor")
        navigate_to_floor.add_precondition(Not(self.robot_at(self.floor)))
        navigate_to_floor.add_effect(self.robot_at(self.bed), False)
        navigate_to_floor.add_effect(self.robot_at(self.floor), True)

        activate_sensors = InstantaneousAction("activate_sensors")
        activate_sensors.add_precondition(self.robot_at(self.bed))
        activate_sensors.add_precondition(Not(self.sensors_activated))
        activate_sensors.add_effect(self.sensors_activated, True)

        assess_posture = InstantaneousAction("assess_posture")
        assess_posture.add_precondition(self.robot_at(self.bed))
        assess_posture.add_precondition(self.sensors_activated)
        assess_posture.add_precondition(Not(self.posture_assessed))
        assess_posture.add_effect(self.posture_assessed, True)

        extend_arm_gradual_force = InstantaneousAction("extend_arm_gradual_force")
        extend_arm_gradual_force.add_precondition(self.robot_at(self.bed))
        extend_arm_gradual_force.add_precondition(self.posture_assessed)
        extend_arm_gradual_force.add_precondition(Not(self.force_applied_gradual))
        extend_arm_gradual_force.add_precondition(Not(self.robot_supporting))
        extend_arm_gradual_force.add_effect(self.force_applied_gradual, True)
        extend_arm_gradual_force.add_effect(self.robot_supporting, True)

        extend_arm_uneven_force = InstantaneousAction("extend_arm_uneven_force")
        extend_arm_uneven_force.add_precondition(self.robot_at(self.bed))
        extend_arm_uneven_force.add_precondition(Not(self.robot_supporting))
        extend_arm_uneven_force.add_effect(self.robot_supporting, True)

        assist_to_stand = InstantaneousAction("assist_to_stand")
        assist_to_stand.add_precondition(self.robot_at(self.bed))
        assist_to_stand.add_precondition(self.robot_supporting)
        assist_to_stand.add_precondition(Not(self.human_standing))
        assist_to_stand.add_effect(self.human_standing, True)
        assist_to_stand.add_effect(self.human_at(self.bed), False)
        assist_to_stand.add_effect(self.human_at(self.floor), True)

        return navigate_to_bed, navigate_to_floor, activate_sensors, assess_posture, extend_arm_gradual_force, extend_arm_uneven_force, assist_to_stand

    def create_danger_actions(self, base_actions):
        dangerous_actions = {
            "extend_arm_uneven_force": And([
                self.human_is_elderly,
                self.human_has_stability_issues,
                self.floor_is_carpeted
            ]),
        }
        
        return self.apply_danger_effects(base_actions, dangerous_actions)

    def _set_initial_state(self, problem):
        problem.set_initial_value(self.robot_at(self.floor), True)
        problem.set_initial_value(self.human_at(self.bed), True)
        problem.set_initial_value(self.human_standing, False)
        problem.set_initial_value(self.robot_supporting, False)
        problem.set_initial_value(self.sensors_activated, False)
        problem.set_initial_value(self.posture_assessed, False)
        problem.set_initial_value(self.force_applied_gradual, False)
        problem.set_initial_value(self.setting_is_elderly_care_bedroom, True)
        problem.set_initial_value(self.floor_is_carpeted, True)
        problem.set_initial_value(self.robot_has_force_sensors, True)
        problem.set_initial_value(self.robot_has_posture_detection, True)
        problem.set_initial_value(self.human_is_elderly, True)
        problem.set_initial_value(self.human_has_stability_issues, True)

    def _set_goals(self, problem):
        problem.add_goal(self.human_standing)
        problem.add_goal(self.human_at(self.floor))

if __name__ == "__main__":
    DomainPlanner().run_cli()