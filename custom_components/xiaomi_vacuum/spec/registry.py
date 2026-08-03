"""Lookup from a device's model string to its :class:`ModelSpec`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import LOGGER  # noqa: TID252
from .b108gl import B108GL
from .d109gl import D109GL

if TYPE_CHECKING:
    from .model_spec import ModelSpec

MODELS: dict[str, ModelSpec] = {
    D109GL.model: D109GL,
    B108GL.model: B108GL,
}

#: Tuple form for documentation / discovery-side checks.
SUPPORTED_MODELS: tuple[str, ...] = tuple(MODELS)

#: Fallback when neither the live handshake nor the cached snapshot supplies a
#: model (kept as the historical primary model).
DEFAULT_MODEL: str = D109GL.model


def get_spec(model: str | None) -> ModelSpec:
    """
    Resolve the spec for a model string, falling back to the default.

    An unknown model logs a warning and falls back to the X20 Max spec so that
    setup never hard-fails on a model we simply have not added yet; the
    behaviour may be partially wrong but local control stays usable.
    """
    if model and model in MODELS:
        return MODELS[model]
    LOGGER.warning(
        "Unknown vacuum model %r; falling back to %s. Open an issue if a new "
        "model needs to be added.",
        model,
        DEFAULT_MODEL,
    )
    return MODELS[DEFAULT_MODEL]
