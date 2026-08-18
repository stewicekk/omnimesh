# OmniMesh Studio agent/MCP runtime

This package contains the concrete 22-agent registry, a standalone MCP-compatible
JSON-RPC stdio server, deterministic canonical mesh utilities, asset manifests,
pipeline planning, memory storage and model-routing metadata.

It is intentionally dependency-light so the agent/MCP layer can be tested independently
of the native C++ editor and optional AI model workers.
