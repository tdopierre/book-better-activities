"""All exceptions."""


class NoSlotFound(Exception):
    """Raised when no slot is found."""


class NotEnoughSlotsFound(Exception):
    """Raised when no enough slots are found."""


class AllBookingAttemptsFailed(Exception):
    """Raised when all booking attempts fail."""

    def __init__(self, job_name: str, errors: list[tuple[int, Exception]]):
        self.job_name = job_name
        self.errors = errors
        error_summary = "\n".join(
            f"  Attempt {idx + 1}: {type(err).__name__}: {err}" for idx, err in errors
        )
        super().__init__(
            f"All {len(errors)} booking attempt(s) failed for job '{job_name}':\n{error_summary}"
        )
