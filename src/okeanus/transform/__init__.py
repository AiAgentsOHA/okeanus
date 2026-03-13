"""Transform pipeline for routing blue economy adapter output to structured tables."""
from okeanus.transform.pipeline import transform, TransformResult, MAPPER_REGISTRY
import okeanus.transform.mappers as _mappers  # noqa: F401 -- side-effect: registers all 30 mappers

# Lazy import -- store depends on geoalchemy2/sqlalchemy which may not be
# available in lightweight test environments.
def store_transform_result(*args, **kwargs):  # type: ignore[no-redef]
    from okeanus.transform.store import store_transform_result as _store
    return _store(*args, **kwargs)

__all__ = ["transform", "TransformResult", "MAPPER_REGISTRY", "store_transform_result"]
