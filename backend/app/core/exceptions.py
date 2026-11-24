"""Domain-specific exceptions mapped to HTTP status codes in FastAPI."""


class DomainError(Exception):
    """Base exception for domain and business-rule errors."""

    status_code: int = 400
    detail: str = "Domain operation failed."

    def __init__(self, detail: str | None = None, status_code: int | None = None) -> None:
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    status_code = 404
    detail = "Resource not found."


class ConflictError(DomainError):
    """Raised when an operation conflicts with current resource state."""

    status_code = 409
    detail = "Operation conflicts with current state."


class ValidationDomainError(DomainError):
    """Raised when domain input fails business validation."""

    status_code = 422
    detail = "Validation failed."


class DoctorNotFoundError(NotFoundError):
    detail = "Doctor not found."


class SlotNotFoundError(NotFoundError):
    detail = "Appointment slot not found."


class SlotAlreadyBookedError(ConflictError):
    detail = "Selected appointment slot is already booked."


class DuplicateBookingError(ConflictError):
    detail = "Patient already has an active appointment for this doctor/time."


class AppointmentNotFoundError(NotFoundError):
    detail = "Appointment not found."


class AppointmentAlreadyCancelledError(ConflictError):
    detail = "Appointment is already cancelled."
