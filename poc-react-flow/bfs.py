from collections import deque


def bfs (graph: list[list[int]]) -> list[int]:
    size = len(graph)
    visited = [False] * size
    res = []

    src = 0
    q = deque()
    visited[src] = True
    q.append(src)

    while q:
        current = q.popleft()
        res.append(current)
        for neighbor in graph[current]:
            if not visited[neighbor]:
                q.append(neighbor)
                visited[neighbor] = True

    return res


def addEdge(adj, u, v):
    adj[u].append(v)
    adj[v].append(u)


if __name__ == "__main__":
    V = 5
    adj = []

    # creating adjacency list
    for i in range(V):
        adj.append([])

    addEdge(adj, 1, 2)
    addEdge(adj, 1, 0)
    addEdge(adj, 2, 0)
    addEdge(adj, 2, 3)
    addEdge(adj, 2, 4)

    res = bfs(adj)

    for node in res:
        print(node, end=" ")
