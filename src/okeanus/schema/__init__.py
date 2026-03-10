"""Domain schema models -- SQLAlchemy ORM + Pydantic types for all observation domains."""

from okeanus.schema.acoustic import (
    AcousticObservation,
    AcousticObservationCreate,
    AcousticObservationRead,
)
from okeanus.schema.base import (
    Base,
    Observation,
    ObservationBase,
    ObservationCreate,
)
from okeanus.schema.biological import (
    BiologicalObservation,
    BiologicalObservationCreate,
    BiologicalObservationRead,
    ObservationMethod,
)
from okeanus.schema.physical import (
    PhysicalObservation,
    PhysicalObservationCreate,
    PhysicalObservationRead,
    PhysicalParameter,
)
from okeanus.schema.satellite import (
    OrbitDirection,
    SatelliteObservation,
    SatelliteObservationCreate,
    SatelliteObservationRead,
)
from okeanus.schema.vessel import (
    VesselObservation,
    VesselObservationCreate,
    VesselObservationRead,
)

__all__ = [
    "Base",
    "Observation",
    "ObservationBase",
    "ObservationCreate",
    "PhysicalObservation",
    "PhysicalObservationCreate",
    "PhysicalObservationRead",
    "PhysicalParameter",
    "VesselObservation",
    "VesselObservationCreate",
    "VesselObservationRead",
    "AcousticObservation",
    "AcousticObservationCreate",
    "AcousticObservationRead",
    "BiologicalObservation",
    "BiologicalObservationCreate",
    "BiologicalObservationRead",
    "ObservationMethod",
    "OrbitDirection",
    "SatelliteObservation",
    "SatelliteObservationCreate",
    "SatelliteObservationRead",
]
