from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    card_id: str
    quantity: int = Field(ge=1, default=1)
    condition: str = Field(default="NM", pattern="^(NM|LP|MP|HP|DMG)$")
    language: str = "en"
    is_foil: bool = False
    purchase_price: float | None = None
    listed_price: float | None = None
    notes: str | None = None


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(ge=0, default=None)
    condition: str | None = Field(default=None, pattern="^(NM|LP|MP|HP|DMG)$")
    purchase_price: float | None = None
    listed_price: float | None = None
    notes: str | None = None
    available_online: bool | None = None
    online_quantity: int | None = None


class InventoryResponse(BaseModel):
    id: int
    card_id: str
    card_name: str | None = None
    quantity: int
    condition: str
    language: str
    is_foil: bool
    purchase_price: float | None
    listed_price: float | None
    notes: str | None
    image_url: str | None = None
    market_price: float | None = None

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    items: list[InventoryResponse]
    total: int
    page: int
    per_page: int
