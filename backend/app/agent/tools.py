TOOLS = [
    {
        "name": "execute_browser_task",
        "description": (
            "Execute a task in the ShopAdmin portal by controlling a browser. "
            "Use this to look up order information, check refund eligibility, issue refunds, "
            "or make any account changes. Describe the task in plain language."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Plain-language description of what to do in the portal.",
                }
            },
            "required": ["task"],
        },
    }
]
