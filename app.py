class Task:
    name: str
    description: str
    is_default: bool = False
    run: function # kwargs for formatting and returns dict[str, Any]