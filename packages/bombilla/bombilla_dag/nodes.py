from typing import Any
import json
import random
import re
import ipdb

# TODO: merge these nodes with the ones defined in the other file
class Node:
    def __init__(
        self,
        object_key: str,
        path: list[str],
        params: None | dict[str, Any] = None,
        class_type: str | None = None,
        class_name: None | str = None,
    ):
        self.object_key = object_key
        self.__params: dict[str, Any] = params if params is not None else {}
        self.path = path
        assert not (
            (class_type is not None) and (class_name is not None)
        ), f"Node {object_key} has both 'class_name' and 'class_type' defined. This is not allowed."
        if (class_type is not None) or (class_name is not None):
            assert (
                module is not None
            ), f"Node {object_key} has 'class_name' or 'class_type' defined, but no 'module' defined. This is not allowed."

    @property
    def params(self):
        return self.__params

    @params.setter
    def params(self, params: dict[str, Any]):
        assert isinstance(params, dict)

        def check_type(val):
            if isinstance(val, Node):
                return True
            elif isinstance(val, list):
                return all([check_type(el) for el in val])
            elif isinstance(val, dict):
                return all([check_type(v) for v in val.values()])
            elif isinstance(val, (str, int, float, bool, type(None))):
                return True
            else:
                return False

        for k, v in params.items():
            assert check_type(
                v
            ), ipdb.set_trace()  # f"Invalid type {type(v)} for param {k}"
        self.__params = params

    def __setitem__(self, key, value):
        if key != "params":
            assert key in self.__dict__, f"Invalid key {key} for Node"
            assert type(value) == type(
                self.__dict__[key]
            ), f"Invalid type {type(value)} for key {key}"
            self.__dict__[key] = value
        else:
            self.params = value

    def __getitem__(self, key: str):
        if key != "params":
            return self.__dict__[key]
        else:
            return self.params

    def to_dict(self) -> dict[str, Any]:
        def get_bombilla_dict(obj: Any) -> Any:
            if type(obj) in (str, int, float, bool, type(None)):
                return obj
            elif isinstance(obj, list):
                return [get_bombilla_dict(el) for el in obj]
            elif isinstance(obj, dict):
                return {key: get_bombilla_dict(val) for key, val in obj.items()}
            else:
                assert isinstance(
                    obj, Node
                ), f"{type(obj)} is not a valid type for a Node"
                return {
                    k if not "params" in k else "params": get_bombilla_dict(v)
                    for k, v in obj.__dict__.items()
                    if k != "path" and not (isinstance(v, str) and v.startswith("_"))
                }

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

    def is_path_parent(self, other):
        return self.path == other.path[: len(self.path)]

    @classmethod
    def from_dict(cls, bomb: Any, path: list[str]):
        pass

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
        elif isinstance(target, dict) or isinstance(target, Node):
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

    def to_py(self, at_root: bool = False) -> str:
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
            return f"""{{{','.join([f'"{k}":{self._render_val(v)}' for k, v in val.items()])}}}"""
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
        self.module = module
        super().__init__(object_key=f"_{self.class_type}", path=path, params=params)

    @staticmethod
    def is_one(obj: Any) -> bool:
        return isinstance(obj, dict) and "module" in obj and "class_type" in obj

    @classmethod
    def from_dict(cls, bomb: Any, path: list[str]):
        assert ClassTypeNode.is_one(bomb)
        assert not ClassNameNode.is_one(bomb)
        return ClassTypeNode(
            class_type=bomb["class_type"],
            module=bomb["module"],
            path=path,
        )

    def to_py(self, at_root: bool = False) -> str:
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
        self.module = module
        # puts new_obj_key from PascalCase to snake_case
        object_key = (
            object_key
            if object_key is not None
            else (f"_{class_name}_{Node._rand_hex(3)}")
        )
        super().__init__(object_key=object_key, path=path, params=params)

    def to_py(self, at_root: bool = False) -> str:
        return f"{self.class_name}({self._render_params(self.params)})"

    @staticmethod
    def is_one(obj: Any) -> bool:
        return isinstance(obj, dict) and "module" in obj and "class_name" in obj

    @classmethod
    def from_dict(cls, bomb: Any, path: list[str]):
        assert ClassNameNode.is_one(bomb)
        assert not ClassTypeNode.is_one(bomb)
        return ClassNameNode(
            object_key=bomb.get("object_key"),
            class_name=bomb["class_name"],
            module=bomb["module"],
            path=path,
            params=bomb.get("params"),
        )


class ValueNode(Node):
    def __init__(self, object_key: str, path: list[str]):
        super().__init__(object_key, path)
        self.module = "os.environ"
        self.class_name = "get"
        self.__key = self.object_key.upper()

    def to_py(self, at_root: bool = False):
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
        object_key = f"_{reference_key}.{function_call}(..)_{Node._rand_hex(3)}"
        super().__init__(object_key=object_key, path=path)
        self.params = params if params is not None else {}

    def to_py(self, at_root: bool = False):
        params = self._render_params(self.params)
        return f"{self.reference_key}.{self.function_call}({params})"

    @staticmethod
    def is_one(bomb: Any):
        return (
            isinstance(bomb, dict)
            and ("function_call" in bomb)
            and ("reference_key" in bomb)
        )

    @classmethod
    def from_dict(cls, bomb: Any, path: list[str]):
        assert FunctionCall.is_one(bomb)
        return FunctionCall(
            reference_key=bomb["reference_key"],
            function_call=bomb["function_call"],
            path=path,
            params=bomb.get("params"),
        )


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

    def to_py(self, at_root: bool = False):
        return f"[{','.join([f'{el.to_py()}' for el in self.execution_cue if el is not None])}]"

    @staticmethod
    def is_one(bomb: Any):
        if not isinstance(bomb, list):
            return False
        if len(bomb) > 0:
            return sum(
                [isinstance(el, dict) and FunctionCall.is_one(el) for el in bomb]
            ) == len(bomb)
        return True


class Edge:
    def __init__(
        self, from_node: str | Node, to_node: str | Node, path: list[str] | None = None
    ):
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
