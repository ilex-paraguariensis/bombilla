# Bambilla, API for bamiblla json format and python objects

from .node import Node, NodeDict
import ipdb


class Bombilla(dict):
    def __init__(
        self,
        bombilla_dict: dict,
        root_module: str = "",
        object_key_map: dict = {},
    ) -> None:

        assert isinstance(bombilla_dict, dict), "Bambilla must be a dict"

        Node.set_config(root_module, object_key_map)
        self.root_node = NodeDict(dict(bombilla_dict))

    def load(self):
        self.root_node.__load__()

    def execute(self):
        self.root_node.__call__()

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

    def find(self, object_name: str):
        return Node._key_value_map[object_name]
