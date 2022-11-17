from .bombilla_dag import BombillaDAG


if __name__ == "__main__":
    #dag = BombillaDAG.from_json("./test_bombillas/default.json")
    #print(dag.to_py("./test_bombillas/default.py"))
    # print(dag.print(True))
    """
    dag.plot()
    print(dag.roots(keys_only=True))
    print(dag.children(dag.roots()[0], keys_only=True))
    print(dag.parents(dag.roots()[0]))
    print(dag.leaves(keys_only=True))
    print(dag.topological_sort(keys_only=True))
    # print(dag.children('pl_model'))
    # print(dag.to_py())
    print(dag.to_json())
    """
    # dag.to_py("./test_bombillas/default.py")
    dag2 = BombillaDAG.from_py_file("./test_bombillas/default2.py")
    print(dag2)
    print(dag2.to_json())
    #print(dag2.to_json())
