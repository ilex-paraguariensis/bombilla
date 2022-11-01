import ast
import ipdb
import json

# which syntax elements are allowed at module level?
whitelist = [
    # docstring
    lambda x: isinstance(x, ast.Expr) and isinstance(x.value, ast.Str),
    # import
    lambda x: isinstance(x, ast.Import),
    # class
    lambda x: isinstance(x, ast.ClassDef),
    # function
    lambda x: isinstance(x, ast.FunctionDef),
]


class Node:
    def __init__(self, object_key: str):
        self.object_key = object_key
        self.import_name = ""
        self.class_name = ""
        self.params = {}

    def __repr__(self):
        # returns a JSON representation of the node
        # by first turning the object into a dict
        return str(self.__dict__)

    def __str__(self):
        return self.__repr__()

    def to_dict(self):
        return self.__dict__


class FunctionCall:
    def __init__(self, reference_key: str, function_call: str, params: dict[str, str]):
        self.reference_key = reference_key
        self.function_call = function_call
        self.params = params

    def to_dict(self):
        return self.__dict__


def parse_args(val) -> dict | list | int | float | str:
    if isinstance(val, ast.Name):
        return "{" + val.id + "}"
    elif isinstance(val, list) and len(val) == 0:
        return []
    elif (
        isinstance(val, list)
        and len(
            [v for v in val if isinstance(v, ast.Constant) or isinstance(v, ast.Name)]
        )
        > 0
    ):
        return [parse_args(v) for v in val]
    elif (
        isinstance(val, list)
        #    isinstance(val[0], ast.keyword)
        #    or isinstance(val[0], ast.Constant)
        # )
    ):
        result = {}
        for i, arg in enumerate(val):
            if isinstance(arg, ast.Name):
                result[i] = "{" + arg.id + "}"
            elif isinstance(arg.value, ast.Constant):
                result[arg.arg] = parse_args(arg.value.value)
            else:
                if isinstance(arg.value, ast.Name):
                    result[arg.arg] = parse_args(arg.value)
                elif isinstance(arg.value, ast.Dict):
                    sub_res = {}
                    for key, val in zip(arg.value.keys, arg.value.values):
                        sub_res[key.value] = parse_args(val)
                    result[arg.arg] = sub_res
                elif isinstance(arg.value, ast.List):
                    result[arg.arg] = parse_args(arg.value.elts)
    elif isinstance(val, ast.Dict):
        result = {}
        for key, subval in zip(val.keys, val.values):
            result[key.value] = parse_args(subval)
    elif isinstance(val, ast.List):
        ipdb.set_trace()
        result = [parse_args(subval) for subval in val]  # FIXME
    elif isinstance(val, ast.Constant):
        result = val.value
    else:
        result = val

    return result


def validate(source, required_functions):
    tree = ast.parse(source)
    nodes = {}
    required_functions = set(required_functions)
    imports = {}
    returns = {}
    for item in tree.body:
        if isinstance(item, ast.Assign):
            # assignment
            for target in item.targets:
                if isinstance(target, ast.Name):
                    if target.id != "returns":
                        node = Node(target.id)
                        nodes[target.id] = node
                        if isinstance(item.value, ast.Call):
                            # function call
                            assert isinstance(item.value.func, ast.Name)
                            # method call
                            node.class_name = item.value.func.id
                            # if its a dictionary, parse the keys
                            parsed = parse_args(item.value.keywords)
                            if isinstance(parsed, list):
                                parsed = {}
                            assert isinstance(parsed, dict)
                            node.params = parsed
                    else:
                        for key, val in zip(item.value.keys, item.value.values):
                            acc = []
                            returns[key.value] = acc
                            for x in val.elts:
                                reference_key = x.func.value.id
                                function_call = x.func.attr
                                params = {}
                                for arg in x.keywords:
                                    params[arg.arg] = "{" + arg.value.id + "}"
                                function_call = FunctionCall(
                                    reference_key, function_call, params
                                )
                                acc.append(function_call)
                # parses the parameters of the function call

        elif isinstance(item, ast.ImportFrom):
            for name in item.names:
                imports[name.name] = item.module
        """
        if all(not checker(item) for checker in whitelist):
            return False
        """
    for _, node in nodes.items():
        node.import_name = imports.get(node.class_name, "")

    result = {
        "objects": [val.to_dict() for key, val in nodes.items() if key != "returns"],
        "returns":{key: [r.to_dict() for r in val] for key, val in returns.items()}
    }
    # at least the required functions must be there
    # return len(required_functions - functions) == 0
    print(json.dumps(result, indent=4))
    return True


if __name__ == "__main__":
    required_funcs = ["init", "execute", "cleanup"]
    with open("generated.py", "rb") as f:
        print("yay!" if validate(f.read(), required_funcs) else "d'oh!")
