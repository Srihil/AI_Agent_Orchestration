import ast
import operator
from langchain_core.tools import tool


_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("Division by zero")
        return _SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported operation: {ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Args:
        expression: A mathematical expression string, e.g. "25 * 4 + 100 / 2"

    Returns:
        The computed result as a string.
    """
    try:
        expression = expression.strip()
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        if result == int(result):
            return str(int(result))
        return f"{result:.6g}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except (ValueError, TypeError, SyntaxError) as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Cannot evaluate expression — {str(e)}"
