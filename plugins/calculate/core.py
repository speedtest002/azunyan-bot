import math

_ALLOWED = {
    "sqrt": math.sqrt, "pow": pow, "abs": abs, "round": round,
    "log": math.log, "pi": math.pi, "e": math.e,
    "mod": lambda x, y: x % y,
    "sin": math.sin,  "cos": math.cos,  "tan": math.tan,
    "sind": lambda x: math.sin(math.radians(x)),
    "cosd": lambda x: math.cos(math.radians(x)),
    "tand": lambda x: math.tan(math.radians(x)),
}

def safe_eval(expr: str):
    expr = (
        expr.replace("^", "**")
            .replace("x", "*")
            .replace("÷", "/")
            .replace("π", "pi")
            .replace("\\*", "*")
            .replace(",", ".")
    )
    try:
        return eval(expr, {"__builtins__": {}}, _ALLOWED)  # noqa: S307
    except Exception as e:
        return f"Lỗi: {e}"


def format_result(expression: str, precision: int) -> str:
    result = safe_eval(expression)
    if isinstance(result, (int, float)):
        return f"{expression.replace('*', '\\*')} = {round(result, precision)}"
    return str(result)
