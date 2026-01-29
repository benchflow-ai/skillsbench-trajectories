#!/usr/bin/env python3
"""
PDDL TPP Task Solver
Uses unified_planning library to solve Travelling Purchase Problem tasks
"""

import sys
from unified_planning.shortcuts import OneshotPlanner, PlanValidator
from unified_planning.io import PDDLReader, PDDLWriter

def load_problem(domain_path, problem_path):
    """
    Load a PDDL domain file and problem file into a unified planning problem object.

    Parameters:
        domain_path (str): Path to PDDL domain file
        problem_path (str): Path to PDDL problem file

    Returns:
        problem_object: A unified_planning.model.Problem instance
    """
    reader = PDDLReader()
    problem = reader.parse_problem(domain_path, problem_path)
    return problem

def generate_plan(problem_object):
    """
    Generate a plan for the given planning problem using a classical planner.

    Parameters:
        problem_object: A unified planning problem instance

    Returns:
        plan_object: A sequential plan or None if no plan exists
    """
    with OneshotPlanner(name='pyperplan') as planner:
        result = planner.solve(problem_object)
        if result.plan is not None:
            return result.plan
        else:
            return None

def validate(problem_object, plan_object):
    """
    Validate that a plan correctly solves the given PDDL problem.

    Parameters:
        problem_object: The planning problem
        plan_object: The generated plan

    Returns:
        bool: True if the plan is valid, False otherwise
    """
    if plan_object is None:
        return False

    with PlanValidator(problem_kind=problem_object.kind) as validator:
        result = validator.validate(problem_object, plan_object)
        return result.status.name == 'VALID'

def save_plan(plan_object, output_path):
    """
    Write a plan object to disk in standard PDDL plan format.

    Parameters:
        plan_object: A unified planning plan
        output_path (str): Output file path
    """
    if plan_object is None:
        with open(output_path, 'w') as f:
            f.write("")
        return

    # Convert plan to text format
    plan_lines = []
    for action in plan_object.actions:
        # Format: action_name(param1, param2, ...)
        action_str = str(action)
        plan_lines.append(action_str)

    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(plan_lines))
        if plan_lines:
            f.write('\n')

def main():
    """Main function to solve TPP task"""
    import argparse

    parser = argparse.ArgumentParser(description='Solve PDDL planning problem')
    parser.add_argument('--domain', required=True, help='Path to domain file')
    parser.add_argument('--problem', required=True, help='Path to problem file')
    parser.add_argument('--output', required=True, help='Path to output plan file')

    args = parser.parse_args()

    print(f"Loading domain: {args.domain}")
    print(f"Loading problem: {args.problem}")

    # Load problem
    problem = load_problem(args.domain, args.problem)
    print(f"Problem loaded successfully")

    # Generate plan
    print("Generating plan...")
    plan = generate_plan(problem)

    if plan is None:
        print("No plan found!")
        save_plan(None, args.output)
        sys.exit(1)

    print(f"Plan generated with {len(plan.actions)} actions")

    # Validate plan
    print("Validating plan...")
    is_valid = validate(problem, plan)

    if not is_valid:
        print("ERROR: Generated plan is invalid!")
        sys.exit(1)

    print("Plan is valid!")

    # Save plan
    print(f"Saving plan to: {args.output}")
    save_plan(plan, args.output)
    print("Plan saved successfully!")

    return 0

if __name__ == "__main__":
    sys.exit(main())
