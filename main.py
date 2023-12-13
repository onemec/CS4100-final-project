import json
from enum import Enum
from typing import List, Union, Optional
import networkx as nx
import matplotlib.pyplot as plt
import heapq
from pydantic import BaseModel
from pyparsing import Or


class RequirementType(str, Enum):
    ANY = "ANY"
    COURSE = "COURSE"
    SECTION = "SECTION"
    FULL_COURSE = "FULL_COURSE"
    AND = "AND"
    OR = "OR"


class Requirement(BaseModel):
    type: RequirementType


class Course(Requirement):
    type: RequirementType = RequirementType.COURSE
    subject: str
    classId: int


class FullCourse(Requirement):
    type: RequirementType = RequirementType.FULL_COURSE
    subject: str
    classId: int
    credits: int
    prereqs: Union[List[str], None]
    coreqs: Union[List[str], None]


class AndRequirement(Requirement):
    type: RequirementType = RequirementType.AND
    courses: Union[List[Requirement], None]


class OrRequirement(Requirement):
    type: RequirementType = RequirementType.OR
    courses: Union[List[Requirement], None]


class Section(BaseModel):
    type: RequirementType = RequirementType.SECTION
    title: str
    requirements: Union[List[Requirement], None]


def load_json(file_path: str) -> dict:
    """
    Load JSON data from a file.

    This function takes a file path as input and reads the contents of the file as JSON data. It returns the loaded JSON data.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        JSONDecodeError: If the file contents cannot be decoded as JSON.
    """
    with open(file_path, "r") as json_file:
        return json.load(json_file)


def handle_requirements(
    graph: nx.DiGraph,
    requirements: Optional[List[Requirement]],
    parent_node: str,
    prerequisites: dict,
) -> nx.DiGraph:
    # If there are no requirements, just return the current graph
    if not requirements or len(requirements) == 0:
        return graph

    i = 0
    for requirement in requirements:
        # If the requirement is a Course, parse it into a FullCourse
        if isinstance(requirement, (Course, FullCourse)):
            for entry in prerequisites:
                # If the current course entry matches the prerequisite
                if entry.get("subject") == requirement.subject and int(entry.get("classId")) == requirement.classId:
                    full_course = FullCourse(
                        classId=requirement.classId,
                        subject=requirement.subject,
                        credits=int(entry.get("maxCredits"))
                                | int(entry.get("minCredits")),
                        prereqs=[
                            f"{course.get('subject')} {course.get('classId')}"
                            for course in entry.get("prereqs", {}).get("values", [])
                            if course not in ["Graduate Admission"]
                        ],
                        coreqs=[
                            f"{course.get('subject')} {course.get('classId')}"
                            for course in entry.get("coreqs", {}).get("values", [])
                        ],
                    )
                    full_course_name = (
                        f"{full_course.subject} {full_course.classId}"
                    )
                    graph.add_node(full_course_name)
                    graph.add_edge(parent_node, full_course_name)
                    # Initially handle corequisites naively, then update them accordingly in recursive calls
                    for coreq_node in full_course.coreqs:
                        graph.add_node(coreq_node)
                        graph.add_edge(coreq_node, full_course_name, relation="coreq")

                    # If the prerequisites are AND type, create a single AND node, else it is an OR type, and any of the sub-nodes can satisfy
                    curr_name_as_parent = full_course_name
                    if entry.get("prereqs").get("type").upper() == RequirementType.AND.value:
                        curr_name_as_parent = f"{full_course.subject} {full_course.classId} {requirement.type}"
                        graph.add_node(curr_name_as_parent)

                    # Fixing the recursive call by passing the correct prerequisites
                    handle_requirements(
                        graph,
                        [
                            create_model_by_type(req)
                            for req in entry.get("prereqs", {}).get("values", [])
                        ],
                        curr_name_as_parent,
                        prerequisites,
                    )
                    handle_requirements(
                        graph,
                        [
                            create_model_by_type(req)
                            for req in entry.get("coreqs", {}).get("values", [])
                        ],
                        parent_node,
                        prerequisites,
                    )

        elif isinstance(requirement, (AndRequirement, OrRequirement, Section)):
            new_node = (
                f"{parent_node}_{requirement.type}_{i}"  # Create a new node for AND/OR
            )
            i += 1
            graph.add_node(new_node, node_type=requirement.type)
            graph.add_edge(parent_node, new_node)  # Connect parent node to AND/OR node
            for course_id in requirement.courses:
                handle_requirements(graph, [course_id], new_node, prerequisites)

    return graph


