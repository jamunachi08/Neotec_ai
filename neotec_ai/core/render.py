"""Safe placeholder substitution for user-edited prompts. Only the known
tokens are replaced; any other braces the user types are left untouched
(unlike str.format, which would raise)."""


def render(template, **values):
    out = template
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out
