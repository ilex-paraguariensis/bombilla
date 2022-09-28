# Bambilla, API for bamiblla json format and python objects

from .node import Node, NodeDict
import ipdb


class Bombilla:
    def __init__(
        self,
        bambilla_dict: dict,
        root_module: str = "",
        base_module: str = "",
        object_key_map: dict = {},
    ) -> None:

        assert isinstance(bambilla_dict, dict), "Bambilla must be a dict"

        Node.set_config(base_module, root_module, object_key_map)
        self.root_node = NodeDict(dict(bambilla_dict))

    def load(self):
        self.root_node.__load__()

    def execute(self):

        self.root_node.__call__()

    def generate_full_dict(self):
        self.root_node.__load__()

        return self.root_node.generate_full_dict()

    def execute_method(
        self, method_name: str, object_name: str = None, *args, **kwargs
    ):

        self.root_node.find(object_name).call_method(method_name, *args, **kwargs)

    def find(self, object_name: str):
        return Node._key_value_map[object_name]
