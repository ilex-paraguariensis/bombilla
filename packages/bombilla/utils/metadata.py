import ipdb
import json
import os


def generate_metadata(obj, metadata, root_module=""):

    return_meta = __generate_metadata(obj, metadata)

    save_metadata(return_meta, metadata, root_module)
    # ipdb.set_trace()


def save_metadata(return_meta, meta, root_module=""):

    # ipdb.set_trace()

    path = find_metadata(meta, root_module)

    if path:
        update_metadata(return_meta, meta, path)


def update_metadata(return_meta, obj_meta, path):

    with open(path, "r") as f:
        meta = json.load(f)

        if "function" in obj_meta:
            for f in meta["exports"]["functions"]:
                if f["function_name"] == obj_meta["function"]:
                    f["returns"] = return_meta
                    break

        elif "class_name" in obj_meta:
            for c in meta["exports"]["classes"]:
                if c["class_name"] == obj_meta["class_name"]:
                    c["returns"] = return_meta
                    # ipdb.set_trace()

                    break
        # ipdb.set_trace()

    meta_json = json.dumps(meta, indent=4)
    # ipdb.set_trace()

    # save to file
    with open(path, "w") as f:
        f.write(meta_json)

    # ipdb.set_trace()

    # find the correct function with same module


def find_metadata(meta, root):

    if not "module" in meta:
        return None

    path = [root] + meta["module"].split(".") + ["metadata.json"]

    path = os.path.join(*path)

    if os.path.exists(path):
        return path

    path = [root] + meta["module"].split(".")[:-1] + ["metadata.json"]

    path = os.path.join(*path)

    if os.path.exists(path):
        return path

    return None


def __generate_metadata(obj, metadata):

    meta = {}

    try:
        klass = obj.__class__
        module = klass.__module__

        meta["class"] = str(klass)
        meta["module"] = str(module)

        mro = klass.mro()

        meta["mro"] = [str(m) for m in mro]

        shape = try_shape(obj)

        if shape is not None:
            meta["shape"] = str(shape)

        if klass == tuple:
            # generate metadata for each element in the tuple
            metas = []
            for i, element in enumerate(obj):
                _meta = __generate_metadata(element, metadata)
                metas.append(_meta)

            meta["return"] = metas

        elif klass == list:
            # generate metadata for each element in the list
            metas = []
            for i, element in enumerate(obj):
                _meta = __generate_metadata(element, metadata)
                metas.append(_meta)
            meta["return"] = metas

    except:
        pass

    return meta


def try_shape(obj):
    try:
        return obj.shape
    except:
        return None
