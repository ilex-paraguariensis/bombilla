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
    Edge,
)
from .dag import DAG
import ast


class BombillaDAG(DAG):
    def __init__(self, filename_or_content: dict[str, Any] | str):
        super().__init__()
        if isinstance(filename_or_content, str):
            filename = filename_or_content
            with open(filename, "r") as f:
                raw_content = f.read()
            if filename.endswith(".json"):
                content = json.loads(raw_content)
                self.from_dict(content, [], None)
                self.__flatten()
            elif filename.endswith(".py"):
                content = ast.parse(raw_content).body
                assert isinstance(content, list)
                for el in content:
                    assert isinstance(el, ast.AST)
                self.from_py(content)
            else:
                raise ValueError("Unknown file extension")
        else:
            content = filename_or_content

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

    def from_dict(self, bomb: Any, path: list[str], parent: Node | None):
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
                self.from_dict(child, path + [str(i)], node)
        elif isinstance(bomb, list):
            for index, item in enumerate(bomb):
                self.from_dict(item, path + [str(index)], parent)
        elif isinstance(bomb, dict):
            if BombillaDAG.__is_method_args(bomb):
                for key, val in bomb["params"].items():
                    self.from_dict(val, path + ["params", key], parent)
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
                    self.from_dict(val, path + ["params", key], function_call)
            elif "module" in bomb:
                node: Node | None = None
                if ((not len(path)) >= 2) and (path[-2] == "params"):
                    bomb["object_key"] = path[-2] + "_" + self.__rand_hex(5)
                if ClassNameNode.is_one(bomb):
                    node = ClassNameNode.from_dict(bomb, path)
                else:
                    assert ClassTypeNode.is_one(bomb)
                    node = ClassTypeNode.from_dict(bomb, path)

                try:
                    self.add_node(node)
                except:
                    ipdb.set_trace()
                self.add_path_edge(parent, node)
                if parent is not None:
                    parent.assign(path, node)  # "{" + bomb["object_key"] + "}")
                    self.add_edge(node, parent, path)  # done
                bomb["path"] = path
                # self.add_node(parent)
                if "params" in bomb:
                    for key, val in bomb["params"].items():
                        self.from_dict(val, path + ["params", key], node)
                """  UNCOMMENT TO ENABLE METHOD ARGS
                if "method_args" in bomb:
                    ipdb.set_trace()
                    for key, val in enumerate(bomb["method_args"]):
                        self.from_dict(val, path + ["method_args", str(key)], node)
                """
            else:
                for key, val in bomb.items():
                    self.from_dict(val, path + [key], parent)
        else:
            if not path[-1] == "params":
                for key, val in bomb.items():
                    self.from_dict(val, path + [key], parent)

    def parse_args(
        self, val, parent: Node, nodes: dict[str, Node], imports: dict[str, str]
    ) -> dict | list | int | float | str | bool | Node:
        if isinstance(val, ast.Name):
            if val.id in imports:
                return ClassTypeNode([], val.id, imports[val.id])
            else:
                return "{" + val.id + "}"
        elif isinstance(val, list):
            if len(val) == 0:
                return []
            elif (
                len(
                    [
                        v
                        for v in val
                        if isinstance(v, ast.Constant) or isinstance(v, ast.Name)
                    ]
                )
                > 0
            ):
                return [self.parse_args(v, parent, nodes, imports) for v in val]
            else:
                result = {}
                for i, arg in enumerate(val):
                    # try:
                    #     if arg.arg == "dirpath":
                    #         ipdb.set_trace()
                    # except:pass
                    if isinstance(arg, ast.Name):
                        result[i] = "{" + arg.id + "}"
                    elif isinstance(arg, ast.Call):
                        if arg.func.id == "AimLogger":
                            ipdb.set_trace()
                        assert isinstance(arg.func, ast.Name)
                        assert arg.func.id in imports
                        node = ClassNameNode(
                            path=[], class_name=arg.func.id, module=imports[arg.func.id]
                        )
                        # nodes[node.object_key] = node
                        uba = self.parse_args(arg.keywords, node, nodes, imports)
                        node.params = uba
                        result[i] = node
                    elif isinstance(arg.value, ast.Constant):
                        result[arg.arg] = self.parse_args(
                            arg.value.value, parent, nodes, imports
                        )
                    elif isinstance(arg.value, ast.JoinedStr):
                        result[arg.arg] = "".join(
                            [
                                "{" + v.value.id + "}"
                                if isinstance(v, ast.FormattedValue)
                                else v.value
                                for v in arg.value.values
                            ]
                        )
                    elif isinstance(arg.value, ast.Call):
                        if isinstance(arg.value.func, ast.Name):
                            node = ClassNameNode(
                                path=[],
                                class_name=arg.value.func.id,
                                module=imports[arg.value.func.id],
                            )
                            uba = self.parse_args(
                                arg.value.keywords, node, nodes, imports
                            )
                            node.params = uba
                            result[arg.arg] = node
                        else:
                            node = FunctionCall(
                                path=[],
                                function_call=arg.value.func.attr,
                                reference_key=arg.value.func.value.id,
                            )
                            uba = self.parse_args(
                                arg.value.keywords, node, nodes, imports
                            )
                            node.params = uba if uba else {}
                            result[arg.arg] = node
                    else:
                        if isinstance(arg.value, ast.Name):
                            result[arg.arg] = self.parse_args(
                                arg.value, parent, nodes, imports
                            )
                        elif isinstance(arg.value, ast.Dict):
                            sub_res = {}
                            for key, val in zip(arg.value.keys, arg.value.values):
                                assert isinstance(key, ast.Constant)
                                sub_res[key.value] = self.parse_args(
                                    val, parent, nodes, imports
                                )
                            result[arg.arg] = sub_res
                        elif isinstance(arg.value, ast.List):
                            uba = self.parse_args(
                                arg.value.elts, parent, nodes, imports
                            )
                            if isinstance(uba, list):
                                result[arg.arg] = uba
                            else:
                                vals = [(int(key), val) for key, val in uba.items()]
                                vals.sort(key=lambda x: x[0])
                                result[arg.arg] = [val for _, val in vals]

        elif isinstance(val, ast.Dict):
            result = {}
            for key, subval in zip(val.keys, val.values):
                assert isinstance(key, ast.Constant)
                uba = self.parse_args(subval, parent, nodes, imports)
                assert isinstance(
                    uba, (str, int, float, bool, Node, list, dict)
                ), ipdb.set_trace()
                result[key.value] = uba
        elif isinstance(val, ast.Constant):
            result = val.value
        elif isinstance(val, ast.Call):
            assert isinstance(val.func, ast.Name)
            assert val.func.id in imports
            node = ClassNameNode(
                path=[], class_name=val.func.id, module=imports[val.func.id]
            )
            # nodes.append(node)
            uba = self.parse_args(val.keywords, node, nodes, imports)
            if isinstance(uba, dict):
                for k, v in uba.items():
                    if not type(v) in [str, int, float, bool, Node]:
                        ipdb.set_trace()
            node.params = uba
            result = node
        else:
            # TODO check if the type is a class, then it is a class type
            result = val
        if isinstance(result, dict) and (list(result.keys()) == ["0", "1"]):
            ipdb.set_trace()

        return result

    def from_py(self, body: list[ast.AST]):
        nodes = {}
        imports = {}
        returns = {}
        for item in body:
            if isinstance(item, ast.ImportFrom):
                for name in item.names:
                    imports[name.name] = item.module
        for item in body:
            if isinstance(item, ast.Assign):
                # assignment
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id != "returns":
                            assert isinstance(item.value, ast.Call)
                            # function call
                            assert isinstance(item.value.func, ast.Name)
                            assert (
                                item.value.func.id in imports
                            ), f"{target.id} not in imports"
                            node = ClassNameNode(
                                class_name=item.value.func.id,
                                object_key=target.id,
                                path=[target.id],
                                module=imports[item.value.func.id],
                            )
                            nodes[node.object_key] = node
                            uba = self.parse_args(
                                item.value.keywords, node, nodes, imports
                            )

                            node.params = uba
                        else:
                            assert isinstance(
                                item.value, ast.Dict
                            ), "returns must be a dictionary"
                            for key, val in zip(item.value.keys, item.value.values):
                                acc = []
                                assert isinstance(key, ast.Constant)
                                returns[key.value] = acc
                                assert isinstance(val, ast.List)
                                for x in val.elts:

                                    reference_key = x.func.value.id
                                    function_call = x.func.attr
                                    params = self.parse_args(
                                        x.keywords, None, nodes, imports
                                    )
                                    # for arg in x.keywords:
                                    #     params[arg.arg] = "{" + arg.value.id + "}"
                                    function_call = FunctionCall(
                                        reference_key=reference_key,
                                        function_call=function_call,
                                        params=params,
                                        path=[],
                                    )
                                    acc.append(function_call)
        returns = returns | nodes  # {node.object_key: node for node in nodes}
        """
        result = {
            "objects": [
                val.to_dict() for key, val in nodes.items() if key != "returns"
            ],
            "returns": {
                key: [r.to_dict() for r in val] for key, val in returns.items()
            },
        }
        """
        # at least the required functions must be there
        # return len(required_functions - functions) == 0
        def to_dict(val):
            if isinstance(val, Node):
                return val.to_dict()
            elif isinstance(val, dict):
                return {key: to_dict(val) for key, val in val.items()}
            elif isinstance(val, list):
                return [to_dict(val) for val in val]
            else:
                return val

        returns = to_dict(returns)
        # print(json.dumps(returns, indent=4))
        self.from_dict(returns, [], None)

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
