class UiCaseCompilerError(Exception):
    """Base exception for UI case compiler failures."""


class PlanValidationError(UiCaseCompilerError):
    """Raised when an executable plan or step fails schema validation."""


class CompilationError(UiCaseCompilerError):
    """Raised when natural-language or recording compilation fails."""


class RecordingError(UiCaseCompilerError):
    """Raised when recorded browser events cannot be converted into steps."""


class StepExecutionError(UiCaseCompilerError):
    """Raised when a step fails during Playwright execution."""


class StorageError(UiCaseCompilerError):
    """Raised when plans or run results cannot be read or written."""


class ReportError(UiCaseCompilerError):
    """Raised when report rendering or artifact handling fails."""

