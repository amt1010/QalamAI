"""HTTP delivery layer.

Owns the wire contract and nothing else: request/response schemas, routing,
error translation, and the ASGI application factory. All reasoning lives below
this layer, so the same platform can later be driven by a gRPC service, a batch
CLI, or an on-device runtime without reimplementation.
"""
