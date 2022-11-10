from .nodes import Node, ValueNode, Edge, FunctionCall
import subprocess
from typing import Any


class DAG:
    def __init__(self):
        root = Node("__root__", [])
        self.root = root
        self.__nodes: dict[str, Node] = {"__root__": root}
        self.edges: list[Edge] = []
        self.path_edges: list[Edge] = []

    def plot(self):
        try:
            import networkx as nx
        except ImportError:
            print(
                "Networkx is not installed. Please install networkx to use this feature."
            )
            return
        import matplotlib.pyplot as plt

        G = nx.DiGraph()
        G.add_nodes_from(self.__nodes.keys())
        G.add_edges_from([(e.from_key, e.to_key) for e in self.edges])
        nx.draw(G, with_labels=True)
        # plt.show()
        plt.savefig("graph.png")

    @property
    def nodes(self):
        return list(self.__nodes.values())

    def print(self, path_network=False):
        edges = None
        if path_network:
            edges = self.path_edges
        else:
            edges = self.edges
        prompt = "\n".join(str(e) for e in edges)
        command = f"echo '{prompt}' | diagon GraphDAG"
        return subprocess.check_output(command, shell=True).decode("utf-8")

    def __str__(self):
        return self.print()

    def __repr__(self):
        return self.__str__()

    def prune(self):
        pass

    def add_node(self, node: Node):
        assert isinstance(node, Node), f"Expected Node, got {type(node)}"
        assert (
            not node in self
        ), f"Node with object_key={node.object_key} already present"
        self.__nodes[node.object_key] = node

    def add_path_edge(self, from_node: Node | str | None, to_node: Node | str):
        from_node = from_node if from_node is not None else self["__root__"]
        edge = Edge(from_node, to_node)
        """
        assert (
            edge.from_key in self
        ), f"Error inserting edge, no node with object_key={edge.from_key}"
        assert (
            edge.to_key in self
        ), f"Error inserting edge, no node with object_key={edge.to_key}"
        """
        self.path_edges.append(edge)

    def add_edge(self, from_node: Node | str, to_node: Node | str, path: list[str]):
        edge = Edge(from_node, to_node, path)
        assert not edge in self, "Tried to insert twice the same edge"
        """
        assert (
            edge.from_key in self
        ), f"Error inserting edge, no node with object_key={edge.from_key}"
        assert (
            edge.to_key in self
        ), f"Error inserting edge, no node with object_key={edge.to_key}"
        """
        self.edges.append(edge)

    def edges_to(self, key: str | Node) -> list[Edge]:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        return [edge for edge in self.edges if edge.to_key == object_key]

    def edges_from(self, key: str | Node) -> list[Edge]:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        return [edge for edge in self.edges if edge.from_key == object_key]

    def path_edge_to(self, key: str | Node) -> Edge | None:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        selected = [edge for edge in self.path_edges if edge.to_key == object_key]
        return selected[0] if len(selected) > 0 else None

    def path_edges_from(self, key: str | Node) -> list[Edge]:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        return [edge for edge in self.path_edges if edge.from_key == object_key]

    def roots(self) -> list[Node]:
        return [node for node in self.nodes if not self.edges_to(node)]

    def leaves(self) -> list[Node]:
        return [node for node in self.nodes if not self.edges_from(node)]

    def topological_sort(self) -> list[Node]:
        roots = self.roots()
        sorted_nodes: list[Node] = []
        visited = set()

        def visit(node: Node):
            if node.object_key in visited:
                return
            visited.add(node.object_key)
            for child in self.children(node):
                assert isinstance(child, Node)
                visit(child)
            sorted_nodes.append(node)

        for root in roots:
            assert isinstance(root, Node)
            visit(root)
        sorted_nodes.reverse()
        return sorted_nodes

    def parents(self, key: Node | str) -> list[Node]:
        return [self[e.from_key] for e in self.edges_to(key)]

    def path_parent(
        self, key: Node | str
    ) -> Node | None:  # path is a tree, so at most one parent (root doesn't count)
        edge = self.path_edge_to(key)
        if edge is None:
            return None
        return self[edge.from_key]

    def path_sort(self):
        roots = self.path_children(self.root)
        topological_sort = [n.object_key for n in self.topological_sort()]
        roots.sort(key=lambda x: topological_sort.index(x.object_key))
        roots = [n for n in self.nodes if isinstance(n, ValueNode)] + roots
        return roots

    def children(self, key: Node | str) -> list[Node]:
        return [self[e.to_key] for e in self.edges_from(key)]

    def object_keys(self) -> list[str]:
        return [node.object_key for node in self.__nodes.values()]

    def remove_node(self, node: Node | str):
        object_key = node if isinstance(node, str) else node.object_key
        assert object_key in self, f"No node with {object_key=}"
        del self.__nodes[object_key]
        children = self.children(object_key)
        self.edges = [edge for edge in self.edges if edge.from_key != object_key]
        for child in children:
            self.remove_node(child)

    def replace_node(self, node: Node, with_node: Node | str):
        object_key = node if isinstance(node, str) else node.object_key
        assert object_key in self, f"No node with {object_key=}"
        for child in self.children(object_key):
            self.remove_node(child)

    def __getitem__(self, object_key: str) -> Node:
        assert object_key in self, f"No node with {object_key=}"
        return self.__nodes[object_key]

    def __contains__(self, other: Edge | Node | str):
        if isinstance(other, Edge):
            return (
                len(
                    tuple(
                        e
                        for e in self.edges
                        if e.from_key == other.from_key and e.to_key == other.to_key
                    )
                )
                > 0
            )
        else:
            object_key = other if isinstance(other, str) else other.object_key
            return object_key in self.__nodes

    def path_children(self, key: Node | str) -> list[Node]:
        return [self[e.to_key] for e in self.path_edges_from(key)]

    def to_dict(self):
        result = {
            val.object_key: val.to_dict()
            for val in self.path_sort()
            if not type(val) in (FunctionCall,) and not val.object_key == "save_dir"
        }
        return result

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    @staticmethod
    def _get_ref(val: str) -> str | None:
        # checks by using a regex if the string has a matching pattern like "{hello}"
        if isinstance(val, str):
            res = re.match(r"{\w+}", val)
            if res is None:
                return None
            else:
                span = res.span()
                return val[span[0] + 1 : span[1] - 1]
        return None
