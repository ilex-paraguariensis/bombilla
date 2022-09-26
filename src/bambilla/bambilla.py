# Bambilla, API for bamiblla json format and python objects

from node import Node, NodeDict


class Bambilla:
    def __init__(
        self,
        bambilla_dict: dict,
        root_module: str = "",
        base_module: str = "",
        object_key_map: dict = {},
    ) -> None:

        assert isinstance(bambilla_dict, dict), "Bambilla must be a dict"

        Node.set_config(base_module, root_module, bambilla_dict, object_key_map)
        self.root_node = Node(bambilla_dict)

    def load(self):
        self.root_node.__load__()

    def execute(self):
        self.root_node.__call__()

    def execute_method(
        self, method_name: str, object_name: str = None, *args, **kwargs
    ):

        self.root_node.__call_method__(method_name)

        self.root_node.find(object_name).method_call(method_name, *args, **kwargs)
