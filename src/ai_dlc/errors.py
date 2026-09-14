"""The application's own exception base.

Every exception class AI-DLC defines derives from ``AiDlcError`` so entry points can
recognise framework failures with one handler. Existing classes keep their historical
``ValueError`` or ``RuntimeError`` base as well, so callers that catch those keep working
while bare ``ValueError`` raises are migrated to typed errors.
"""

from __future__ import annotations


class AiDlcError(Exception):
    """A failure AI-DLC itself detected and can describe to the user.

    ``exit_code`` is the process exit status a command reports for the failure.
    """

    exit_code = 2


class RefusedError(AiDlcError, ValueError):
    """An operation was refused before any change: invalid input, policy or state."""


class UncertainError(AiDlcError, RuntimeError):
    """An operation may have partially happened; remote or local state needs reconciling."""
