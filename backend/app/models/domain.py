from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SlotStatus(StrEnum):
    """Allowed lifecycle states for a doctor's appointment slot."""

    AVAILABLE = "available"
    BOOKED = "booked"


class AppointmentStatus(StrEnum):
    """Allowed lifecycle states for a patient appointment."""

    BOOKED = "booked"
    CANCELLED = "cancelled"


class Doctor(Base):
    """Doctor profile and weekly consultation schedule metadata."""

    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    speciality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    qualification: Mapped[str] = mapped_column(String(150), nullable=False)
    experience: Mapped[int] = mapped_column(Integer, nullable=False)
    consultation_fee: Mapped[float] = mapped_column(Float, nullable=False)
    available_days: Mapped[str] = mapped_column(String(120), nullable=False)

    slots: Mapped[list["Slot"]] = relationship(
        "Slot",
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="Slot.appointment_date, Slot.appointment_time",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="Appointment.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint("experience >= 0", name="ck_doctor_experience_non_negative"),
        CheckConstraint("consultation_fee >= 0", name="ck_doctor_fee_non_negative"),
    )


class Slot(Base):
    """Individual bookable time slot belonging to a doctor."""

    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SlotStatus.AVAILABLE.value,
        index=True,
    )

    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="slots")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="slot",
    )

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "appointment_date",
            "appointment_time",
            name="uq_doctor_slot_datetime",
        ),
        CheckConstraint(
            "status IN ('available', 'booked')",
            name="ck_slot_status",
        ),
    )


class Appointment(Base):
    """Patient appointment record linked to both a doctor and a specific slot."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_phone: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("slots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AppointmentStatus.BOOKED.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    slot: Mapped["Slot"] = relationship("Slot", back_populates="appointments")

    __table_args__ = (
        CheckConstraint(
            "status IN ('booked', 'cancelled')",
            name="ck_appointment_status",
        ),
        Index(
            "uq_active_appointment_per_slot",
            "slot_id",
            unique=True,
            sqlite_where=text("status = 'booked'"),
        ),
    )
