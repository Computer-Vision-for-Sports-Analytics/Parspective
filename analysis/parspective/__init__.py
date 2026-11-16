"""Parspective Mobile analysis core.

Pipeline: video file -> pose landmarks per frame -> smoothing -> stroke phases -> metrics -> JSON.

    from parspective import analyze
    result = analyze("putt.mp4", hand="right", overlay_path="out.mp4")
    print(len(result.strokes), "strokes found")
"""

__version__ = "0.1.0"

#: Version of the result JSON schema. Bump on any breaking change to the result shape.
SCHEMA_VERSION = "1.0"


def analyze(*args, **kwargs):
    """Analyze one putting video. See :func:`parspective.pipeline.analyze`."""
    from .pipeline import analyze as _analyze  # lazy: keeps `import parspective` light

    return _analyze(*args, **kwargs)
