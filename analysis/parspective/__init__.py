"""Parspective Mobile analysis core.

Pipeline: video file -> pose landmarks per frame -> smoothing -> stroke phases -> metrics -> JSON.
"""

__version__ = "0.1.0"

#: Version of the result JSON schema. Bump on any breaking change to the result shape.
SCHEMA_VERSION = "1.0"