def remaining_incomplete_requirements(c_graph: nx.DiGraph, taken_courses: list[Course]):
    """
    Calculate the remaining incomplete requirements based on the courses taken.

    Args:
        c_graph: The graph representing the courses and their dependencies.
        taken_courses (list): The list of courses already taken.

    Returns:
        tuple: A tuple containing the number of unsatisfied categories and the shortest fulfillment for each category.
    """
    unsatisfied_categories = 0
    shortest_fulfillment = []

    for requirement in c_graph.nodes(data=True):
        node_type = requirement[1].get("node_type")
        if node_type == "section":
            requirements = [
                taken_course
                for taken_course in c_graph.successors(requirement[0])
                if taken_course not in taken_courses
            ]

            if any(requirements):
                unsatisfied_categories += 1
                shortest_fulfillment.append(min(requirements, default=0))

    return unsatisfied_categories, shortest_fulfillment


def create_model_by_type(requirement: dict):
    if requirement == 'Graduate Admission':
        return
    elif isinstance(requirement, dict):
        req_type = requirement.get("type")
        if req_type == RequirementType.COURSE:
            return Course.model_validate(requirement)
        elif req_type == RequirementType.FULL_COURSE:
            return FullCourse.model_validate(requirement)
        elif req_type == RequirementType.SECTION:
            return Section.model_validate(requirement)
        elif req_type == RequirementType.OR:
            return OrRequirement.model_validate(requirement)
        elif req_type == RequirementType.AND:
            return AndRequirement.model_validate(requirement)
    else:
        raise ValueError("Invalid requirement format:", requirement)


def create_course_graph(data: dict, prerequisites: dict) -> nx.DiGraph:
    """
    Create a graph of course requirements.

    Args:
        data (dict): Parsed JSON data
        prerequisites (dict): Prerequisite information for courses

    Returns:
        nx.DiGraph: NetworkX graph object representing course requirements
    """
    c_graph = nx.DiGraph()

    for section in data["requirementSections"]:
        c_graph.add_node(section["title"], node_type="section")
        reqs = [create_model_by_type(req) for req in section.get("requirements")]
        handle_requirements(
            c_graph, reqs, section["title"], prerequisites
        )

    return c_graph


def graph_courses(c_graph: nx.DiGraph):
    """
    Draws the course graph using NetworkX and MatPlotLib.

    Args:
        c_graph (nx.DiGraph): The course being visualized.

    Returns:
        None

    Raises:
        None
    """

    pos = nx.spring_layout(c_graph)
    nx.draw(
        c_graph,
        pos,
        with_labels=True,
        font_weight="bold",
        node_size=800,
        node_color="lightblue",
    )
    plt.show()


def heuristic(
    taken_courses: list[Course],
    c_graph: nx.DiGraph,
    neighboring_course: Course,
    required_credits: int,
):
    credits_taken_so_far = sum(course.credits for course in taken_courses)

    # Don't underestimate the cost to go
    heuristic_value = max(required_credits - credits_taken_so_far, 0)

    # Return if we've reached the goal
    if heuristic_value == 0:
        return 0

    # Count of how many unfilled requirements this fulfills (or contributes to fulfilling)

    # Figure out co-requisites

    # Number of courses this will "unlock"

    # Break ties with lower priority courses

    return heuristic_value


def a_star(c_graph: nx.DiGraph, starting_courses: set, required_credits: int):
    frontier = []
    starting_course = None
    for course in starting_courses:
        heapq.heappush(frontier, (0, course))
        if starting_course is None:
            starting_course = course

    while frontier:
        _, current = heapq.heappop(frontier)
        incomplete_req, available_per_section = remaining_incomplete_requirements(
            c_graph=c_graph, taken_courses=current
        )
        # Continue implementation here
    return None  # No path found


# Load pre-requisite data
prerequisite_data = load_json("prerequisite_data.json")
# Load JSON data
json_data = load_json("Computer_Science_BACS-2022.json")
# Create course graph
course_graph = create_course_graph(
    json_data, prerequisite_data.get("neu").get("classes")
)
# Visualize the graph
graph_courses(course_graph)
print(remaining_incomplete_requirements(c_graph=course_graph, taken_courses=[]))

sections = {entry.get("title") for entry in json_data.get("requirementSections")}
print("What concentration are you?")
concentration_section = "Artificial Intelligence"

# Check if "concentrations" key exists and is a dictionary
if "concentrations" in json_data and isinstance(json_data["concentrations"], dict):
    concentration_options = json_data["concentrations"].get("concentrationOptions")
    if isinstance(concentration_options, list):
        for concentration in concentration_options:
            if concentration.get("title") == concentration_section:
                print(concentration)
                break
else:
    print("No concentration information found in JSON data.")

a_star(
    course_graph,
    {entry.get("title") for entry in json_data.get("requirementSections")},
    required_credits=json_data.get("totalCreditsRequired"),
)
