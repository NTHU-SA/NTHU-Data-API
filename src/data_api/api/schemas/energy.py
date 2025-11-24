"""Energy API schemas."""

from pydantic import BaseModel, Field


class EnergyElectricityInfo(BaseModel):
    """Electricity usage information."""

    name: str = Field(..., description="電力名稱")
    data: int = Field(..., description="電力使用量")
    capacity: int = Field(..., description="電力容量")
    unit: str = Field(..., description="單位")
    last_updated: str = Field(..., description="最後更新時間")
