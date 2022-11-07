from typing import Any
from abc import ABC, abstractmethod
import os
import re
import random
import json
import ipdb
import subprocess


# TODO: merge these nodes with the ones defined in the other file
class Node:
    def __init__(
        self,
        object_key: str,
        path: list[str],
        params: None | dict[str, Any] = None,
        class_type: str | None = None,
        module: None | str = None,
        class_name: None | str = None,
    ):
        self.object_key = object_key
        self.module = module
        self.params: dict[str, Any] = params if params is not None else {}
        self.path = path
        assert not (
            (class_type is not None) and (class_name is not None)
        ), f"Node {object_key} has both 'class_name' and 'class_type' defined. This is not allowed."
        if (class_type is not None) or (class_name is not None):
            assert (
                module is not None
            ), f"Node {object_key} has 'class_name' or 'class_type' defined, but no 'module' defined. This is not allowed."

    def to_dict(self) -> dict[str, Any]:
        def get_bombilla_dict(obj: Any) -> Any:
            if type(obj) in (str, int, float, bool, type(None)):
                return obj
            elif isinstance(obj, list):
                return [get_bombilla_dict(el) for el in obj]
            elif isinstance(obj, dict):
                return {key: get_bombilla_dict(val) for key, val in obj.items()}
            else:
                assert isinstance(obj, Node), f"{type(obj)} is not a valid type for a Node"
                return {k: get_bombilla_dict(v) for k, v in obj.__dict__.items() if k != "path" and not (isinstance(v, str) and v.startswith("_"))}

        result = get_bombilla_dict(self)
        assert isinstance(result, dict)
        return result

    def __repr__(self):
        return json.dumps(self.to_dict(), indent=4)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Node) and self.to_dict() == other.to_dict()

    def assign(self, path: list[str], obj: Any):
        relative_path = Node.__relative_path(self.path[-1], path)
        Node.__assign(self, relative_path, obj)

    @staticmethod
    def __relative_path(value: str, path: list[str]) -> list[str]:
        last_occurrence = len(path) - 1 - path[::-1].index(value)
        return path[last_occurrence + 1 :]

    @staticmethod
    def __assign(target: Any, path: list[str], obj: Any):
        if len(path) == 0:
            return
        if isinstance(target, list) or path[0].isdigit():
            to_set = target
            current_key = int(path[0])
            if len(path) == 1:
                to_set[current_key] = obj
                return
            next_obj = to_set[current_key]
        elif isinstance(target, dict):
            to_set = target
            current_key = path[0]
            if len(path) == 1:
                to_set[current_key] = obj
                return
            next_obj = to_set[current_key]
        else:
            to_set = target.__dict__
            current_key = path[0]
            if len(path) == 1:
                to_set[current_key] = obj
                return
            next_obj = to_set[current_key]
        Node.__assign(next_obj, path[1:], obj)

    @staticmethod
    def _rand_hex(length: int) -> str:
        randint = random.randint(0, 16**length - 1)
        return hex(randint)[2:].zfill(length)

    @abstractmethod
    def to_py(self, at_root:bool=False) -> str:
        return "None"

    def _render_val(self, val: Any):
        if isinstance(val, str):
            match = re.match(r"{\w+}", val)
            if match is not None:
                span = match.span()
                found = val[span[0] + 1 : span[1] - 1]
                if len(found) == (len(val) - 2):
                    return found
                else:
                    return f'''f"{val}"'''
            return f'"{val}"'
        elif isinstance(val, Node):
            return val.to_py()
        elif isinstance(val, list):
            return f"[{','.join([self._render_val(el) for el in val])}]"
        elif isinstance(val, dict):
            return f"{{{','.join([f'{k}:{self._render_val(v)}' for k, v in val.items()])}}}"
        else:
            return str(val)

    def _render_params(self, params: dict[str, Any]):
        return ",".join([f"{k}={self._render_val(v)}" for k, v in params.items()])


class ClassTypeNode(Node):
    def __init__(
        self,
        path: list[str],
        class_type: str,
        module: str,
        params: None | dict[str, Any] = None,
    ):
        self.class_type = class_type
        super().__init__(object_key=f"_{self.class_type}", path=path, params=params, module=module)

    def to_py(self, at_root:bool = False) -> str:
        return self.class_type


