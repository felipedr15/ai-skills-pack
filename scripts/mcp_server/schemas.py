"""Tool and resource schemas for the MCP server."""
from __future__ import annotations

TOOLS = [
    {
        "name": "ai_os_status",
        "description": "Get AI OS repository status, validation state, and generated artifact availability.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_ai_os",
        "description": "Search the AI OS repository using semantic discovery.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "type": {"type": "string", "description": "Filter by entity type"},
                "path": {"type": "string", "description": "Filter by source path prefix"},
                "relationship": {"type": "string", "description": "Filter by relationship type"},
                "exact": {"type": "boolean", "description": "Exact match only"},
                "case_sensitive": {"type": "boolean", "description": "Case-sensitive search"},
                "limit": {"type": "integer", "description": "Maximum results (max 100)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "explain_search_result",
        "description": "Explain why an entity matches a search query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Entity or node ID"},
                "query": {"type": "string", "description": "Search query to explain against"},
            },
            "required": ["entity_id", "query"],
        },
    },
    {
        "name": "get_entity",
        "description": "Get a knowledge graph entity by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Node ID in the knowledge graph"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "get_related_entities",
        "description": "Get entities related to a given node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Node ID"},
                "relationship": {"type": "string", "description": "Filter by relationship type"},
                "direction": {"type": "string", "enum": ["inbound", "outbound", ""], "description": "Filter by direction"},
                "limit": {"type": "integer", "description": "Maximum results"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "traverse_knowledge_graph",
        "description": "Traverse the knowledge graph from a starting node using BFS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Starting node ID"},
                "depth": {"type": "integer", "description": "Traversal depth (1-5)"},
                "relationship": {"type": "string", "description": "Filter by relationship type"},
                "direction": {"type": "string", "enum": ["inbound", "outbound", ""], "description": "Filter direction"},
                "limit": {"type": "integer", "description": "Maximum results"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "find_knowledge_path",
        "description": "Find shortest path between two knowledge graph nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_id": {"type": "string", "description": "Source node ID"},
                "target_id": {"type": "string", "description": "Target node ID"},
                "relationship": {"type": "string", "description": "Optional relationship filter"},
            },
            "required": ["source_id", "target_id"],
        },
    },
    {
        "name": "list_skills",
        "description": "List registered AI OS skills with optional filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "Filter by platform"},
                "tool": {"type": "string", "description": "Filter by tool"},
                "category": {"type": "string", "description": "Filter by category"},
                "path": {"type": "string", "description": "Filter by path prefix"},
                "limit": {"type": "integer", "description": "Maximum results"},
                "cursor": {"type": "integer", "description": "Pagination cursor"},
            },
            "required": [],
        },
    },
    {
        "name": "get_skill",
        "description": "Get a specific skill by ID or path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill ID"},
                "source_path": {"type": "string", "description": "Skill source path"},
            },
            "required": [],
        },
    },
    {
        "name": "list_memory_summaries",
        "description": "List memory record summaries. Never returns full sensitive content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project"},
                "category": {"type": "string", "description": "Filter by memory type"},
                "source": {"type": "string", "description": "Filter by source"},
                "limit": {"type": "integer", "description": "Maximum results"},
                "cursor": {"type": "integer", "description": "Pagination cursor"},
            },
            "required": [],
        },
    },
    {
        "name": "get_memory_summary",
        "description": "Get a memory record summary by ID. Never returns full sensitive content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory record ID"},
            },
            "required": ["memory_id"],
        },
    },
    {
        "name": "get_repository_file",
        "description": "Get metadata and bounded safe excerpt of a repository text file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "Repository-relative file path"},
                "max_chars": {"type": "integer", "description": "Maximum excerpt characters (max 2000)"},
            },
            "required": ["source_path"],
        },
    },
    {
        "name": "get_validation_status",
        "description": "Get current validation status of generated artifacts.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_generated_artifacts",
        "description": "List all generated artifacts with their current status.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_dashboard_status",
        "description": "Get dashboard build and availability status.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
]

RESOURCES = [
    {"uri": "ai-os://status", "name": "AI OS Status", "description": "Repository status and artifact availability", "mimeType": "application/json"},
    {"uri": "ai-os://architecture", "name": "Architecture", "description": "AI OS architecture summary", "mimeType": "text/markdown"},
    {"uri": "ai-os://repository-map", "name": "Repository Map", "description": "Generated repository file map", "mimeType": "text/markdown"},
    {"uri": "ai-os://skills", "name": "Skill Registry", "description": "Generated skill registry summary", "mimeType": "text/markdown"},
    {"uri": "ai-os://memory-summary", "name": "Memory Summary", "description": "Generated memory index summary", "mimeType": "text/markdown"},
    {"uri": "ai-os://knowledge-graph", "name": "Knowledge Graph", "description": "Generated knowledge graph summary", "mimeType": "text/markdown"},
    {"uri": "ai-os://discovery", "name": "Discovery Index", "description": "Generated discovery index summary", "mimeType": "text/markdown"},
    {"uri": "ai-os://dashboard", "name": "Dashboard", "description": "Dashboard data summary", "mimeType": "application/json"},
    {"uri": "ai-os://validation", "name": "Validation", "description": "Validation status summary", "mimeType": "application/json"},
]
