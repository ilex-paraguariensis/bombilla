from typing import Any
import os
import re
import random
import json
import ipdb
import subprocess
from .nodes import (
    Node,
    ValueNode,
    FunctionCall,
    ClassNameNode,
    ClassTypeNode,
    ReturnNode,
)
from .dag import DAG
from .python_to_dict import python_to_dict
import ast


class BombillaDAG(DAG):
    def __init__(self, bombilla_dict: dict[str, Any]):
        super().__init__()
        self.__from_dict(bombilla_dict, [], None)
        self.__flatten()

    @classmethod
    def from_py(cls, filename: str):
        with open(filename, "rb") as f:
            raw_content = f.read()
        content = python_to_dict(ast.parse(raw_content).body)
        return cls(content)

    @classmethod
    def from_json(cls, filename: str):
        with open(filename, "r") as f:
            content = json.loads(f.read())
        return cls(content)

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

    def __str__(self):
        return self.print()

    def __repr__(self):
        return self.__str__()

    def prune(self):
        pass

    def __flatten(self):
        def path_walk(node: Any, parent: Node | None = None):
            if isinstance(node, dict):
                for k, v in node.items():
                    return path_walk(v)
            elif isinstance(node, list):
                for el in node:
                    return path_walk(el)
            elif type(node) in [str, int, float, bool]:
                return
            else:
                # ipdb.set_trace()
                assert isinstance(node, Node)
                if len(self.children(node)) > 1 and self.path_parent(node) != self.root:
                    parent = self.path_parent(node)
                    assert parent is not None
                    parent.assign(node.path, "{" + node.object_key + "}")
                    # self.root.assign([node.object_key], node)
                    edge = self.path_edge_to(node)
                    assert edge is not None
                    self.path_edges.remove(edge)
                    self.add_path_edge(self.root, node)
                for child in self.path_children(node):
                    path_walk(child, node)

        path_walk(self.root)

    def __from_dict(self, bomb: Any, path: list[str], parent: Node | None):
        if self.__is_simple_type(bomb):
            assert parent is not None, ipdb.set_trace()
            ref = self.__get_ref(bomb)
            if ref is not None:
                if ref in ("save_path",):
                    self.add_node(ValueNode(ref, path))
                self.add_edge(ref, parent, path)
            parent.assign(path, bomb)
        elif ReturnNode.is_one(bomb):
            node = ReturnNode(object_key=path[-1], path=path)
            self.add_node(node)
            self.add_path_edge(parent, node)
            assert isinstance(bomb, list)
            assert len(path) == 1
            for i, child in enumerate(bomb):
                self.__from_dict(child, path + [str(i)], node)
        elif isinstance(bomb, list):
            for index, item in enumerate(bomb):
                self.__from_dict(item, path + [str(index)], parent)
        elif isinstance(bomb, dict):
            if BombillaDAG.__is_method_args(bomb):
                for key, val in bomb["params"].items():
                    self.__from_dict(val, path + ["params", key], parent)
            if FunctionCall.is_one(bomb):
                assert parent is not None
                function_call = FunctionCall.from_dict(bomb, path)
                self.add_node(function_call)
                self.add_edge(
                    from_node=bomb["reference_key"],  # bomb["reference_key"],
                    to_node=function_call,
                    path=path,
                )
                self.add_path_edge(parent, function_call)
                self.add_edge(function_call, parent, path)
                parent.assign(path, function_call)
                assert isinstance(bomb["params"], dict)
                for key, val in bomb["params"].items():
                    self.__from_dict(val, path + ["params", key], function_call)
            elif "module" in bomb:
                node: Node | None = None
                if ((not len(path)) >= 2) and (path[-2] == "params"):
                    bomb["object_key"] = path[-2] + "_" + self.__rand_hex(5)
                if ClassNameNode.is_one(bomb):
                    node = ClassNameNode.from_dict(bomb, path)
                else:
                    assert ClassTypeNode.is_one(bomb)
                    node = ClassTypeNode.from_dict(bomb, path)

                self.add_node(node)
                self.add_path_edge(parent, node)
                if parent is not None:
                    parent.assign(path, node)  # "{" + bomb["object_key"] + "}")
                    self.add_edge(node, parent, path)  # done
                bomb["path"] = path
                # self.add_node(parent)
                if "params" in bomb:
                    for key, val in bomb["params"].items():
                        self.__from_dict(val, path + ["params", key], node)
                """  UNCOMMENT TO ENABLE METHOD ARGS
                if "method_args" in bomb:
                    ipdb.set_trace()
                    for key, val in enumerate(bomb["method_args"]):
                        self.from_dict(val, path + ["method_args", str(key)], node)
                """
            else:
                for key, val in bomb.items():
                    self.__from_dict(val, path + [key], parent)
        else:
            if not path[-1] == "params":
                for key, val in bomb.items():
                    self.__from_dict(val, path + [key], parent)

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

    def to_py(self, filename: str | None = None):
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

        if filename is not None:
            with open(filename, "w") as f:
                f.write(result)
        return result

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

    """
    @staticmethod
    def __is_return(bomb: Any):
        if not isinstance(bomb, list):
            return False
        if len(bomb) > 0:
            return sum(
                [
                    isinstance(el, dict) and FunctionCall.is_one(el)
                    for el in bomb
                ]
            ) == len(bomb)
        return True
    """

    @staticmethod
    def __rand_hex(length: int) -> str:
        randint = random.randint(0, 16**length - 1)
        return hex(randint)[2:].zfill(length)

    @staticmethod
    def _is_simple_type(bomb: Any):
        return type(bomb) in (str, int, float, bool, type(None))

    @staticmethod
    def __is_method_args(bomb: Any):
        return "function" in bomb and "params" in bomb and not ("module" in bomb)

    @staticmethod
    def __is_simple_type(bomb: Any):
        return type(bomb) in (str, int, float, bool, type(None))

    """
    @staticmethod
    def __is_function_call(bomb: Any):
        return ("function_call" in bomb) and ("reference_key" in bomb)
    
    @staticmethod
    def __is_module(bomb: dict[str, Any]):
        return "module" in bomb
    """
