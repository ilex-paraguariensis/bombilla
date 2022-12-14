from distutils import errors
from re import S
from typing import Optional, Any, Callable, Type, Union
import json

import toml
from .utils.metadata import generate_metadata

from . import utils
import regex as re

import ipdb

SimpleType = Union[str, int, float, bool, None]


class Node:
    object_key: Optional[str] = None
    _py_object: Optional[object] = None
    _docs: Optional[str] = None

    def __init__(self, args, parent=None, **kawrgs) -> None:
        self._original_keys = args.keys()
        self._original_args = dict(args)
        self._uno_key_value_map = {}
        self._parent = parent

        if args is None:
            args = self._json()
        for key, val in args.items():
            setattr(self, key, val)

    def _get_python_object(self) -> object:
        pass

    def find(self):
        pass

    @staticmethod
    def set_config(root_module: str, key_value_map: dict):
        Node._root_module = root_module
        Node._key_value_map = key_value_map

    def load_dynamic_objects(self):
        for key, value in self.__dict__.items():
            if (
                type(value) == str
                and key in self._original_keys
                and re.search(r"{.*}", value)
            ):
                # get the key name
                key_name = re.search(r"{.*}", value).group(0)[1:-1]

                dynamic_object = Node._key_value_map[key_name]
                self._uno_key_value_map[key] = value

                setattr(self, key, dynamic_object)

            if type(value) == list:
                set = False
                for i, item in enumerate(value):
                    if (
                        type(item) == str
                        and key in self._original_keys
                        and re.search(r"{.*}", item)
                    ):
                        # get the key name
                        key_name = re.search(r"{.*}", item).group(0)[1:-1]

                        dynamic_object = Node._key_value_map[key_name]
                        value[i] = dynamic_object
                        set = True

                if set:

                    self._uno_key_value_map[key] = value
                    setattr(self, key, value)

    def post_object_creation(self):
        if "object_key" in self._original_keys:
            Node._key_value_map[self.object_key] = self._py_object

        self.generate_metadata(self._py_object, self.to_dict())

    def generate_metadata(self, obj, metadata):

        generate_metadata(obj, metadata, Node._root_module)

    def load_module(self):
        assert "module" in self.__dict__, "module not found"

        fromlist = [self.class_name] if hasattr(self, "class_name") else []
        fromlist = [getattr(self, "class")] if hasattr(self, "class") else fromlist

        if hasattr(self, "function") and not hasattr(self, "class_name"):
            fromlist = [self.function]

        if hasattr(self, "class_type"):
            fromlist = [self.class_type]

        module_list = [
            self.module,
        ]
        if (
            hasattr(Node, "_root_module")
            and Node._root_module != None
            and self._root_module != ""
        ):
            module_list.append(Node._root_module + "." + self.module)
        module = None
        for module_name in module_list:
            # print(f"Trying to import {module_name}")
            try:
                module = __import__(module_name, fromlist=fromlist)
                break
            except ModuleNotFoundError as err:
                # print(f"{err.name=} {err.path=} {err.msg=}")
                # print(f"{module_name=}")
                if (
                    err.name != None
                    and err.name.split(".")[0] != module_name.split(".")[0]
                ):
                    raise err
                pass

        if module == None:
            raise ModuleNotFoundError(f'Module "{self.module}" not found')

        if "class_name" in self.__dict__:
            module = getattr(module, self.class_name)
        # if "class_name" in self:
        #     module = getattr(module, getattr[self, "class_name"])

        return module

    def get_imports(self):
        if not hasattr(self, "module"):
            return None
        if hasattr(self, "class_name"):
            return f"from {self.module} import {self.class_name}"
        if hasattr(self, "function"):
            return f"from {self.module} import {self.function}"
        if hasattr(self, "class_type"):
            return f"from {self.module} import {self.class_type}"

        return f"import {self.module}"

    def _json(self):
        # returns a simple json representing the node (filtering out private properties and methods)

        def to_json(obj):
            if isinstance(obj, Node):
                return {
                    key: to_json(val)
                    for key, val in obj.__dict__.items()
                    if not key.startswith("_")
                    and not callable(val)
                    and type(val) in [str, int, float, bool, dict]
                }
            elif isinstance(obj, list):
                return [to_json(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: to_json(val) for key, val in obj.items()}
            else:
                return obj

        return to_json(self)

    def __str__(self):
        return json.dumps(self._json(), indent=4)

    def __repr__(self):
        return str(self)

    @classmethod
    def _base_json(cls):
        # returns a simple json representing the node (filtering out private properties and methods)
        cur_params = {
            key: val
            for key, val in cls.__dict__.items()
            if not key.startswith("_") and not callable(val) and type(val) != object
        }
        for base_class in cls.__bases__:
            if base_class != object:
                cur_params |= {
                    key: val
                    for key, val in base_class.__dict__.items()
                    if not key.startswith("_")
                    and not callable(val)
                    and not (hasattr(val, "__get__") and callable(val.__get__))
                }
        return cur_params

    @classmethod
    def is_one(cls: Type, obj: Any) -> bool:
        # checks that the given object has the same property as the current node
        """
        return isinstance(obj, dict) and (
            sorted(list(obj.keys())) == node_properties
        )
        """
        if not isinstance(obj, dict):
            return False
        for key, val in cls._base_json().items():
            if key not in obj and val is not None:
                return False
        return True

    @classmethod
    def assert_is_one(cls: Type, obj: Any):
        if not cls.is_one(obj):
            raise SyntaxError(
                f"Object {obj} is not a valid node Node. \n This is how it should look like:\n{cls._base_json()}"
            )

    def __load__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):

        if self._py_object != None:
            return self._py_object
        else:

            super_dict = self.__dict__
            super_dict = dict(
                {
                    key: val() if isinstance(val, Node) else val
                    for key, val in super_dict.items()
                    if not key.startswith("_") and key in self._original_keys
                }
            )
            return super_dict

    def to_toml(self):
        t = toml.dumps(self.to_dict())
        return t

    # def __dict__(self):
    #     super_dict = super().__dict__
    #     return dict({key: val for key, val in super_dict.items() if not key.startswith("_")})