class ClassNameNode(Node):
    def __init__(
        self,
        *,
        path: list[str],
        class_name: str,
        module: str,
        object_key: str | None = None,
        params: None | dict[str, Any] = None,
    ):
        self.class_name = class_name
        # puts new_obj_key from PascalCase to snake_case
        object_key = (
            object_key
            if object_key is not None
            else (
                f"_{class_name}_{Node._rand_hex(3)}"
            )
        )
        super().__init__(object_key=object_key, path=path, params=params, module=module)

    def to_py(self, at_root:bool=False) -> str:
        return f"{self.class_name}({self._render_params(self.params)})"


class ValueNode(Node):
    def __init__(self, object_key: str, path: list[str]):
        super().__init__(object_key, path)
        self.module = "os.environ"
        self.class_name = "get"
        self.__key = self.object_key.upper()

    def to_py(self, at_root:bool=False):
        if at_root:
            return f"{self.object_key}:str = get('{self.__key}')"
        else:
            return self.object_key


class FunctionCall(Node):
    def __init__(
        self,
        reference_key: str,
        function_call: str,
        path: list[str],
        params: dict[str, Any] | None = None,
    ):
        self.reference_key = reference_key
        self.function_call = function_call
        self.params = params if params is not None else {}
        object_key = f"_{reference_key}.{function_call}(..)_{Node._rand_hex(3)}"
        super().__init__(object_key=object_key, path=path)

    def to_py(self, at_root:bool=False):
        params = self._render_params(self.params)
        return f"{self.reference_key}.{self.function_call}({params})"


class ReturnNode(Node):
    def __init__(self, object_key: str, path: list[str]):
        super().__init__(object_key=object_key, path=path)
        self.execution_cue: list[FunctionCall | None] = []

    def __getitem__(self, key: int) -> FunctionCall:
        result = self.execution_cue[key]
        assert result is not None
        return result

    def __setitem__(self, key: int, value: FunctionCall):
        if key + 1 > len(self.execution_cue):
            self.execution_cue.extend([None] * (key - len(self.execution_cue) + 1))
        self.execution_cue[key] = value

    def to_py(self, at_root:bool=False):
        return f"[{','.join([f'{el.to_py()}' for el in self.execution_cue if el is not None])}]"


class Edge:
    def __init__(self, from_node: str | Node, to_node: str | Node, path: list[str]):
        self.from_key = (
            from_node if isinstance(from_node, str) else from_node.object_key
        )
        self.to_key = to_node if isinstance(to_node, str) else to_node.object_key
        assert (
            self.to_key != self.from_key
        ), f"Tried to reference {self.from_key} to itself. Self-references are not allowed."
        self.path = path

    def to_json(self):
        return self.__dict__

    def __repr__(self):
        return f"{self.from_key} -> {self.to_key}"

    def __str__(self):
        return self.__repr__()


