"""Errors of the explanation (`DT-069`)."""

from __future__ import annotations


class ExplanationError(ValueError):
    """The input violates the contract of `DT-068` (unknown outcome, missing fact for a template...)."""


class UnverifiedFigureError(ValueError):
    """Internal: the generated text contains figures that are not the ``display`` of any fact (RS-010).

    It never reaches the client: ``explain`` turns it into ``DEGRADED``. Only the offending figures are
    kept, never the rejected text.
    """

    def __init__(self, figures: tuple[str, ...]) -> None:
        self.figures = figures
        super().__init__(f"{len(figures)} unverified figure(s)")


class GeneratorUnavailable(RuntimeError):
    """Internal: a remote generator (U13, Azure OpenAI) gave no usable text: timeout, HTTP error, rate limit or
    an unexpected answer. ``explain`` falls back to the template (`DT-101` point 8); the message never contains
    the prompt, the answer or a token."""