class NodeDict(Node):
    def __init__(self, args, **kawrgs) -> None:
        assert type(args) == dict, "args must be a dict"
        super().__init__(args, **kawrgs)
        self._node_key_dict = {}
        self._loaded = False

    def __load__(self, parent: Optional[Node] = None):

        if self._loaded:
            return self

        # ipdb.set_trace()

        for key, val in self.__dict__.items():

            if not key.startswith("_") and key in self._original_keys:
                val = load_node(val, parent=self)
                if isinstance(val, Node):
                    val.__load__(parent=self)
                    setattr(self, key, val)
                    self._node_key_dict[key] = val

                elif isinstance(val, list):
                    nodes = []
                    for i, item in enumerate(val):
                        item = load_node(item, parent=self)
                        if isinstance(item, Node):
                            item.__load__(parent=self)
                            nodes.append(item)
                            val[i] = item
                            self._node_key_dict[key] = nodes
                    setattr(self, key, val)

        self._loaded = True
        # ipdb.set_trace()

        return self

    def __call__(self, *args: Any, **kwds: Any) -> Any:

        self.load_dynamic_objects()

        def val_to_call(val, parent: Node | None = None):
            if isinstance(val, Node):
                return val()  # if not isinstance(parent, ExperimentNode) else val
            elif isinstance(val, list):
                return [val_to_call(item) for item in val]
            else:
                return val

        result = {
            key: val_to_call(val)
            for key, val in self.__dict__.items()
            if not key.startswith("_") and key in self._original_keys
        }
        return result

    def find(self, key_name):
        assert (
            self._node_key_dict != None
        ), "node_key_dict is None, cannot find before loading"
        return self._node_key_dict[key_name]

    def to_dict(self):

        if self._node_key_dict == None:
            self.__load__()

        def load_node(node):
            if isinstance(node, Node):
                return node.to_dict()
            elif isinstance(node, list):
                return [load_node(item) for item in node]
            else:
                return node

        result = {}

        for key, val in self.__dict__.items():
            if not key.startswith("_") and key in self._original_keys:
                if key in self._node_key_dict:
                    val = load_node(self._node_key_dict[key])
                    result[key] = val
                elif key in self._uno_key_value_map:
                    result[key] = self._uno_key_value_map[key]

                elif type(val) == object:
                    result[key] = self._original_args[key]
                else:
                    result[key] = val

        return result

    def generate_full_dict(self):

        if self._node_key_dict == None:
            self.__load__()

        errors = []

        def load_node(node, errors=errors):
            if isinstance(node, Node):
                n, e = node.generate_full_dict()
                errors += e
                return n
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    if isinstance(item, Node):
                        n, e = item.generate_full_dict()
                        errors += [e]
                        node[i] = n

                return node

            else:
                return node

        result = {}

        for key, val in self.__dict__.items():
            if not key.startswith("_") and key in self._original_keys:

                if key in self._uno_key_value_map:
                    result[key] = self._uno_key_value_map[key]
                elif key in self._node_key_dict:
                    val = load_node(self._node_key_dict[key])
                    result[key] = val

                elif type(val) == list or type(val) == Node:
                    result[key] = load_node(val)
                else:
                    result[key] = val

        errors = [e for e in errors if e != None and e != []]

        return result, errors

    def parse_params(self):

        if self._node_key_dict == None:
            self.__load__()

        errors = []
        params = {}

        for key, val in self.__dict__.items():

            if not key.startswith("_") and key in self._original_keys:

                if key in self._node_key_dict:
                    p, e = self._node_key_dict[key].parse_params()
                    params[key] = p
                    errors += e
                elif isinstance(val, Node):
                    p, e = val.parse_params()
                    params[key] = p
                    errors += e

                else:
                    params[key] = val

        # remove None from errors
        errors = [e for e in errors if e != None and e != []]

        return params, errors


