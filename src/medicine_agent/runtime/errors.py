from __future__ import annotations


class PlatformError(Exception):
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SkillNotFoundError(PlatformError):
    code = "SKILL_NOT_FOUND"


class SkillVersionUnsupportedError(PlatformError):
    code = "SKILL_VERSION_UNSUPPORTED"


class UnsupportedFormatError(PlatformError):
    code = "UNSUPPORTED_FORMAT"


class ModelConfigMissingError(PlatformError):
    code = "MODEL_CONFIG_MISSING"


class ModelCallFailedError(PlatformError):
    code = "MODEL_CALL_FAILED"


class PackageValidationError(PlatformError):
    code = "PACKAGE_VALIDATION_FAILED"

