import ast
import ipdb
from .nodes import Node, ClassTypeNode, ClassNameNode, FunctionCall
from typing import Any


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
                        uba = self.parse_args(arg.value.keywords, node, nodes, imports)
                        node.params = uba
                        result[arg.arg] = node
                    else:
                        node = FunctionCall(
                            path=[],
                            function_call=arg.value.func.attr,
                            reference_key=arg.value.func.value.id,
                        )
                        uba = self.parse_args(arg.value.keywords, node, nodes, imports)
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
                        uba = self.parse_args(arg.value.elts, parent, nodes, imports)
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
        node.params = uba
        result = node
    else:
        # TODO check if the type is a class, then it is a class type
        result = val
    return result


def python_to_dict(self, body: list[ast.AST]) -> dict[str, Any]:
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
                        uba = self.parse_args(item.value.keywords, node, nodes, imports)

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
    assert isinstance(returns, dict)
    return returns
