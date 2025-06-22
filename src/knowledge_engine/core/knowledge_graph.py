import json
import sqlite3
from pathlib import Path

from .models import Node, Relation


class KnowledgeGraph:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    uri TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_uri TEXT NOT NULL,
                    target_uri TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_uri) REFERENCES nodes(uri) ON DELETE CASCADE,
                    FOREIGN KEY (target_uri) REFERENCES nodes(uri) ON DELETE CASCADE,
                    UNIQUE(source_uri, target_uri, relation_type)
                );
            """)

    def add_node(self, node: Node):
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO nodes (uri, node_type, name, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    node_type=excluded.node_type,
                    name=excluded.name,
                    content=excluded.content,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at
                """,
                (
                    node.uri,
                    node.node_type,
                    node.name,
                    node.content,
                    json.dumps(node.metadata),
                    node.created_at,
                    node.updated_at,
                ),
            )

    def get_node(self, uri: str) -> Node | None:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE uri = ?", (uri,))
        row = cursor.fetchone()
        if row:
            return Node(
                uri=row["uri"],
                node_type=row["node_type"],
                name=row["name"],
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    def update_node(self, node: Node):
        with self._conn:
            self._conn.execute(
                """
                UPDATE nodes
                SET node_type = ?, name = ?, content = ?, metadata = ?, updated_at = ?
                WHERE uri = ?
                """,
                (
                    node.node_type,
                    node.name,
                    node.content,
                    json.dumps(node.metadata),
                    node.updated_at,
                    node.uri,
                ),
            )

    def delete_node(self, uri: str):
        with self._conn:
            self._conn.execute("DELETE FROM nodes WHERE uri = ?", (uri,))

    def add_relation(self, relation: Relation):
        with self._conn:
            self._conn.cursor().execute(
                """
                INSERT INTO relations (source_uri, target_uri, relation_type, weight, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_uri, target_uri, relation_type) DO NOTHING
                """,
                (
                    relation.source_uri,
                    relation.target_uri,
                    relation.relation_type,
                    relation.weight,
                    json.dumps(relation.metadata),
                    relation.created_at,
                ),
            )

    def get_relations(
        self, source_uri: str | None = None, target_uri: str | None = None
    ) -> list[Relation]:
        query = "SELECT * FROM relations"
        params = []
        conditions = []

        if source_uri:
            conditions.append("source_uri = ?")
            params.append(source_uri)
        if target_uri:
            conditions.append("target_uri = ?")
            params.append(target_uri)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self._conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            Relation(
                id=row["id"],
                source_uri=row["source_uri"],
                target_uri=row["target_uri"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def delete_relation(self, relation_id: int):
        with self._conn:
            self._conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))

    def delete_relation_by_uris_and_type(self, source_uri: str, target_uri: str, relation_type: str):
        with self._conn:
            self._conn.execute(
                "DELETE FROM relations WHERE source_uri = ? AND target_uri = ? AND relation_type = ?",
                (source_uri, target_uri, relation_type),
            )

    def get_node_count(self) -> int:
        """Returns the total number of nodes in the graph."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        count = cursor.fetchone()
        return count[0] if count else 0

    def get_relation_count(self) -> int:
        """Returns the total number of relations in the graph."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM relations")
        count = cursor.fetchone()
        return count[0] if count else 0

    def get_relations_for_nodes(self, uris: list[str]) -> list[Relation]:
        """Returns all relations that connect the nodes with the given URIs."""
        if not uris:
            return []

        placeholders = ",".join("?" for _ in uris)
        query = f"""
            SELECT * FROM relations
            WHERE source_uri IN ({placeholders})
            AND target_uri IN ({placeholders})
        """
        params = uris + uris
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            Relation(
                id=row["id"],
                source_uri=row["source_uri"],
                target_uri=row["target_uri"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def clear_graph(self):
        with self._conn:
            self._conn.execute("DELETE FROM nodes")
            self._conn.execute("DELETE FROM relations")

    def get_all_nodes_and_relations(self) -> tuple[list[Node], list[Relation]]:
        nodes = self._conn.execute("SELECT * FROM nodes").fetchall()
        relations = self._conn.execute("SELECT * FROM relations").fetchall()

        node_list = [
            Node(
                uri=row["uri"],
                node_type=row["node_type"],
                name=row["name"],
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in nodes
        ]

        relation_list = [
            Relation(
                id=row["id"],
                source_uri=row["source_uri"],
                target_uri=row["target_uri"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )
            for row in relations
        ]
        return node_list, relation_list

    def close(self):
        self._conn.close()

    def move_node(self, old_uri: str, new_uri: str):
        with self._conn:
            # Check if the new URI already exists
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1 FROM nodes WHERE uri = ?", (new_uri,))
            if cursor.fetchone():
                raise ValueError(f"URI '{new_uri}' already exists.")

            # Update the node's URI
            self._conn.execute("UPDATE nodes SET uri = ? WHERE uri = ?", (new_uri, old_uri))
            
            # Update all relations pointing to the old URI
            self._conn.execute("UPDATE relations SET source_uri = ? WHERE source_uri = ?", (new_uri, old_uri))
            self._conn.execute("UPDATE relations SET target_uri = ? WHERE target_uri = ?", (new_uri, old_uri)) 