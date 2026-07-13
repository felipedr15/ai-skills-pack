"""Knowledge graph generation and validation modules."""

SCHEMA_VERSION = "1.0.0"
GENERATOR = "ai-os-knowledge-graph"

NODE_TYPES = {"skill", "memory", "project", "document", "platform", "tool", "concept"}
EDGE_TYPES = {"contains", "references", "related_to", "supports", "uses", "belongs_to", "generated_from"}
