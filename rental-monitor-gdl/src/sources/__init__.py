from .demo_source import DemoSource
from .inmuebles24_stub import Inmuebles24Stub
from .vivanuncios_stub import VivanunciosStub
from .lamudi_stub import LamudiStub
from .manual_feed import ManualFeedSource

ALL_SOURCES = {
    "demo": DemoSource,
    "manual": ManualFeedSource,
    "inmuebles24": Inmuebles24Stub,
    "vivanuncios": VivanunciosStub,
    "lamudi": LamudiStub,
}


def get_sources(names: list[str] | None = None):
    if names is None:
        names = list(ALL_SOURCES.keys())
    sources = []
    for name in names:
        cls = ALL_SOURCES.get(name)
        if cls:
            sources.append(cls())
        else:
            import logging
            logging.getLogger(__name__).warning("Unknown source: %s", name)
    return sources
