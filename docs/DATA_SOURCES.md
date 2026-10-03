# STEP 2 data source decision

Reviewed 2026-10-03. Selected: KRX OPEN API for local noncommercial research.

| Candidate | Advantages | Constraints | Decision |
| --- | --- | --- | --- |
| KRX OPEN API | Exchange-owned official source; stock master, daily stocks, KOSPI/KOSDAQ series; advertised coverage since 2010-01-04 | Authentication and approval per API; noncommercial use, redistribution restrictions, request limits | Selected official route |
| Financial Services Commission / data.go.kr | Explicitly free official REST; stock and index services | Advertised index coverage since 2020; next business day after 13:00 publication; restrictive license | Alternative if KRX approval unavailable; not implemented |
| pykrx | Broad Korean stock research helpers | Scraping library, not exchange-approved API contract; upstream changes; new dependency | Not selected |
| FinanceDataReader | Convenient listing and domestic/global time series | Multiple upstream sources; not a single official delivery contract; new dependency | Not selected |

KRX fits the four requested datasets under one source and leaves a longer historical
coverage window for STEP 3. Existing httpx and Pydantic suffice; no packages added.
The OPEN API route is chosen instead of paid feeds. Public pages reviewed do not
state a separate per-call charge; confirm actual conditions during account approval.
Do not assume free means unrestricted redistribution or a real-time service.

## Official references and conditions

- [KRX service catalog](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd)
- [KRX access procedure](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp)
- [KRX terms](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp)
- [FSC stock prices](https://www.data.go.kr/data/15094808/openapi.do)
- [FSC index prices](https://www.data.go.kr/data/15094807/openapi.do)
- [pykrx maintainer documentation](https://github.com/sharebook-kr/pykrx)
- [FinanceDataReader maintainer documentation](https://github.com/FinanceData/FinanceDataReader)

KRX requires a Data Marketplace account, approved authentication key, and separate
approval for each API. Terms restrict use to noncommercial purposes, prohibit third
party data provision, require attribution in data-based screens, cap requests at
10,000 per key per day, and set a one-year access period with renewal. Review updated
terms before distribution or hosting. API operation hours do not guarantee same-day
publication. This implementation conservatively accepts only past Seoul dates.

FSC describes next-business-day publication after 13:00 and noncommercial,
no-redistribution conditions. Its metadata also labels the update cycle real-time;
use the detailed publication description rather than that generic label.

## Implemented contract

HTTPS base: `https://data-dbg.krx.co.kr/svc/apis`.
GET query: `basDd=YYYYMMDD`. Authentication: `AUTH_KEY` request header.
Expected JSON row array: `OutBlock_1`.

| Endpoint | Required approval |
| --- | --- |
| sto/stk_isu_base_info | KOSPI stock basic information |
| sto/ksq_isu_base_info | KOSDAQ stock basic information |
| sto/stk_bydd_trd | KOSPI daily stock trading information |
| sto/ksq_bydd_trd | KOSDAQ daily stock trading information |
| idx/kospi_dd_trd | KOSPI series daily index information |
| idx/kosdaq_dd_trd | KOSDAQ series daily index information |

Master uses `ISU_SRT_CD` as symbol and `ISU_NM` as name. `ISU_CD` in master is the
standard identifier, not its short trading symbol; daily `ISU_CD` is the short
symbol and must join to master. Raw responses retain the other supplied identifiers.
Daily stock prices use `TDD_OPNPRC`, `TDD_HGPRC`, `TDD_LWPRC`, `TDD_CLSPRC`.
Indices use `OPNPRC_IDX`, `HGPRC_IDX`, `LWPRC_IDX`, `CLSPRC_IDX`; exact headline
names are Korean or English KOSPI/KOSDAQ, not KOSPI 200 or KOSDAQ 150.
Both use `BAS_DD`, `ACC_TRDVOL`, and `ACC_TRDVAL`.

Values are source-reported daily prices, not a computed adjusted series. Stocks
are interpreted in KRW, index prices in points, trading value in KRW, and volume
in shares. Do not combine this series with future adjusted-price collectors until
corporate-action policy is defined. Symbols preserve leading zeros and allow
six-character uppercase alphanumeric codes. Scope excludes KONEX and separate
ETF/ETN/ELW endpoints; no common-stock-only filter is imposed.

Missing required prices/volumes fail collection; never replace them with zero.
Missing trading value is nullable. Source-reported suspended-stock zero O/H/L and
zero volume are preserved even when close is nonzero. Prices must otherwise obey
OHLC bounds. SQLite Numeric uses SQLite numeric affinity; it is not arbitrary
precision storage. Monetary precision beyond SQLite's numeric capacity requires
an explicit later schema decision.

## Verification status

Public official catalog, procedure, and terms were readable through web search.
Direct local HTTP access to the dynamic specification page returned 403; detailed
fields/endpoints could not be independently confirmed from a downloaded current
official specification in this session. Tests therefore use synthetic contract
fixtures, not captured production responses. No approved key was available and
no authenticated live collection was performed. Treat adapter live compatibility
and source units as pending verification against approved official specifications
and a real response before relying on the research archive.

After approval: populate `.env` locally, run one published historical date, inspect
row counts/units and the stored raw response, then rerun the same date. Do not send
keys through chat, commit them, or bypass authentication/access restrictions.
