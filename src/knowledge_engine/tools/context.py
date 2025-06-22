from ..core.active_context import ActiveContext
from ..core.models import Node


def get_active_context(ac: ActiveContext) -> list[Node]:
    """
    Returns all nodes currently in the Active Context.
    """
    return ac.list_nodes() 