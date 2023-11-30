import json
import networkx as nx
import matplotlib.pyplot as plt


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
    graph: nx.Graph, requirements: list, parent_node: str
) -> nx.Graph:
    """
    Handle requirements and build a graph representation.

    This function takes a graph, a list of requirements, and a parent node as input. It iterates over each requirement and adds course nodes to the graph if the requirement type is "COURSE". It also adds edges from the parent node to the course nodes. If the requirement type is "AND", "OR", or "XOM", and there are associated courses, it recursively calls itself with the courses as requirements. Finally, it returns the updated graph.

    Args:
        graph (nx.Graph): The graph object to which the nodes and edges will be added.
        requirements (list): A list of requirements.
        parent_node (str): The parent node to which the course nodes will be connected.

    Returns:
        nx.Graph: The updated graph object.

    Raises:
        None
    """
    for requirement in requirements:
        if requirement["type"] == "COURSE":
            graph.add_node(requirement["classId"], subject=requirement["subject"])
            graph.add_edge(parent_node, requirement["classId"])
        elif requirement["type"] in ["AND", "OR", "XOM"]:
            if "courses" in requirement:
                for course in requirement["courses"]:
                    handle_requirements(graph, [course], parent_node)
    return graph


def create_course_graph(data: dict) -> nx.Graph:
    """
    Create a graph of course requirements.

    Args:
        data (dict): Parsed JSON data

    Returns:
        nx.Graph: NetworkX graph object representing course requirements
    """
    course_graph = nx.DiGraph()

    requirement_sections = data["requirementSections"]

    for section in requirement_sections:
        section_title = section["title"]
        course_graph.add_node(section_title, node_type="section")
        handle_requirements(course_graph, section["requirements"], section_title)

    return course_graph


def visualize_course_graph(course_graph: nx.Graph):
    """
    Visualize the course graph.

    This function takes a course graph as input and visualizes it using the NetworkX library. It uses the spring layout algorithm to position the nodes and draws the graph with node labels, bold font weight, and light blue node color. The visualization is displayed using matplotlib.

    Args:
        course_graph (nx.Graph): The course graph to be visualized.

    Returns:
        None

    Raises:
        None
    """

    pos = nx.spring_layout(course_graph)
    nx.draw(
        course_graph,
        pos,
        with_labels=True,
        font_weight="bold",
        node_size=800,
        node_color="lightblue",
    )
    plt.show()


# Load JSON data
json_data = load_json("Computer_Science_BACS-2022.json")
# Create course graph
course_graph = create_course_graph(json_data)
# Visualize the graph
visualize_course_graph(course_graph)
