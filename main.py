import json
from enum import Enum
from typing import List, Union, Optional, Tuple
import networkx as nx
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

FULL_COURSE_LOAD_CREDITS = 18


class RequirementType(str, Enum):
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
    prereqs: Union[
        Tuple[
            str,
            Union[Course, "FullCourse", "OrRequirement", "AndRequirement", "Section"],
        ],
        None,
    ]
    coreqs: Union[
        Tuple[
            str,
            Union[Course, "FullCourse", "OrRequirement", "AndRequirement", "Section"],
        ],
        None,
    ]


class AndRequirement(Requirement):
    type: RequirementType = RequirementType.AND
    values: Union[
        List[Union[Course, FullCourse, "OrRequirement", "AndRequirement", "Section"]],
        None,
    ]


class OrRequirement(Requirement):
    type: RequirementType = RequirementType.OR
    values: Union[
        List[Union[Course, FullCourse, "OrRequirement", AndRequirement, "Section"]],
        None,
    ]


class Section(BaseModel):
    type: RequirementType = RequirementType.SECTION
    title: str
    values: Union[
        List[Union[Course, FullCourse, OrRequirement, AndRequirement, "Section"]], None
    ] = Field(alias="requirements")


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


def add_course_to_graph():
    pass


def add_and_or_to_graph():
    pass


def node_to_name(
    node: Union[Course, FullCourse, OrRequirement, AndRequirement, Section],
    parent_node_name: str,
    i: int,
    graph,
) -> tuple[str, int]:
    if isinstance(node, dict):
        model = create_model_by_type(node)
        return node_to_name(
            node=model, parent_node_name=parent_node_name, i=i, graph=graph
        )
    node_from_graph = get_node_from_graph(node, graph)
    if node_from_graph is not None:
        return node_from_graph, i
    if isinstance(node, (Course, FullCourse)):
        return f"{node.subject} {node.classId}", i
    if isinstance(node, (OrRequirement, AndRequirement)):
        return f"{parent_node_name}_{node.type.value}_{i}", i + 1
    if isinstance(node, Section):
        return f"{node.title}", i


def get_node_from_graph(node_data, graph):
    similar_node = None
    for node in graph.nodes(data=True):
        data = node[1].get("data")
        if data:
            if isinstance(data, (Course, FullCourse)) and isinstance(
                node_data, (Course, FullCourse)
            ):
                if (
                    data.subject == node_data.subject
                    and data.classId == node_data.classId
                ):
                    similar_node = node[0]
                    break
            elif data == node_data:
                similar_node = node[0]
                break
    return similar_node


def add_node_with_check(
    graph, node_data, node_name, parent_node, relation, prerequisites
):
    if similar_node := get_node_from_graph(node_data, graph):
        graph.add_edge(parent_node, similar_node, relation=relation)
        if relation == "coreq":
            graph.add_edge(similar_node, parent_node, relation=relation)
    else:
        graph.add_node(node_name, data=node_data)
        graph.add_edge(parent_node, node_name, relation=relation)
        if relation == "coreq":
            graph.add_edge(node_name, parent_node, relation=relation)
            handle_requirements(graph, [node_data], parent_node, prerequisites)


def handle_requirements(
    graph: nx.DiGraph,
    requirements: Optional[
        List[Union[Course, FullCourse, OrRequirement, AndRequirement, Section]]
    ],
    parent_node: str,
    prerequisites: dict,
):
    if not requirements or len(requirements) == 0:
        return graph

    i = 0
    for requirement in requirements:
        if isinstance(requirement, (Course, FullCourse)):
            for entry in prerequisites:
                if (
                    entry.get("subject") == requirement.subject
                    and int(entry.get("classId")) == requirement.classId
                ):
                    prereqs = None
                    coreqs = None
                    full_course_name = f"{requirement.subject} {requirement.classId}"
                    if entry.get("prereqs", {}).get("values"):
                        prereqs = (
                            create_model_by_type(entry.get("prereqs", {}))
                            if isinstance(entry.get("prereqs", {}), dict)
                            else entry.get("prereqs", {})
                        )
                    if entry.get("coreqs", {}).get("values"):
                        coreqs = (
                            create_model_by_type(entry.get("coreqs", {}))
                            if isinstance(entry.get("coreqs", {}), dict)
                            else entry.get("coreqs", {})
                        )
                    full_course = FullCourse(
                        classId=requirement.classId,
                        subject=requirement.subject,
                        credits=(
                            int(entry.get("maxCredits")) + int(entry.get("minCredits"))
                        )
                        // 2,
                        prereqs=prereqs
                        if entry.get("prereqs", {}).get("values")
                        else None,
                        coreqs=coreqs
                        if entry.get("coreqs", {}).get("values")
                        else None,
                    )

                    if full_course_name not in graph:
                        graph.add_node(full_course_name, data=full_course)
                    else:
                        graph.nodes[full_course_name]["data"] = full_course
                    graph.add_edge(parent_node, full_course_name, relation="req")

                    if full_course.coreqs and full_course.coreqs[1]:
                        add_node_with_check(
                            graph,
                            full_course.coreqs[0],
                            coreqs[0],
                            full_course_name,
                            "coreq",
                            prerequisites,
                        )
                        graph.add_edge(full_course_name, coreqs[0], relation="coreq")

                    if full_course.prereqs and full_course.prereqs[1]:
                        add_node_with_check(
                            graph,
                            full_course.prereqs[0],
                            prereqs[0],
                            full_course_name,
                            "req",
                            prerequisites,
                        )
                        graph.add_edge(prereqs[0], full_course_name, relation="req")

        elif isinstance(requirement, (AndRequirement, OrRequirement)):
            new_node = f"{parent_node}_{requirement.type.value}_{i}"
            i += 1
            graph.add_node(new_node, data=requirement)
            graph.add_edge(parent_node, new_node, relation="req")
            handle_requirements(
                graph,
                requirement.values.copy(),
                new_node,
                prerequisites,
            )
    return graph


