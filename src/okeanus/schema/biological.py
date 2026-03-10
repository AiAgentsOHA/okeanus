"""Biological observations -- species occurrence and abundance.

Sources: OBIS, GBIF, eDNA metabarcoding, visual surveys, camera traps,
net/trawl surveys, satellite-derived chlorophyll.
"""

from __future__ import annotations

import enum

from pydantic import ConfigDict, Field
from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Observation, ObservationBase, ObservationCreate


class ObservationMethod(enum.StrEnum):
    """Method used to observe the organism."""

    VISUAL = "VISUAL"
    EDNA = "EDNA"
    ACOUSTIC = "ACOUSTIC"
    CAMERA = "CAMERA"
    NET_TRAWL = "NET_TRAWL"
    SATELLITE = "SATELLITE"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class BiologicalObservation(Observation):
    """A biological occurrence record.

    Links to the WoRMS taxonomy via ``aphia_id`` on the parent table.
    Stores taxon metadata, abundance, biomass, and observation methodology.
    """

    __mapper_args__ = {"polymorphic_identity": "biological"}

    taxon_aphia_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True,
        doc="WoRMS AphiaID (duplicated from parent for query convenience)",
    )
    taxon_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, doc="Scientific name of the taxon"
    )
    taxon_rank: Mapped[str | None] = mapped_column(
        String(50), nullable=True, doc="Taxonomic rank (e.g. species, genus, family)"
    )
    abundance: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Organism count or density"
    )
    biomass_kg: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Biomass in kilograms"
    )
    observation_method: Mapped[ObservationMethod | None] = mapped_column(
        Enum(ObservationMethod, name="observation_method", create_constraint=True),
        nullable=True,
        index=True,
    )
    life_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True, doc="Life stage (e.g. adult, juvenile, larva, egg)"
    )


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class BiologicalObservationRead(ObservationBase):
    """API response model for a biological observation."""

    model_config = ConfigDict(from_attributes=True)

    taxon_aphia_id: int | None = None
    taxon_name: str
    taxon_rank: str
    abundance: float | None = None
    biomass_kg: float | None = None
    observation_method: ObservationMethod
    life_stage: str | None = None


class BiologicalObservationCreate(ObservationCreate):
    """API request model for creating a biological observation."""

    taxon_aphia_id: int | None = None
    taxon_name: str
    taxon_rank: str
    abundance: float | None = Field(None, ge=0.0)
    biomass_kg: float | None = Field(None, ge=0.0)
    observation_method: ObservationMethod
    life_stage: str | None = None
