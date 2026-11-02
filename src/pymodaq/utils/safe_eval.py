"""Evaluate the text of stored values without being able to run code"""
import ast
import datetime
from collections import OrderedDict
from typing import Any, Optional

import numpy as np


class UnsafeExpressionError(ValueError):
    """Raised when the text of a stored value is anything else than a plain value"""


def _literal_value(node: ast.AST) -> Any:
    """Rebuild a value from the ast of its ``repr`` without ever evaluating code

    Only numbers, strings, bytes, booleans, None, signed numbers, tuples, lists, dicts and sets of these,
    and the str, int, float, datetime, date, time and numpy.float64 constructors given plain arguments are
    accepted.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, bytes, int, float, bool, type(None))):
            return node.value
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _literal_value(node.operand)
        if isinstance(operand, (int, float)) and not isinstance(operand, bool):
            return -operand if isinstance(node.op, ast.USub) else +operand
    elif isinstance(node, ast.Name) and node.id in ('nan', 'inf'):
        return float(node.id)
    elif isinstance(node, ast.Attribute) and _dotted_name(node) in ('np.nan', 'numpy.nan'):
        return np.nan
    elif isinstance(node, ast.Dict):
        if any(key is None for key in node.keys):
            raise UnsafeExpressionError('Unexpected unpacking in stored value')
        return {_literal_value(key): _literal_value(value) for key, value in zip(node.keys, node.values)}
    elif isinstance(node, ast.Set):
        return {_literal_value(elt) for elt in node.elts}
    elif isinstance(node, ast.Tuple):
        return tuple(_literal_value(elt) for elt in node.elts)
    elif isinstance(node, ast.List):
        return [_literal_value(elt) for elt in node.elts]
    elif isinstance(node, ast.Call):
        name = _dotted_name(node.func)
        constructor = _SAFE_CONSTRUCTORS.get(name)
        if constructor is not None:
            args = [_literal_value(arg) for arg in node.args]
            kwargs = {}
            for keyword in node.keywords:
                if keyword.arg == 'tzinfo' and _dotted_name(keyword.value) == 'datetime.timezone.utc':
                    kwargs['tzinfo'] = datetime.timezone.utc
                elif keyword.arg == 'fold':
                    kwargs['fold'] = _literal_value(keyword.value)
                else:
                    raise UnsafeExpressionError(f'Unexpected argument {keyword.arg}')
            return constructor(*args, **kwargs)
    raise UnsafeExpressionError(f'Unexpected content in stored value: {type(node).__name__}')


def _dotted_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return None if base is None else f'{base}.{node.attr}'
    return None


_SAFE_CONSTRUCTORS = {
    'datetime.datetime': datetime.datetime,
    'datetime.date': datetime.date,
    'datetime.time': datetime.time,
    'np.float64': np.float64,
    'numpy.float64': np.float64,
    'str': str,
    'int': int,
    'float': float,
    'OrderedDict': OrderedDict,
    'collections.OrderedDict': OrderedDict,
    'np.array': np.array,
    'array': np.array,
    'np.int64': np.int64,
    'np.int32': np.int32,
    'np.float32': np.float32,
}


def safe_literal_eval(text: str) -> Any:
    """Equivalent of eval for the repr of the values stored by :class:`JsonConverter`, that cannot run code"""
    try:
        return _literal_value(ast.parse(text.strip(), mode='eval').body)
    except UnsafeExpressionError:
        raise
    except (SyntaxError, ValueError, TypeError, OverflowError, MemoryError, RecursionError) as e:
        raise UnsafeExpressionError(str(e)) from e