class ObjectReference(Node):
    reference_key: str = ""
    _reference: Optional[Node] = None

    def __init__(self, args, parent: Optional[Node] = None, **kawrgs) -> None:
        super().__init__(args, parent=parent, **kawrgs)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return Node._key_value_map[self.reference_key]


class MethodCall(Node):
    function_call: str = ""
    reference_key: Optional[str] = None
    params: dict = {}

    def __load__(self, parent=None, *args, **kwargs):

        self.param_node = NodeDict(self.params, parent=self)
        self.param_node.__load__(self)
        return self

    def __call__(self, parent: Optional[object] = None, *args, **kwargs):
        if self._py_object != None:
            return self._py_object
        # first create DictNode of params
        params = self.param_node()
        # print("method call params", params)

        # then call the function
        object = Node._key_value_map[self.reference_key]
        function = getattr(object, self.function_call)
        self._py_object = function(**params)
        self.post_object_creation()
        return self._py_object

    def __init__(self, args, parent: Optional[object] = None):
        super().__init__(args)

    def to_dict(self):
        return {
            "reference_key": self.reference_key,
            "function_call": self.function_call,
            "params": self.param_node.to_dict(),
        }

    def generate_full_dict(self):

        full_params, errors = self.param_node.parse_params()
        errors = [e for e in errors if e != None and e != []]

        result = {
            "reference_key": self.reference_key,
            "function_call": self.function_call,
            "params": full_params,
        }

        if self._docs != None:
            result["docs"] = self._docs

        return result, errors

    def parse_params(self):

        function = getattr(Node._key_value_map[self.reference_key], self.function_call)

        # get the function args that are missing from the params
        params, errors = utils.get_function_args(function, self.param_node)
        self._docs = utils.parse_docs(function)
        errors = [e for e in errors if e != None and e != []]

        return params, errors


# Methodcall for objects
class ObjectMethodCall(Node):
    function: str = ""
    params: dict = {}

    def __init__(self, args, parent=None, **kawrgs) -> None:
        super().__init__(args, parent, **kawrgs)
        self._node = None

    def __load__(self, parent=None) -> object:

        if self._node == None:
            self._node = NodeDict(self.params, parent=self)
            self._node.__load__(self)
            return self
        # self._node = NodeDict(self.params)
        return self

    def __call__(self, *args, **kwargs):
        return self._node()

    def to_dict(self):
        return {"function": self.function, "params": self._node.to_dict()}

    def generate_full_dict(self):
        full_params, errors = self._node.generate_full_dict()
        return {"function": self.function, "params": full_params}, errors