def remaining_incomplete_requirements(c_graph: nx.DiGraph, taken_courses: list[Course]):
    unsatisfied_categories = 0
    shortest_fulfillment = []

    for requirement in c_graph.nodes(data=True):
        node_type = requirement[1].get("node_type")
        if node_type == RequirementType.SECTION.value:
            requirements = [
                taken_course
                for taken_course in c_graph.successors(requirement[0])
                if taken_course not in taken_courses and "_" not in taken_course
            ]

            if any(requirements):
                unsatisfied_categories += 1
                shortest_fulfillment.append(min(requirements, default=0))

    return unsatisfied_categories, shortest_fulfillment


def check_if_requirements_met(
    classes_taken: List[str], requirement: Union[str, None], c_graph: nx.DiGraph
) -> bool:
    if requirement is None:
        return True
    if isinstance(requirement, FullCourse):
        return requirement.prereqs is None or check_if_requirements_met(
            classes_taken, requirement.prereqs[0], c_graph
        )

    elif isinstance(requirement, Course):
        return any(
            course.split()[0] == requirement.subject
            and course.split()[1] == requirement.classId
            for course in classes_taken
        )

    requirement_value = None
    for node, data in c_graph.nodes(data=True):
        if requirement == node:
            requirement_value = data.get("data")

    if isinstance(requirement_value, AndRequirement):
        return all(
            check_if_requirements_met(classes_taken, req, c_graph)
            for req in requirement_value.values
        )

    elif isinstance(requirement_value, OrRequirement):
        return any(
            check_if_requirements_met(classes_taken, req, c_graph)
            for req in requirement_value.values
        )

    elif isinstance(requirement_value, Section):
        return all(
            check_if_requirements_met(classes_taken, req, c_graph)
            for req in requirement_value.values
            if req is not None
        )

    return False


