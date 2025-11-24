"""
Buses domain adapters.

Convert between domain models and API schemas.
In this case, the domain service returns dict structures that match
the Pydantic schemas, so conversion is minimal.
"""

__all__ = []

# Note: The buses service returns dict structures that are directly
# compatible with Pydantic schemas, so no explicit adapters are needed.
# If domain models were returned directly, we would add:
#
# def bus_stop_to_schema(stop: models.Stop) -> dict:
#     return {
#         "name": stop.name,
#         "name_en": stop.name_en,
#         "latitude": stop.latitude,
#         "longitude": stop.longitude,
#     }
