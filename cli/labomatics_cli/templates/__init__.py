"""Template rendering avec Jinja2."""

from jinja2 import Environment, PackageLoader


env = Environment(loader=PackageLoader("labomatics_cli", "templates"))


def render_template(template_name: str, context: dict) -> str:
    """Rendre un template Jinja2."""
    template = env.get_template(template_name)
    return template.render(**context)
