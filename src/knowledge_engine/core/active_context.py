import json
from collections import deque
from typing import OrderedDict
from pathlib import Path

from .knowledge_graph import KnowledgeGraph
from .models import Node
from .config import get_context_path


class ActiveContext:
    def __init__(self, knowledge_graph: KnowledgeGraph, max_size: int = 100):
        self.kg = knowledge_graph
        self.max_size = max_size
        self.nodes: OrderedDict[str, Node] = OrderedDict()
        self._context_path: Path = get_context_path()
        self._load()

    def _load(self):
        if not self._context_path.exists():
            return
        with open(self._context_path, "r") as f:
            try:
                uris = json.load(f)
                for uri in uris:
                    node = self.kg.get_node(uri)
                    if node:
                        self.nodes[uri] = node
            except json.JSONDecodeError:
                # File is corrupt or empty, start fresh
                pass

    def _save(self):
        self._context_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._context_path, "w") as f:
            json.dump(list(self.nodes.keys()), f)

    def add(self, node: Node):
        if node.uri in self.nodes:
            self.nodes.move_to_end(node.uri)
        else:
            if len(self.nodes) >= self.max_size:
                self.nodes.popitem(last=False)
            self.nodes[node.uri] = node
        self._save()

    def get(self, uri: str) -> Node | None:
        if uri in self.nodes:
            self.nodes.move_to_end(uri)
            self._save()
            return self.nodes[uri]
        
        node = self.kg.get_node(uri)
        if node:
            self.add(node)
        return node

    def clear(self):
        self.nodes.clear()
        self._save()

    def list_nodes(self) -> list[Node]:
        return list(self.nodes.values())

    def traverse(self, start_uri: str, max_cost: float = 1.0) -> list[Node]:
        if not self.kg.get_node(start_uri):
            return []

        queue = deque([(start_uri, 0.0)])
        visited_costs = {start_uri: 0.0}
        
        context_nodes = []

        while queue:
            current_uri, current_cost = queue.popleft()
            
            node = self.get(current_uri)
            if node:
                if node not in context_nodes:
                    context_nodes.append(node)

            relations = self.kg.get_relations(source_uri=current_uri)
            relations.extend(self.kg.get_relations(target_uri=current_uri))

            for relation in relations:
                if relation.source_uri == current_uri:
                    neighbor_uri = relation.target_uri
                else:
                    neighbor_uri = relation.source_uri

                new_cost = current_cost + relation.weight
                if new_cost <= max_cost:
                    if (
                        neighbor_uri not in visited_costs
                        or new_cost < visited_costs[neighbor_uri]
                    ):
                        visited_costs[neighbor_uri] = new_cost
                        queue.append((neighbor_uri, new_cost))
        
        return context_nodes 