JSON = {
    "nodes": [
        {
            "id": "N5",
            "type": "OUTPUT",
            "data": {"outputs": [{"field": "message", "type": "string"}]},
        },
        {
            "id": "N2",
            "type": "INPUT",
            "data": {
                "inputs": [
                    {"field": "name", "store_as": "user_name", "type": "string"},
                    {"field": "date_of_birth", "store_as": "dob", "type": "date"},
                ]
            },
        },
        {"id": "N7", "type": "END"},
        {
            "id": "N4",
            "type": "ACTION",
            "data": {
                "operation": "calculate_age",
                "inputs": {"dob": "dob"},
                "output": "age",
            },
        },
        {
            "id": "N6",
            "type": "OUTPUT",
            "data": {"outputs": [{"field": "age", "type": "integer"}]},
        },
        {"id": "N1", "type": "START"},
        {
            "id": "N3",
            "type": "ACTION",
            "data": {
                "operation": "greet",
                "inputs": {"name": "user_name"},
                "output": "message",
            },
        },
    ],
    "edges": [
        {"id": "E1", "source": "N1", "target": "N2"},
        {"id": "E2", "source": "N2", "target": "N3"},
        {"id": "E3", "source": "N2", "target": "N4"},
        {"id": "E4", "source": "N3", "target": "N5"},
        {"id": "E5", "source": "N4", "target": "N6"},
        {"id": "E6", "source": "N5", "target": "N7"},
        {"id": "E7", "source": "N6", "target": "N7"},
    ],
}

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

def compile(workflow: dict):
  node_map = generate_node_map(workflow)
  print(node_map)
  adjaceny = generate_adjaceny_list(workflow)
  print(adjaceny)
  starting_point = find_entrypoint(node_map)
  print(starting_point)

  graph = generate_graph_structure(starting_point, node_map, adjaceny)
  print_graph(graph)

  traversal_order = traverse_graph(graph)
  print(traversal_order)


if __name__ == "__main__":
  compile(JSON)
