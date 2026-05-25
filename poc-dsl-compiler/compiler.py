def generate_node_map(workflow: dict):
    node_map = {}

    for node in workflow["nodes"]:
        node_map[node["id"]] = node

    return node_map

def generate_adjaceny_list(workflow: dict):
    adjacency = {}

    for edge in workflow["edges"]:
        source = edge["source"]
        target = edge["target"]

        if source not in adjacency:
            adjacency[source] = []

        adjacency[source].append(target)

    return adjacency

def find_entrypoint(node_map: dict):
  for node_id, node in node_map.items():

    if node["type"] == "START":
      return node_id

  return "Entrypoint not found"

def generate_graph_structure(entrypoint, node_map, adjacency, graph=None):
    if graph is None:
        graph = {}

    if entrypoint in graph:
        return graph[entrypoint]

    graph[entrypoint] = {"node": node_map[entrypoint], "children": []}
    children = adjacency.get(entrypoint, [])

    for child in children:
        graph[entrypoint]["children"].append(
            generate_graph_structure(child, node_map, adjacency, graph)
        )

    return graph[entrypoint]

def print_graph(graph, level=0, visited=None):
    if visited is None:
        visited = set()

    node_id = graph["node"]["id"]
    prefix = "  " * level

    if node_id in visited:
        print(prefix + graph["node"]["type"] + " [REF]")
        return

    visited.add(node_id)
    print(prefix + graph["node"]["type"])

    for child in graph["children"]:
        print_graph(child, level + 1, visited)

def traverse_graph(graph, order=None, visited=None):
    if order is None:
        order = []

    if visited is None:
        visited = set()

    node_id = graph["node"]["id"]

    if node_id in visited:
        return order

    visited.add(node_id)

    order.append(graph["node"])

    for child in graph["children"]:
        traverse_graph(child, order, visited)

    return order

def run_compiler(workflow: dict) -> dict:
    """Compiler to generate Graph and Traversal Flow"""
    node_map = generate_node_map(workflow)
    adjacency = generate_adjaceny_list(workflow)
    starting_point = find_entrypoint(node_map)

    graph = generate_graph_structure(starting_point, node_map, adjacency)
    traversal = traverse_graph(graph)

    return {
        "node_map": node_map,
        "adjacency": adjacency,
        "graph": graph,
        "traversal": traversal,
    }
