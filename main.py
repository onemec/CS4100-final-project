import json
import networkx as nx
import matplotlib.pyplot as plt

# Parse the JSON data
with open("Computer_Science_BACS-2022.json", "r") as json_file:
    data = json.load(json_file)

# Create a directed graph
course_graph = nx.DiGraph()


def handle_requirements(requirements, parent_node):
    for requirement in requirements:
        if requirement["type"] == "COURSE":
            # Add course node to the graph
            course_graph.add_node(
                requirement["classId"], subject=requirement["subject"]
            )

            # Add an edge from the parent node to the course node
            course_graph.add_edge(parent_node, requirement["classId"])
        elif requirement["type"] in ["AND", "OR", "XOM"]:
            if "courses" in requirement:
                for course in requirement["courses"]:
                    handle_requirements([course], parent_node)


# Accessing 'requirementSections'
requirement_sections = data["requirementSections"]

for section in requirement_sections:
    section_title = section["title"]
    print("\nSection Title:", section_title)
    print("Minimum Requirement Count:", section["minRequirementCount"])

    requirements = section["requirements"]

    # Create a node for the section title
    course_graph.add_node(section_title, node_type="section")

    handle_requirements(requirements, section_title)

# Visualize the course graph (optional)
# You might need to adjust the layout depending on the graph size
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