# A node that has method_args, could be a function or class
class MethodArgNode(Node):
    module: str = ""
    params: dict = {}
    method_args: Optional[list[ObjectMethodCall]] = None

    def call_method(self, method_name: str, *args, **kwargs):

        method_arg_names = [arg["function"] for arg in self.method_args]
        assert method_name in method_arg_names

        idx = method_arg_names.index(method_name)
        method_args = self.method_args[idx]["params"]

        method_args = load_node(method_args, parent=self)
        method_args.__load__(self)
        method_args = method_args()
        f, p = flatten_nameless_params(method_args)

        method = getattr(self._py_object, method_name)

        if f:
            return method(*args, *f, **p, **kwargs)

        return method(*args, **p, **kwargs)

    def has_method(self, method_name: str):
        method_arg_names = [arg["function"] for arg in self.method_args]
        return method_name in method_arg_names

    def call_all_methods(self):

        for method_arg in self.method_args:
            self.call_method(method_arg["function"])

    def parse_method_args(self):

        # assert self._py_object != None, "Object not created yet"
        assert self.method_args != None, "No method args"

        errors = []
        params = {}
        results = []

        for method in self._method_args_nodes:

            function = method.function
            method.__load__(self)
            full_args, errs = method.generate_full_dict()
            errors += errs

            gen_method = {
                "function": function,
            }

            if self._py_object:
                m = getattr(self._py_object, function)
                p, error = utils.get_function_args(m, full_args["params"])
                docs = utils.parse_docs(m)
                errors += error
                gen_method["params"] = p
                if docs:
                    gen_method["docs"] = docs
            else:
                try:
                    m = getattr(self.load_module(), function)
                    p, error = utils.get_function_args(m, full_args["params"])
                    docs = utils.parse_docs(m)
                    gen_method["params"] = p
                    if docs:
                        gen_method["docs"] = docs
                    errors += error
                except:
                    gen_method["params"] = full_args["params"]

            results += [gen_method]

        # remove None from errors
        errors = [e for e in errors if e != None and e != []]

        return results, errors


class FunctionModuleCall(MethodArgNode):
    function: str = ""
    module: str = ""
    params: dict = {}
    method_args: Optional[list[ObjectMethodCall]] = None

    def __load__(self, parent=None) -> object:

        self._param_node = NodeDict(self.params)
        self._param_node.__load__(self)
        self._method_args_nodes = (
            [ObjectMethodCall(m, self) for m in self.method_args]
            if self.method_args
            else []
        )
        return self

    def to_dict(self):
        return {
            "function": self.function,
            "module": self.module,
            "params": self._param_node.to_dict(),
        }

    def generate_full_dict(self):
        result = {
            "function": self.function,
            "module": self.module,
        }

        if hasattr(self, "object_key") and self.object_key != "":
            result["object_key"] = self.object_key

        errs = []
        if self.method_args != None:
            full_method_args, err = self.parse_method_args()
            result["method_args"] = full_method_args
            errs += err

        full_params, err = self.parse_params()
        result["params"] = full_params

        if self._docs != None:
            result["docs"] = self._docs

        errs += err

        # remove None from errors
        errs = [e for e in errs if e != None and e != []]

        return result, errs

    def parse_params(self):

        module = self.load_module()
        function = getattr(module, self.function)

        params, errors = utils.get_function_args(function, self._param_node)

        self._docs = utils.parse_docs(function)

        errors = [e for e in errors if e != None and e != []]

        return params, errors

    def __call__(self):
        params = self._param_node()

        module = self.load_module()
        function = getattr(module, self.function)

        _arg, _kwarg = flatten_nameless_params(params)

        if _arg:
            self._py_object = function(*_arg, **_kwarg)
        else:
            self._py_object = function(**params)
        self.post_object_creation()
        return self._py_object


def flatten_nameless_params(params: dict) -> dict:

    flat = params.pop("", None)
    flats = []
    while flat != None:
        flats.append(flat)
        flat = params.pop("", None)

    return flats, params