def create_model_by_type(requirement: dict):
    if requirement == "Graduate Admission":
        return
    elif isinstance(requirement, dict):
        req_type = requirement.get("type", RequirementType.COURSE)

        if "courses" in requirement:
            requirement["values"] = [
                create_model_by_type(course)
                for course in requirement.pop("courses")
                if isinstance(course, dict)
            ]
        elif "values" in requirement:
            if (
                requirement["values"]
                and len(requirement["values"]) > 0
                and isinstance(requirement["values"][0], dict)
            ):
                requirement["values"] = [
                    create_model_by_type(course)
                    for course in requirement["values"]
                    if isinstance(course, dict)
                ]
        if req_type in ["or", "and"]:
            requirement["type"] = (
                RequirementType.OR.value
                if req_type == "or"
                else RequirementType.AND.value
            )
        if req_type == RequirementType.COURSE:
            return Course(**requirement)
        elif req_type == RequirementType.FULL_COURSE:
            return FullCourse(**requirement)
        elif req_type == RequirementType.SECTION:
            return Section(**requirement)
        elif req_type == RequirementType.OR:
            return OrRequirement(**requirement)
        elif req_type == RequirementType.AND:
            return AndRequirement(**requirement)
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
        if section["title"] != "Khoury Elective Courses":
            c_graph.add_node(
                section["title"],
                data=Section.model_validate(
                    {
                        "title": section["title"],
                        "requirements": [
                            create_model_by_type(entry)
                            for entry in section.get("requirements", [])
                        ],
                    }
                ),
                node_type=RequirementType.SECTION.value,
            )
            reqs = [create_model_by_type(req) for req in section.get("requirements")]
            c_graph = handle_requirements(
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


def heuristic(c_graph: nx.DiGraph, starting_courses: list, nodes: list) -> float:
    prev_unsat_categories, _ = remaining_incomplete_requirements(
        c_graph, starting_courses
    )
    (
        now_unsat_categories,
        now_best_for_each_category,
    ) = remaining_incomplete_requirements(c_graph, starting_courses + nodes)

    # Estimate remaining semesters with an average of 4 courses per semester
    remaining_semesters = max(now_unsat_categories - prev_unsat_categories, 0) / 4

    # Convert the credits taken into a "semester" unit by dividing by 18 (credits per semester)
    credits_taken = sum(
        c_graph.nodes[course]["data"].credits
        if isinstance(c_graph.nodes[course]["data"], FullCourse)
        else 0
        for course in (starting_courses + nodes)
        if isinstance(course, str) and course in c_graph.nodes
    )
    credits_difference = max(0, credits_taken - FULL_COURSE_LOAD_CREDITS)
    return remaining_semesters - credits_difference / 18.0


def a_star(c_graph: nx.DiGraph, starting_courses: list, required_credits: int):
    courses_to_take = []
    credits_taken = 0

    while credits_taken < required_credits:
        best_course = None
        best_heuristic = float("inf")
        best_cost = 0

        for course, course_data in c_graph.nodes(data=True):
            if course in courses_to_take:
                continue
            full_course = course_data.get("data")
            if (
                isinstance(full_course, FullCourse)
                and (course not in courses_to_take)
                and (
                    full_course.prereqs is None
                    or check_if_requirements_met(
                        classes_taken=starting_courses,
                        requirement=full_course.prereqs[0],
                        c_graph=c_graph,
                    )
                )
            ):
                coreq_course_names = [
                    coreq
                    for _, coreq, d in c_graph.edges(course, data=True)
                    if d.get("relation") == "coreq"
                ]
                coreqs_met = all(
                    check_if_requirements_met(
                        classes_taken=(starting_courses + courses_to_take),
                        requirement=c_graph.nodes[coreq_course].get("coreqs"),
                        c_graph=c_graph,
                    )
                    for coreq_course in coreq_course_names
                )

                prereqs_met = all(
                    check_if_requirements_met(
                        classes_taken=starting_courses,
                        requirement=c_graph.nodes[coreq_course].get("prereqs"),
                        c_graph=c_graph,
                    )
                    for coreq_course in coreq_course_names
                )

                cost_in_credits = sum(
                    course_graph.nodes[course]["data"].credits
                    if isinstance(course_graph.nodes[course]["data"], FullCourse)
                    else 0
                    for course in (coreq_course_names + [course])
                    if isinstance(course, str) and course in c_graph.nodes
                )

                if (
                    prereqs_met
                    and coreqs_met
                    and course not in (starting_courses + courses_to_take)
                    and credits_taken + cost_in_credits <= FULL_COURSE_LOAD_CREDITS
                ):
                    hs = heuristic(
                        c_graph, starting_courses, [course] + coreq_course_names
                    )
                    if hs < best_heuristic:
                        best_heuristic = hs
                        best_course = course
                        best_cost = cost_in_credits
        if best_course:
            courses_to_take.append(best_course)
            credits_taken += best_cost
        else:
            break

    return courses_to_take, credits_taken


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

sections = {entry.get("title") for entry in json_data.get("requirementSections")}
# print("What concentration are you?")
# concentration_section = "Artificial Intelligence"
#
# # Check if "concentrations" key exists and is a dictionary
# if "concentrations" in json_data and isinstance(json_data["concentrations"], dict):
#     concentration_options = json_data["concentrations"].get("concentrationOptions")
#     if isinstance(concentration_options, list):
#         for concentration in concentration_options:
#             if concentration.get("title") == concentration_section:
#                 print(concentration)
#                 break
# else:
#     print("No concentration information found in JSON data.")

req_sec = [entry.get("title") for entry in json_data.get("requirementSections")]
overall_sections = sorted(
    [
        course_graph.nodes[node].get("data")
        for node in course_graph.nodes
        if node in req_sec
    ],
    key=lambda x: x.title,
)

taken_courses = []
semester = 0
while not all(
    check_if_requirements_met(
        classes_taken=taken_courses,
        requirement=requirement_section,
        c_graph=course_graph,
    )
    for requirement_section in overall_sections
):
    newly_taken_courses, newly_taken_credits = a_star(
        course_graph,
        taken_courses,
        required_credits=json_data.get("totalCreditsRequired"),
    )
    print(f"Semester {semester} ({newly_taken_credits} credits): {newly_taken_courses}")
    semester += 1
    taken_courses = taken_courses.copy() + newly_taken_courses
    if newly_taken_credits == 0:
        break
