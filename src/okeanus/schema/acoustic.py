"""Acoustic event observations.

Sources: hydrophone arrays, passive acoustic monitoring (PAM) systems,
automated acoustic classifiers.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Observation, ObservationBase, ObservationCreate


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class AcousticObservation(Observation):
    """A detected acoustic event.

    Captures frequency band, duration, sound pressure level, and optional
    automatic classification.  When the classifier identifies a biological
    source the ``aphia_id`` on the parent row links to WoRMS taxonomy.
    """

    __mapper_args__ = {"polymorphic_identity": "acoustic"}

    frequency_min_hz: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Lower bound of detected frequency band (Hz)"
    )
    frequency_max_hz: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Upper bound of detected frequency band (Hz)"
    )
    duration_s: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Duration of the acoustic event in seconds"
    )
    spl_db: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Sound pressure level in dB re 1 uPa"
    )
    classification: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True, doc="Classifier label for the event"
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Classifier confidence in [0.0, 1.0]"
    )
    classifier_model: Mapped[str | None] = mapped_column(
        String(120), nullable=True, doc="Name/version of the classification model"
    )


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class AcousticObservationRead(ObservationBase):
    """API response model for an acoustic observation."""

    model_config = ConfigDict(from_attributes=True)

    frequency_min_hz: float
    frequency_max_hz: float
    duration_s: float
    spl_db: float
    classification: str | None = None
    confidence: float | None = None
    classifier_model: str | None = None


class AcousticObservationCreate(ObservationCreate):
    """API request model for creating an acoustic observation."""

    frequency_min_hz: float = Field(..., gt=0.0)
    frequency_max_hz: float = Field(..., gt=0.0)
    duration_s: float = Field(..., gt=0.0)
    spl_db: float
    classification: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    classifier_model: str | None = None
