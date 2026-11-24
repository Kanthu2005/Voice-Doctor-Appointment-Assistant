from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error payload returned for domain and server errors."""

    detail: str


class ValidationErrorResponse(BaseModel):
    """Validation error payload returned for malformed requests."""

    detail: str
    errors: list[dict[str, object]]
