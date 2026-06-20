export interface Card {
  id: string
  game_id: string
  name: string
  set: { code: string; name: string }
  rarity: string | null
  image_url: string | null
  price: { market: number | null; currency: string } | null
  inventory: { quantity: number; conditions: string[] } | null
}
