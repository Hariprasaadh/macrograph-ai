// Fixed coordinates for the 20 canonical indicators (viewBox 980 x 480). No layout library needed.
export const KG_VIEWBOX = { width: 980, height: 480 };

const P = 'in.macro.';
export const KG_POSITIONS: Record<string, { x: number; y: number }> = {
  [`${P}prices.brent_crude`]: { x: 70, y: 100 },
  [`${P}prices.wpi_all`]: { x: 210, y: 100 },
  [`${P}prices.cpi_headline`]: { x: 350, y: 100 },
  [`${P}monetary.repo_rate`]: { x: 490, y: 100 },
  [`${P}monetary.bank_credit_growth`]: { x: 630, y: 100 },
  [`${P}real.iip_growth`]: { x: 770, y: 100 },
  [`${P}real.gdp_growth`]: { x: 910, y: 100 },
  [`${P}external.trade_balance`]: { x: 210, y: 220 },
  [`${P}external.usd_inr`]: { x: 350, y: 220 },
  [`${P}capmarkets.bank_nifty`]: { x: 630, y: 220 },
  [`${P}fiscal.central_capex`]: { x: 70, y: 330 },
  [`${P}real.gfcf_investment`]: { x: 210, y: 330 },
  [`${P}agri.monsoon_departure`]: { x: 70, y: 430 },
  [`${P}agri.foodgrain_production`]: { x: 210, y: 430 },
  [`${P}prices.cpi_food`]: { x: 350, y: 430 },
  [`${P}fiscal.debt_to_gdp`]: { x: 560, y: 330 },
  [`${P}external.forex_reserves`]: { x: 700, y: 330 },
  [`${P}capmarkets.nifty_50`]: { x: 840, y: 330 },
  [`${P}capmarkets.india_vix`]: { x: 560, y: 430 },
  [`${P}labour.epfo_additions`]: { x: 700, y: 430 },
};

export function nodePosition(id: string, index: number): { x: number; y: number } {
  return KG_POSITIONS[id] ?? { x: 80 + (index % 8) * 110, y: 40 + Math.floor(index / 8) * 60 };
}

export const SECTOR_COLORS: Record<string, string> = {
  real_economy: '#34d399',
  prices_inflation: '#f59e0b',
  monetary_banking: '#818cf8',
  fiscal: '#f472b6',
  external: '#22d3ee',
  capital_markets: '#a78bfa',
  agriculture_rural: '#84cc16',
  labour_employment: '#fb923c',
};
