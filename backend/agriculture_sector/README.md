# Agriculture data integration

The Agriculture agent calls its FastMCP server (`mcp_server.py`). Crop and
mandi observations use the
[community data.gov.in MCP](https://github.com/Yash-Kavaiya/data-gov-in-mcp)
vendored in `backend/data_gov_in_mcp/` (MIT license). The vendor code retains
its `get_dataset`, `get_dataset_fields`, `get_dataset_summary`,
`paginate_dataset`, and `filter_dataset` tools. Local fixes pass API filters
and sort fields using the data.gov.in parameter names, read the API's `field`
schema, and avoid logging URLs containing the API key. The MCP's catalogue
search is a placeholder; resource IDs are configured explicitly.

Set `DATA_GOV_IN_API_KEY` in the backend environment. The application passes
it to the in-process MCP client without putting it in tool arguments or
reports. A missing key returns a `not_configured` source error.

## Verified resources (live check: 2026-10-14)

| Purpose | Resource ID | Source fields | Unit/period |
|---|---|---|---|
| Daily mandi prices | `9ef84268-d588-465a-a308-a864a43d0070` | `state`, `district`, `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`, `max_price`, `modal_price` | INR/quintal; daily date |
| District-season crop production | `35be999b-0208-4354-b557-f6ca9a5355de` | `state_name`, `district_name`, `crop_year`, `season`, `crop`, `area_`, `production_` | hectares, tonnes; crop year |

The resource IDs, titles and field contracts are in `data_gov_resources.py`.
The issuing organization shown on the portal is the Ministry of Agriculture
and Farmers Welfare / Department of Agriculture and Farmers Welfare. Every
fetch validates the MCP schema and a live sample record before returning rows.
The API's `total` describes the filtered result, so the adapter requests
100-row pages until that count is reached. It stops on missing, duplicate,
repeated or changing pages. A query matching more than 5,000 rows asks for
a narrower scope. Crop years are filtered server-side, then checked again
against the returned records. Mandi dates are filtered locally because this
resource rejected arrival-date sorting in the live API check.

The crop resource's latest Wheat year seen on 2026-10-14 was **2015**. Its
Wheat rows had very different district-season coverage in 2014 and 2015, so
the report does not infer an all-India production trend by summing them.
An explicitly requested 2023 crop year returns a missing-period error.
Yield is calculated as `production_ / area_` only for positive area and valid
production; it is labeled calculated and uses tonnes/hectare.

Historical rainfall and daily weather use Open-Meteo's Indian geocoder and
archive/forecast APIs. The seven completed days ending 2026-10-13 for Mumbai
returned seven dated precipitation readings in millimetres. These are grid
estimates at a reference coordinate, not IMD station data or city totals.

The current Wheat MSP is parsed from the live [official PIB Rabi MSP
announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2316956&lang=2&reg=48),
not stored as a number in code. On 2026-10-14, the active RMS 2026-27 value was
INR 2,585/quintal and the next approved RMS 2027-28 value was INR 2,610/quintal.
The source table and marketing season are validated before returning rows.
This URL must be reviewed when a newer MSP release is published; an outdated
release is rejected. A matching current data.gov.in API resource was not
verified, so this official release supplies MSP instead.

Fertilizer and irrigation retain their MoSPI MCP routes. Crop and mandi stay
on the two verified data.gov.in resources. If a dataset is unavailable or old,
Tavily may add linked source excerpts, preferably from official domains.
Those excerpts are labeled separately from verified observations. FAOSTAT and
CEDA are not used for Agriculture routing. Market arrivals, official monsoon
status, schemes, and nationally representative state rankings still need
appropriate verified data. Other MacroGraph sectors keep their own routes.

## Reports and testing

Reports show source observations, a short LLM explanation when available,
resource title/ID, publisher, API URL, requested and actual periods, source
fields, units, retrieval timestamp, and calculation labels. Full original
rows remain in the A2A `agriculture_sector_data` payload. Derived growth
requires matching crop, geography, season, variety, grade, units, and
consecutive years.

Run the offline tests and price-sector regression tests from the repository
root:

```powershell
python -m pytest backend/agriculture_sector/test_agriculture.py backend/tests/test_prices_mospi.py backend/tests/test_prices_wpi_metadata.py -q -p no:cacheprovider
```

The previous multisource Agriculture tests are preserved in
`legacy_agriculture_checks.py` for reference. They describe the older source
configuration and are not part of the active test suite.
