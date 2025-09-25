def js_bool(b: bool) -> str:
    return "true" if b else "false"

def js_str(s: str) -> str:
    # robust JS string literal (uses Python's repr for basic escaping)
    return repr(s)