class BombillaDAG:
    def __init__(self, bombilla: dict[str, Any] | str):
        if isinstance(bombilla, str):
            with open(bombilla, "r") as f:
                bombilla = json.load(f)
        self.__nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.__load_nodes(bombilla, [], None)

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

    def __str__(self):
        prompt = "\n".join(str(e) for e in self.edges)
        command = f"echo '{prompt}' | diagon GraphDAG"
        # runs the command and returns the output
        return subprocess.check_output(command, shell=True).decode("utf-8")

    def __repr__(self):
        return self.__str__()

    def __load_nodes(self, bomb: Any, path: list[str], parent: Node | None):
        if self.__is_simple_type(bomb):
            assert (
                parent is not None
            ), (
                ipdb.set_trace()
            )  # "Parent is None"  # remove this to add support for simple types as nodes
            ref = self.__get_ref(bomb)
            if ref is not None:
                if ref not in self:
                    self.add_node(ValueNode(ref, path))
                self.add_edge(Edge(ref, parent, path))  # done
            # if isinstance(bomb, str) and "save_dir" in bomb:
            #     ipdb.set_trace()
            parent.assign(path, bomb)
        elif BombillaDAG.__is_return(bomb):
            parent = ReturnNode(object_key=path[-1], path=path)
            self.add_node(parent)
            assert isinstance(bomb, list)
            assert len(path) == 1
            for i, child in enumerate(bomb):
                self.__load_nodes(child, path + [str(i)], parent)
        elif isinstance(bomb, list):
            for index, item in enumerate(bomb):
                self.__load_nodes(item, path + [str(index)], parent)
        elif isinstance(bomb, dict):
            if BombillaDAG.__is_method_args(bomb):
                assert "params" in bomb
                for key, val in bomb["params"].items():
                    self.__load_nodes(val, path + ["params", key], parent)
            if BombillaDAG.__is_function_call(bomb):
                if parent is None:
                    parent = Node(
                        object_key=path[0],
                        path=path,
                    )
                    self.add_node(parent)

                assert parent is not None
                assert "function_call" in bomb
                assert "reference_key" in bomb
                assert "params" in bomb
                function_call = FunctionCall(
                    reference_key=bomb["reference_key"],
                    function_call=bomb["function_call"],
                    path=path,
                    params=bomb["params"],
                )
                self.add_node(function_call)
                self.add_edge(
                    Edge(
                        from_node=bomb["reference_key"],  # bomb["reference_key"],
                        to_node=function_call,
                        path=path,
                    )
                )
                self.add_edge(Edge(function_call, parent, path))
                parent.assign(path, function_call)
                assert isinstance(bomb["params"], dict)
                for key, val in bomb["params"].items():
                    self.__load_nodes(val, path + ["params", key], function_call)
            elif BombillaDAG.__is_module(bomb):
                node: Node | None = None
                # if bomb["object_key"] == "classifier":
                #     ipdb.set_trace()
                if ((not len(path)) >= 2) and (path[-2] == "params"):
                    bomb["object_key"] = path[-2] + "_" + self.__rand_hex(5)
                # if "object_key" not in bomb:
                #     bomb["object_key"] = "node_" + self.__rand_hex(4)
                if "class_name" in bomb:
                    assert (
                        "class_type" not in bomb
                    ), "class_name and class_type cannot be both present"
                    node = ClassNameNode(
                        object_key=bomb.get("object_key"),
                        class_name=bomb["class_name"],
                        module=bomb["module"],
                        path=path,
                        params=bomb.get("params"),
                    )
                else:
                    assert (
                        "class_name" not in bomb
                    ), "class_name and class_type cannot be both present"
                    node = ClassTypeNode(
                        class_type=bomb["class_type"],
                        module=bomb["module"],
                        path=path,
                    )
                node = (
                    node
                    if node is not None
                    else Node(
                        object_key=bomb["object_key"],
                        path=path,
                        params=bomb.get("params"),
                    )
                )
                assert node is not None
                self.add_node(node)
                if parent is not None:
                    parent.assign(path, node)  # "{" + bomb["object_key"] + "}")
                    self.add_edge(Edge(node, parent, path))  # done
                bomb["path"] = path
                # self.add_node(parent)
                if "params" in bomb:
                    for key, val in bomb["params"].items():
                        self.__load_nodes(val, path + ["params", key], node)

                if "method_args" in bomb:
                    for key, val in enumerate(bomb["method_args"]):
                        self.__load_nodes(val, path + ["method_args", str(key)], node)

            else:
                for key, val in bomb.items():
                    self.__load_nodes(val, path + [key], parent)
        else:
            if not path[-1] == "params":
                for key, val in bomb.items():
                    self.__load_nodes(val, path + [key], parent)

    def add_node(self, node: Node):
        assert (
            not node in self
        ), f"Node with object_key={node.object_key} already present"
        self.__nodes[node.object_key] = node

    def add_edge(self, edge: Edge):
        assert not edge in self, "Tried to insert twice the same edge"
        assert (
            edge.from_key in self
        ), f"Error inserting edge, no node with object_key={edge.from_key}"
        assert (
            edge.to_key in self
        ), f"Error inserting edge, no node with object_key={edge.to_key}"
        self.edges.append(edge)

    def edges_to(self, key: str | Node) -> list[Edge]:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        return [edge for edge in self.edges if edge.to_key == object_key]

    def edges_from(self, key: str | Node) -> list[Edge]:
        object_key = key if isinstance(key, str) else key.object_key
        assert object_key in self, f"No node with {object_key=}"
        return [edge for edge in self.edges if edge.from_key == object_key]

    def roots(self, keys_only: bool = False) -> list[Node] | list[str]:
        result = [node for node in self.nodes if not self.edges_to(node)]
        if keys_only:
            return [node.object_key for node in result]
        return result

    def leaves(self, keys_only: bool = False) -> list[Node] | list[str]:
        result = [node for node in self.nodes if not self.edges_from(node)]
        if keys_only:
            return [node.object_key for node in result]
        return result

    def topological_sort(self, keys_only=False) -> list[Node] | list[str]:
        roots = self.roots()
        sorted_nodes: list[Node] = []
        visited = set()

        def visit(node: Node):
            if node.object_key in visited:
                return
            visited.add(node.object_key)
            for child in self.children(node):
                visit(child)
            sorted_nodes.append(node)

        for root in roots:
            visit(root)
        sorted_nodes.reverse()
        return (
            sorted_nodes
            if not keys_only
            else [node.object_key for node in sorted_nodes]
        )

    def parents(self, key: Node | str, keys_only=False) -> list[Node] | list[str]:
        result = [self[e.from_key] for e in self.edges_to(key)]
        if keys_only:
            return [node.object_key for node in result]
        return result

    def path_roots(self):
        return [n for n in self.nodes if len(n.path) == 1]

    def path_sort(self):
        roots = self.path_roots()
        topological_sort = self.topological_sort(keys_only=True)
        roots.sort(key=lambda x: topological_sort.index(x.object_key))
        roots = [n for n in self.nodes if isinstance(n, ValueNode)] + roots
        return roots

    def children(self, key: Node | str, keys_only=False) -> list[Node] | list[str]:
        result = [self[e.to_key] for e in self.edges_from(key)]
        if keys_only:
            return [node.object_key for node in result]
        return result

    def object_keys(self) -> list[str]:
        return [node.object_key for node in self.__nodes.values()]

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

    def to_py(self):
        code = []
        for node in self.nodes:
            if isinstance(node, ClassNameNode) or isinstance(node, ClassTypeNode):
                class_name = node.__dict__.get(
                    "class_name", node.__dict__.get("class_type")
                )
                if class_name is not None:
                    assert node.module is not None
                    module_split = node.module.split(".")
                    if len(module_split) > 1 and module_split[0] in (
                        "trainers",
                        "models",
                        "data",
                    ):
                        module = ".." + ".".join(module_split)
                    else:
                        module = node.module

                    code.append(f"from {module} import {class_name}")
                elif node.module is not None:
                    code.append(f"import {module}")
        for node in self.path_sort():
            if isinstance(node, ValueNode):
                code.append(node.to_py(at_root=True))
            elif not (isinstance(node, FunctionCall) or isinstance(node, ReturnNode)):
                code.append(f"{node.object_key}={node.to_py()}")
        code.append(
            "returns={"
            + ",".join(
                f"'{n.object_key}': {n.to_py()}"
                for n in self.nodes
                if isinstance(n, ReturnNode)
            )
            + "}"
        )
        result = "\n".join(code)
        with open("/tmp/test.py", "w") as f:
            f.write(result)
        os.system("black /tmp/test.py")
        with open("/tmp/test.py", "r") as f:
            result = f.read()
        return result

    def to_dict(self):
        result =  {
            val.object_key:val.to_dict() for val in self.path_sort() if not type(val) in (FunctionCall, ) and not val.object_key == "save_dir"
        }
        return result

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    @staticmethod
    def __get_ref(val: str) -> str | None:
        # checks by using a regex if the string has a matching pattern like "{hello}"
        if isinstance(val, str):
            res = re.match(r"{\w+}", val)
            if res is None:
                return None
            else:
                span = res.span()
                return val[span[0] + 1 : span[1] - 1]
        return None

    @staticmethod
    def __is_return(bomb: Any):
        if not isinstance(bomb, list):
            return False
        if len(bomb) > 0:
            return sum(
                [isinstance(el, dict) and BombillaDAG.__is_function_call(el) for el in bomb]
            ) == len(bomb)
        return True

    @staticmethod
    def __rand_hex(length: int) -> str:
        randint = random.randint(0, 16**length - 1)
        return hex(randint)[2:].zfill(length)

    @staticmethod
    def __is_simple_type(bomb: Any):
        return type(bomb) in (str, int, float, bool, type(None))

    @staticmethod
    def __is_function_call(bomb: Any):
        return ("function_call" in bomb) and ("reference_key" in bomb)

    @staticmethod
    def __is_method_args(bomb: Any):
        return "function" in bomb and "params" in bomb and not ("module" in bomb)

    @staticmethod
    def __is_module(bomb: dict[str, Any]):
        return "module" in bomb


if __name__ == "__main__":
    dag = BombillaDAG("./test_bombillas/default.json")
    print(dag)
    dag.plot()
    print(dag.roots(keys_only=True))
    print(dag.children(dag.roots()[0], keys_only=True))
    print(dag.parents(dag.roots()[0]))
    print(dag.leaves(keys_only=True))
    print(dag.topological_sort(keys_only=True))
    # print(dag.children('pl_model'))
    # print(dag.to_py())
    print(dag.to_json())
