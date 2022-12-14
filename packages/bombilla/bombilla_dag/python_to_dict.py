import ast
import ipdb
from .nodes import (
    Node,
    ClassTypeNode,
    ClassNameNode,
    MethodCall,
    ValueNode,
    FunctionCall,
)
from typing import Any


def parse_args(
    val, parent: Node, nodes: dict[str, Node], imports: dict[str, str]
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
            return [parse_args(v, parent, nodes, imports) for v in val]
        else:
            result = {}
            for i, arg in enumerate(val):
                if isinstance(arg, ast.Name):
                    result[i] = "{" + arg.id + "}"
                elif isinstance(arg, ast.Call):
                    assert isinstance(arg.func, ast.Name)
                    assert arg.func.id in imports
                    node = ClassNameNode(
                        path=[], class_name=arg.func.id, module=imports[arg.func.id]
                    )
                    # nodes[node.object_key] = node
                    uba = parse_args(arg.keywords, node, nodes, imports)
                    assert isinstance(uba, dict)
                    node.params = uba
                    result[i] = node
                elif isinstance(arg.value, ast.Constant):
                    result[arg.arg] = parse_args(
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
                        uba = parse_args(arg.value.keywords, node, nodes, imports)
                        assert isinstance(uba, dict)
                        node.params = uba
                        result[arg.arg] = node
                    else:
                        node = MethodCall(
                            path=[],
                            function_call=arg.value.func.attr,
                            reference_key=arg.value.func.value.id,
                        )
                        uba = parse_args(arg.value.keywords, node, nodes, imports)
                        node.params = uba if uba else {}
                        result[arg.arg] = node
                else:
                    if isinstance(arg.value, ast.Name):
                        result[arg.arg] = parse_args(arg.value, parent, nodes, imports)
                    elif isinstance(arg.value, ast.Dict):
                        sub_res = {}
                        for key, val in zip(arg.value.keys, arg.value.values):
                            assert isinstance(key, ast.Constant)
                            sub_res[key.value] = parse_args(val, parent, nodes, imports)
                        result[arg.arg] = sub_res
                    elif isinstance(arg.value, ast.List):
                        uba = parse_args(arg.value.elts, parent, nodes, imports)
                        if isinstance(uba, list):
                            result[arg.arg] = uba
                        else:
                            assert isinstance(uba, dict)
                            vals = [(int(key), val) for key, val in uba.items()]
                            vals.sort(key=lambda x: x[0])
                            result[arg.arg] = [val for _, val in vals]

    elif isinstance(val, ast.Dict):
        result = {}
        for key, subval in zip(val.keys, val.values):
            assert isinstance(key, ast.Constant)
            uba = parse_args(subval, parent, nodes, imports)
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
        uba = parse_args(val.keywords, node, nodes, imports)
        node.params = uba
        result = node
    else:
        result = val
    return result

def get_class_name(val:ast.Assign | ast.AnnAssign | ast.Attribute | ast.Name, acc: list[str]) -> list[str]:
    if isinstance(val, ast.Assign):
        return get_class_name(val.value.func, acc)
    elif isinstance(val, ast.AnnAssign):
        return get_class_name(val.value.func, acc)
    elif isinstance(val, ast.Attribute):
        acc.append(val.attr)
        return get_class_name(val.value, acc)
    elif isinstance(val, ast.Name):
        acc.append(val.id)
        return acc
    else:
        return acc

def parse_assign(
    item: ast.Assign | ast.AnnAssign, imports: dict[str, str], nodes: dict[str, Node]
) -> None:
    if not isinstance(item.value, ast.Subscript):
        class_name = ".".join(get_class_name(item, [])[::-1])
        target = item.targets[0] if isinstance(item, ast.Assign) else item.target
        if isinstance(target, ast.Name):
            if isinstance(item.value, ast.Call):
                if isinstance(item.value.func, ast.Name):
                    assert item.value.func.id in imports, f"{target.id} not in imports"
                    node = ClassNameNode(
                        class_name=class_name,
                        object_key=target.id,
                        path=[target.id],
                        module=imports[class_name.split(".")[0]],
                    )
                    nodes[node.object_key] = node
                    args = parse_args(item.value.keywords, node, nodes, imports)
                    node.params = args if args else {}
                elif isinstance(item.value.func, ast.Attribute):
                    if not class_name == "os":
                        node = ClassNameNode(
                            class_name=class_name,
                            object_key=target.id,
                            path=[target.id],
                            module=imports[class_name.split(".")[0]],
                        )
                        nodes[node.object_key] = node
                        args = parse_args(item.value.keywords, node, nodes, imports)
                        node.params = args if args else {}
                    else:
                        node = ValueNode(object_key=target.id, path=[target.id])
                        nodes[node.object_key] = node


def match_if(
    value: ast.If, imports, nodes
) -> dict[str, list[FunctionCall | MethodCall]]:
    returns: dict[str, list[FunctionCall | MethodCall]] = {}
    current: ast.If | None = value
    while current != None:
        assert isinstance(current, ast.If)
        assert isinstance(current.test, ast.Compare)
        assert isinstance(current.test.left, ast.Name)
        assert isinstance(current.test.comparators[0], ast.Constant)
        assert isinstance(current.test.ops[0], ast.Eq)
        assert current.test.left.id == "command"
        statements = current.body
        command = current.test.comparators[0].value
        acc = []
        returns[command] = acc

        for statement in statements:
            if not isinstance(statement, ast.Pass):
                assert isinstance(statement, ast.Expr)
                assert isinstance(statement.value, ast.Call)
                x = statement.value
                if not isinstance(x.func, ast.Name):
                    assert isinstance(x.func, ast.Attribute)
                    assert isinstance(x.func.value, ast.Name)
                    reference_key = x.func.value.id
                    function_call = x.func.attr
                    params = parse_args(x.keywords, None, nodes, imports)
                    assert isinstance(params, dict)
                    function_call = MethodCall(
                        reference_key=reference_key,
                        function_call=function_call,
                        params=params,
                        path=[],
                    )
                else:
                    function = x.func.id
                    params = parse_args(x.keywords, None, nodes, imports)
                    assert isinstance(params, dict)
                    function_call = FunctionCall(
                        function=function,
                        module=imports[function],
                        params=params,
                        path=[],
                    )

                acc.append(function_call)
        new_current = current.orelse[0] if current.orelse else None
        assert new_current == None or isinstance(new_current, ast.If)
        current = new_current

    return returns


def python_to_dict(py_string: str) -> dict[str, Any]:
    body = ast.parse(str.encode(py_string)).body
    nodes: dict[str, Node] = {}
    imports: dict[str, str] = {}
    returns = {}
    allowed_types = (ast.Assign, ast.AnnAssign, ast.If, ast.Import, ast.ImportFrom)
    assert all(
        isinstance(item, allowed_types) for item in body
    ), f"The python file must only contain assignments, imports, and one if statement. Found non-allowed type: {tuple(b for b in body if not isinstance(b, allowed_types))}"
    assert (
        len([item for item in body if isinstance(item, ast.If)]) == 1
    ), "The python file must only contain one if statement"
    for item in body:
        if isinstance(item, ast.ImportFrom):
            for name in item.names:
                imports[name.name] = item.module
        elif isinstance(item, ast.Import):
            for name in item.names:
                imports[name.name] = name.name
    for item in body:
        if isinstance(item, ast.Assign) or isinstance(item, ast.AnnAssign):
            parse_assign(item, imports, nodes)
        elif isinstance(item, ast.If):
            returns = match_if(item, imports, nodes)
    # returns = returns | nodes  # {node.object_key: node for node in nodes}

    def to_dict(val):
        if isinstance(val, Node):
            return val.to_dict()
        elif isinstance(val, dict):
            return {key: to_dict(val) for key, val in val.items()}
        elif isinstance(val, list):
            return [to_dict(val) for val in val]
        else:
            return val

    # returns = to_dict(returns)
    # assert isinstance(returns, dict)
    result = {
        "objects": {key: val.to_dict() for key, val in nodes.items() if not val.class_name == "os.environ.get"},
        "experiment": {key: [v.to_dict() for v in val] for key, val in returns.items()},
    }
    return result
