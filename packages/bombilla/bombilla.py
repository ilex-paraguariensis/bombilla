# Bambilla, API for bamiblla json format and python objects

from .node import Node, NodeDict, ExperimentNode
import ipdb
from .bombilla_dag.bombilla_dag import BombillaDAG



class Bombilla(dict):
    def __init__(
        self,
        bombilla_dict: dict,
        root_module: str = "",
        object_key_map: dict = {},
    ) -> None:

        self.dag = BombillaDAG(bombilla_dict)
        assert isinstance(bombilla_dict, dict), "Bambilla must be a dict"

        Node.set_config(root_module, object_key_map)
        self.root_node = ExperimentNode(dict(bombilla_dict))

    @classmethod
    def from_file(cls, filename: str, root_module: str = "", object_key_map: dict = {}):
        return cls(
            BombillaDAG.from_file(filename).to_dict(), root_module, object_key_map
        )

    @classmethod
    def from_py_string(
        cls, py_string: str, root_module: str = "", object_key_map: dict = {}
    ):
        return cls(
            BombillaDAG.from_py_string(py_string).to_dict(), root_module, object_key_map
        )

    @classmethod
    def from_py_file(
        cls, filename: str, root_module: str = "", object_key_map: dict = {}
    ):
        dag = BombillaDAG.from_py_file(filename)
        return cls(dag.to_dict(), root_module, object_key_map)

    @classmethod
    def from_json_file(
        cls, filename: str, root_module: str = "", object_key_map: dict = {}
    ):
        dag = BombillaDAG.from_json_file(filename)
        return cls(dag.to_dict(), root_module, object_key_map)

    @classmethod
    def from_string(
        cls, py_string: str, root_module: str = "", object_key_map: dict = {}
    ):
        return cls(
            Bombilla.from_string(py_string).to_dict(), root_module, object_key_map
        )

    @classmethod
    def format_json(cls, filename: str):
        BombillaDAG.format_json(filename)

    @classmethod
    def from_raw(cls, content: str):
        pass

    def load(self):
        self.root_node.__load__()

    def execute(self, type: str = "train"):
        self.root_node.__call__()
        self.root_node.execute_experiment(type)

    def generate_full_dict(self):
        self.root_node.__load__()

        return self.root_node.generate_full_dict()

    def execute_method(self, method_name: str, object_name: str, *args, **kwargs):

        self.root_node.find(object_name).call_method(method_name, *args, **kwargs)

    def get_node_by_key(self, key: str):
        return getattr(self.root_node, key)

    def __getitem__(self, key):
        return self.get_node_by_key(key)()

    def has_method(self, method_name: str, object_name: str):
        try:
            node = self.root_node.find(object_name)
            return node.has_method(method_name)
        except:
            return False

    def call_all_methods(self, object_key: str):
        try:
            node = self.root_node.find(object_key)
            node.call_all_methods()
        except:
            try:
                node = self.root_node[object_key]
                node.call_all_methods()
            except:
                return False

            return False

    def find(self, object_name: str):
        return Node._key_value_map[object_name]
