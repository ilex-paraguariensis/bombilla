from typing import Callable
import inspect
import ipdb
from docstring_parser import (
    Docstring,
    DocstringMeta,
    DocstringParam,
    DocstringReturns,
    DocstringStyle,
    parse_from_object,
)
from docstring_parser.common import DocstringExample


def parse_default_param(param):

    # if param is object:
    #     ipdb.set_trace()

    # if param is a class, return the class name
    if inspect.isclass(param):
        return {
            "class_type": param.__name__,
            "module": param.__module__,
        }

    if param is list:
        return [parse_default_param(p) for p in param]

    return param


def get_function_args(
    function: Callable,
    args={},
    generate_defaults: bool = True,
    generate_none: bool = False,
):

    params = args.to_dict() if hasattr(args, "to_dict") else args
    default = {}
    errors = []

    for param_name, param in inspect.signature(function).parameters.items():
        # only add parameters that are not self or exist in the params

        if param_name in params or param_name == "self":
            continue

        # only allow named parameters and not *args or **kwargs
        if param.kind != param.POSITIONAL_OR_KEYWORD:
            continue

        if param.default is not param.empty:
            # ignore None values
            if param.default != None and generate_defaults:
                default[param_name] = parse_default_param(param.default)

                # check if default is type class, or object

            elif generate_none:
                default[param_name] = None

        elif param.annotation is not param.empty:
            default[param_name] = f"Fix me! {param.annotation}"
            error = f"Missing parameter {param_name}.  Hint: {param.annotation}"
            errors.append(error)
        else:
            default[param_name] = "Fix me!"
            error = f"Missing parameter {param_name}. Hint: Add a default value or type annotation"
            errors.append(error)

            #

    params.update(default)

    # docs = parse_docs(function)
    # if docs != {}:
    #     params["__doc__"] = docs

    return params, errors


def parse_docs(obj):
    """Get the docstring for an object.

    Args:
        obj: Object to get the docstring for.

    Returns:
        The docstring for the object.
    """

    doc = parse_from_object(obj)

    if doc.style != DocstringStyle.EPYDOC:
        return docstring_to_json(doc)
    return {}


def docstring_to_json(doc: Docstring):
    """Convert a docstring to a JSON representation.

    Args:
        doc: Docstring to convert.

    Returns:
        A JSON representation of the docstring.
    """
    res = {
        "short_description": doc.short_description,
        "long_description": doc.long_description,
        "params": [param_to_json(param) for param in doc.params],
        # "meta": [meta_to_json(meta) for meta in doc.meta],
        "returns": returons_to_json(doc.returns),
        "examples": [example_to_json(example) for example in doc.examples],
    }

    # remove empty values
    return {k: v for k, v in res.items() if v}


def example_to_json(example: DocstringExample):
    """Convert an example to a JSON representation.

    Args:
        example: Example to convert.

    Returns:
        A JSON representation of the example.
    """
    if example is None:
        return None
    return {
        "args": example.args,
        "snippet": example.snippet,
        "description": example.description,
    }


def returons_to_json(returns: DocstringReturns):
    """Convert a returns to a JSON representation.

    Args:
        returns: Returns to convert.

    Returns:
        A JSON representation of the returns.
    """
    if returns is None:
        return None
    return {
        "type": returns.type_name,
        "description": returns.description,
    }


def meta_to_json(meta: DocstringMeta):
    """Convert a meta to a JSON representation.

    Args:
        meta: Meta to convert.

    Returns:
        A JSON representation of the meta.
    """
    return {
        "args": meta.args,
        "description": meta.description,
    }


def param_to_json(param: DocstringParam):
    """Convert a param to a JSON representation.

    Args:
        param: Param to convert.

    Returns:
        A JSON representation of the param.
    """
    if param is None:
        return None
    return {
        "name": param.arg_name,
        "type": param.type_name,
        "description": param.description,
        "default": param.default,
        "is_optional": param.is_optional,
    }
