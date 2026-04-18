from __future__ import annotations

from aragora.server.handlers import ALL_HANDLERS
from aragora.server.handlers.pipeline_graph import PipelineGraphHandler
from aragora.server.openapi import generate_openapi_schema


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _operation_methods(path_spec: dict[str, object]) -> set[str]:
    return {method for method in path_spec if method in HTTP_METHODS}


def test_pipeline_graph_handler_participates_in_all_handlers() -> None:
    assert PipelineGraphHandler in set(ALL_HANDLERS)


def test_pipeline_graph_routes_appear_in_generated_openapi_with_declared_methods() -> None:
    paths = generate_openapi_schema()["paths"]

    expected_methods = {
        "/api/v1/pipeline/graph": {"get", "post"},
        "/api/v1/pipeline/graph/{id}": {"get", "delete"},
        "/api/v1/pipeline/graph/{id}/node": {"post"},
        "/api/v1/pipeline/graph/{id}/node/{node_id}": {"delete"},
        "/api/v1/pipeline/graph/{id}/nodes": {"get"},
        "/api/v1/pipeline/graph/{id}/promote": {"post"},
        "/api/v1/pipeline/graph/{id}/provenance/{node_id}": {"get"},
        "/api/v1/pipeline/graph/{id}/react-flow": {"get"},
        "/api/v1/pipeline/graph/{id}/integrity": {"get"},
        "/api/v1/pipeline/graph/{id}/suggestions": {"get"},
        "/api/v1/pipeline/graph/{id}/node/{nodeId}/reassign": {"post"},
    }

    for path, methods in expected_methods.items():
        assert path in paths
        assert _operation_methods(paths[path]) == methods
