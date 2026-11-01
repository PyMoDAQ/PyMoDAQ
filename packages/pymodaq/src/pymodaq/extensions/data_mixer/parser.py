import ast
import operator
import re
import types
from typing import Any, List

import numpy as np


data_name_regexp = re.compile(r"({.*?})+")  # first occurrences of things between {}


def split_formulae(formulae: str) -> List[str]:
    """ Split a string into a list of string for each new line

    Parameters
    ----------
    formulae: str
        The formulae containing various mathematical formula separated with a new line character

    Returns
    -------
    The various formula as a list of string
    """
    return re.split(r'\n', formulae)


def extract_data_names(formula: str) -> List[str]:
    """ Extract the names of the data appearing between curly brackets with a given string formula

    Parameters
    ----------
    formula: str
        The mathematical expression to compute containing in curly brackets the data full names

    Returns
    -------

    """
    data_names = [data_name_with_curly[1:-1] for
                  data_name_with_curly in data_name_regexp.findall(formula)]
    return data_names


def replace_names_in_formula(formula: str):
    formula_tmp = formula[:]
    names = []
    while True:
        m = data_name_regexp.search(formula_tmp)
        if m is not None:
            names.append(m.group())
            formula_tmp = (
                formula_tmp.replace(formula_tmp[m.start(): m.end()],
                                    f'dte.get_data_from_full_name("{m.group()[1:-1]}")'))
        else:
            break
    return formula_tmp, names



class UnsafeFormulaError(ValueError):
    """Raised when a formula contains anything else than arithmetic and numpy functions applied to the data"""


_BINARY_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow, ast.MatMult: operator.matmul,
}
_UNARY_OPERATORS = {ast.USub: operator.neg, ast.UAdd: operator.pos}

_ALLOWED_BUILTINS = {'abs': abs, 'min': min, 'max': max, 'sum': sum, 'round': round, 'pow': pow,
                     'float': float, 'int': int, 'len': len}

# numpy submodules whose functions can be used in a formula, e.g. np.random.normal, np.linalg.norm
_ALLOWED_NUMPY_SUBMODULES = ('random', 'linalg', 'fft', 'emath', 'polynomial')

# numpy functions that read or write files, or change the global state of numpy
_DENIED_NUMPY_NAMES = {
    'load', 'save', 'savez', 'savez_compressed', 'loadtxt', 'savetxt', 'genfromtxt', 'fromfile', 'memmap',
    'fromregex', 'DataSource', 'show_config', 'show_runtime', 'get_include', 'info', 'lookfor', 'test',
    'add_newdoc', 'add_docstring', 'add_newdoc_ufunc', 'seterr', 'seterrcall', 'setbufsize', 'errstate',
    'set_printoptions', 'printoptions', 'set_string_function', 'set_num_threads',
}


def _dotted_parts(node: ast.AST) -> List[str]:
    """['np', 'random', 'normal'] for the node of np.random.normal, [] for anything else"""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return parts[::-1]
    return []


def _numpy_member(node: ast.AST) -> Any:
    """Get the numpy function or constant named by a node such as np.sin or np.random.normal"""
    parts = _dotted_parts(node)
    if len(parts) < 2 or len(parts) > 3 or parts[0] != 'np':
        raise UnsafeFormulaError('Only numpy functions (np.xxx) can be used in a formula')
    member: Any = np
    for ind, part in enumerate(parts[1:]):
        if part.startswith('_'):
            raise UnsafeFormulaError(f'{part} cannot be used in a formula')
        if member is np:
            if part in _DENIED_NUMPY_NAMES:
                raise UnsafeFormulaError(f'np.{part} cannot be used in a formula')
        elif not isinstance(member, types.ModuleType):
            raise UnsafeFormulaError('Only numpy functions (np.xxx) can be used in a formula')
        member = getattr(member, part, None)
        if member is None:
            raise UnsafeFormulaError(f'{".".join(parts[:ind + 2])} is not a numpy function')
        if isinstance(member, types.ModuleType):
            if ind != 0 or part not in _ALLOWED_NUMPY_SUBMODULES:
                raise UnsafeFormulaError(f'np.{part} cannot be used in a formula')
    if isinstance(member, types.ModuleType) or not (callable(member) or isinstance(member, (int, float))):
        raise UnsafeFormulaError(f'{".".join(parts)} cannot be used in a formula')
    return member


def _evaluate(node: ast.AST, dte) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex, str, bool, type(None))):
            return node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        return _BINARY_OPERATORS[type(node.op)](_evaluate(node.left, dte), _evaluate(node.right, dte))
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand, dte))
    elif isinstance(node, ast.Tuple):
        return tuple(_evaluate(elt, dte) for elt in node.elts)
    elif isinstance(node, ast.List):
        return [_evaluate(elt, dte) for elt in node.elts]
    elif isinstance(node, ast.Attribute):
        return _numpy_member(node)  # a constant such as np.pi
    elif isinstance(node, ast.Call):
        args = [_evaluate(arg, dte) for arg in node.args]
        if any(keyword.arg is None for keyword in node.keywords):
            raise UnsafeFormulaError('Unpacking arguments cannot be used in a formula')
        kwargs = {keyword.arg: _evaluate(keyword.value, dte) for keyword in node.keywords}
        if _dotted_parts(node.func) == ['dte', 'get_data_from_full_name']:  # inserted for the {data names}
            if len(args) != 1 or kwargs or not isinstance(args[0], str):
                raise UnsafeFormulaError('Unexpected data name in the formula')
            return dte.get_data_from_full_name(args[0])
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_BUILTINS:
            return _ALLOWED_BUILTINS[node.func.id](*args, **kwargs)
        return _numpy_member(node.func)(*args, **kwargs)
    raise UnsafeFormulaError(f'{type(node).__name__} cannot be used in a formula')


def evaluate_formula(formula: str, dte) -> Any:
    """Compute a formula without ever running anything else than arithmetic and numpy functions

    Parameters
    ----------
    formula: str
        A formula in which the data names have been replaced by calls to dte.get_data_from_full_name (see
        :func:`replace_names_in_formula`).
    dte: DataToExport
        The data the names of the formula refer to

    Raises
    ------
    UnsafeFormulaError
        if the formula contains anything else than arithmetic, numpy functions (np.xxx), a few builtins
        (abs, min, max, ...) and the data
    """
    try:
        tree = ast.parse(formula.strip(), mode='eval')
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise UnsafeFormulaError(f'Invalid formula: {e}') from e
    return _evaluate(tree.body, dte)