class Object(MethodArgNode):
    module: str = ""
    class_name: str = ""
    params: dict = {}  # param is actualy a dictnode
    method_args: Optional[list[ObjectMethodCall]] = None

    def __load__(self, parent: Optional[object] = None) -> object:

        if self._py_object != None:
            return self

        self.param_node = NodeDict(self.params)

        self.param_node.__load__()

        self._method_args_nodes = (
            [ObjectMethodCall(m, self) for m in self.method_args]
            if self.method_args
            else []
        )

        return self

    def __call__(self, *args, **kwargs):

        if self._py_object != None:
            return self._py_object

        module = self.load_module()
        self._py_object = module(**self.param_node())
        self.post_object_creation()
        return self._py_object

    def to_dict(self):
        return {
            "module": self.module,
            "class_name": self.class_name,
            "params": self.param_node.to_dict(),
        }

    def generate_full_dict(self):
        result = {
            "module": self.module,
            "class_name": self.class_name,
        }

        if (
            hasattr(self, "object_key")
            and self.object_key != ""
            and self.object_key != None
        ):
            result["object_key"] = self.object_key

        errs = []
        if self.method_args != None:
            full_method_args, err = self.parse_method_args()
            result["method_args"] = full_method_args
            errs += [err]

        full_params, err = self.parse_params()
        result["params"] = full_params

        if self._docs != None:
            result["docs"] = self._docs

        errs += err

        # remove None from errors
        errs = [e for e in errs if e != None]

        return result, errs

    def parse_params(self):

        module = self.load_module()

        params, err = self.param_node.generate_full_dict()

        errors = err

        params, erros = utils.get_function_args(module, params)
        self._docs = utils.parse_docs(module)

        errors += erros
        errors = [e for e in errors if e != None and e != []]

        return params, errors

    def __init__(self, args: Optional[dict], parent: Optional[object] = None):
        super().__init__(args, parent=parent)


class AnnonymousObject(Node):
    def __init__(self, args: Optional[dict] = None) -> None:
        super().__init__(args)
        setattr(self, "", "")


class ClassTypeAnnotation(Node):
    module: str = ""
    class_type: str = ""

    def __load__(self, parent: Optional[Node] = None) -> object:
        self._module = self.load_module()
        return self

    def __call__(self, *args, **kwargs):

        return getattr(self._module, self.class_type)

    def to_dict(self):
        return {
            "module": self.module,
            "class_type": self.class_type,
        }

    def generate_full_dict(self):
        return self.to_dict(), []


class ExperimentNode(Node):
    objects: dict = {}
    experiment: dict = {}

    def __init__(self, args, **kawrgs) -> None:
        # ipdb.set_trace()
        assert type(args) == dict, "args must be a dict"
        super().__init__(args, **kawrgs)
        self._node_key_dict = {}
        self._objects_node = NodeDict(self.objects)

    def to_dict(self):
        return {
            "objects": self._objects_node.to_dict(),
            "experiment": self.experiment,
        }

    def __str__(self):
        return f"{self.to_dict()}"

    def generate_full_dict(self):
        return self._objects_node.generate_full_dict()

    def __load__(self, parent: Optional[Node] = None) -> object:

        self._objects_node.__load__()

    def __call__(self, *args: Any, **kwds: Any) -> Any:

        self.load_dynamic_objects()

        # ipdb.set_trace()
        self._objects_node.__call__()

        return self._objects_node

    def execute_experiment(self, exec_type: str = "train"):

        assert exec_type in self.experiment, f"{exec_type} not in returns"
        dic = self.experiment[exec_type]

        # ipdb.set_trace()

        nodes = (
            [load_node(item) for item in dic] if type(dic) == list else [load_node(dic)]
        )

        for node in nodes:
            node.__load__()
            node.__call__()

        return self


node_types: list[Type] = [
    Object,
    MethodCall,
    FunctionModuleCall,
    ObjectMethodCall,
    ObjectReference,
    ClassTypeAnnotation,
    ExperimentNode,
    NodeDict,
]
SyntaxNode = Union[
    Object,
    FunctionModuleCall,
    MethodCall,
    ObjectReference,
    ObjectMethodCall,
    ClassTypeAnnotation,
    ExperimentNode,
    NodeDict,
]


def load_node(args, parent=None):
    if isinstance(args, dict):
        node: Optional[SyntaxNode] = None
        for node_type in node_types:
            if node_type.is_one(args):
                node = node_type(args, parent=parent)
                return node

    return args
