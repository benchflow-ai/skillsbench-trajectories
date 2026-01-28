# Investment Spending Shock Analysis for Georgia - Implementation Plan

## Overview
Estimate the investment spending shock impact on Georgia's economy using Cobb-Douglas production function analysis in Excel. The investment will be 6.5 billion USD over 8 years starting from 2026.

## Task Breakdown

### STEP 1: Data Collection
#### 1.1 PWT Database
- Source: https://www.rug.nl/ggdc/productivity/pwt/?lang=en
- Task: Extract relevant data for Georgia and populate columns B and C in "PWT" sheet
- Need to: Read metadata to understand variable definitions

#### 1.2 IMF WEO Database (using Playwright MCP)
- Get real GDP level and growth rate from 2000-2027
- Populate "WEO_Data" sheet
- Extend 2027 growth rate until 2043
- Calculate projected real GDP based on extended growth rates

#### 1.3 ECB Fixed Capital Consumption Data
- Source: https://data.ecb.europa.eu/data/geographical-areas/georgia
- Extract annual consumption of fixed capital (depreciation) for Georgia
- Populate Column C in "CFC data" sheet
- Link capital stock data from PWT
- Calculate depreciation rate using formulas

#### 1.4 Production Sheet - Depreciation Rate
- Calculate average depreciation rate for most recent 8 years
- Use formula to populate cell B3

### STEP 2: HP Filter in Excel
- Link data from other sheets to D6:D27 and E6:E27 in "Production"
- Calculate LnK and LnY columns
- Use Excel Solver to find smoothed LnZ_HP trend
- Calculate second-order differences and residuals as sanity checks
- Set up objective function in P5 and use Solver to minimize

### STEP 3: Production Function Analysis
- Link K and Y from relevant sheets
- Calculate K/Y ratios from 2002-2023
- Extend K using fixed anchor (average K/Y of most recent 9 years)
- Link HP filtered LnZ trend and extend to 2041 using TREND formula
- Calculate Ystar_base using capital's share parameter
- Link Investment data and calculate deltaK and K_With
- Calculate Ystar_with with new capital
- Complete remaining calculations

## Data Sources to Access
1. PWT (Penn World Table) - https://www.rug.nl/ggdc/productivity/pwt/?lang=en
2. IMF WEO - https://www.imf.org/external/datamapper/
3. ECB Statistical Data Warehouse - https://data.ecb.europa.eu/data/geographical-areas/georgia

## Output
- File: `test-supply.xlsx`
- Multiple sheets with calculations maintained as formulas
- No hardcoded values in calculation cells

## Key Implementation Notes
- Use Playwright MCP for web data collection
- Maintain all formulas in Excel (no hardcoded numbers)
- HP Filter optimization using Excel Solver with lambda = 1600 (standard for annual data)
- Cobb-Douglas production function: Y = A * K^α * L^(1-α)
- Capital stock extrapolation using K/Y ratios
- Capital share (α) to be estimated from production data or derived from wage/income shares
- Labor input assumptions: will be clearly documented in Excel file

## Implementation Steps

### Phase 1: Data Collection & Excel Setup
1. Create test-supply.xlsx with required sheets:
   - PWT (Penn World Table data for Georgia)
   - WEO_Data (IMF GDP data and projections)
   - CFC data (ECB depreciation data)
   - Production (Main analysis sheet)
   - Investment (Investment shock parameters)
   - HP_Filter (Intermediate calculations)

2. Use Playwright MCP to access web data sources and manually populate with formulas referencing external sheets

3. Document all variable definitions and sources in each sheet

### Phase 2: Depreciation Rate Calculation
- Link CFC data from ECB sheet
- Calculate depreciation rates for each year
- Average most recent 8 years, place result in B3 using formula

### Phase 3: HP Filter Implementation
- Link LnK and LnY data to Production sheet
- Set up HP filter structure with LnZ values
- Use Excel Solver to optimize LnZ_HP with lambda=1600
- Verify with sanity checks (second differences, residuals)

### Phase 4: Production Function
- Calculate K/Y ratios for historical period
- Extend capital stock using fixed anchor
- Apply Cobb-Douglas formula: Ystar_base = exp(lnZ) * Y * (K/Y)^α
- Calculate shock scenario with new investment
- Complete impact analysis

### Phase 5: Verification
- Ensure all calculation cells use formulas (no hardcoded values)
- Verify data links across sheets work correctly
- Check HP filter convergence and Solver solution
- Validate production function outputs

## Critical Files
- Output: /root/test-supply.xlsx
- All formulas preserved, no hardcoded calculation values

## Assumptions
- HP Filter Lambda: 1600 (annual data standard)
- Capital Share (α): To be derived from production data
- Investment: $6.5B over 8 years (2026-2033)
- Analysis Period: 2000-2043 (base) + shock scenario
