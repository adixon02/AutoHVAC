# Code Compliance & Energy Regulation Data Strategy

## Overview
This document outlines the strategy for aggregating building code compliance and energy regulation data by ZIP code for AutoHVAC. This is planned for post-MVP implementation.

## MVP Approach (Phase 0)
For the initial MVP, we will:
- Use hardcoded climate zones for major metros
- Implement basic Manual J calculations with standard assumptions
- Focus on common building codes (2018/2021 IECC)
- Add manual override options for users

## Data Architecture Approach

### Hybrid Data Strategy
Implement a three-tier data architecture:
1. **Primary APIs** - Real-time data from authoritative sources
2. **Cached Database** - Local storage of frequently accessed data
3. **Fallback Sources** - Manual data entry and crowdsourcing

## Primary Data Sources

### Building Codes
1. **ICC Code Connect API** (Primary)
   - Direct access to International Code Council standards
   - Covers model codes used by most US jurisdictions
   - Integration: RESTful API with authentication
   - URL: https://solutions.iccsafe.org/codeconnect

2. **BuildZoom API** (Comprehensive)
   - 2,400 jurisdictions covering 90% of US population
   - Historical permit data and code requirements
   - Commercial API with tiered pricing
   - URL: https://www.buildzoom.com/data

3. **Shovels.ai** (Alternative)
   - 170 million building permits database
   - 10,000+ building permit jurisdictions
   - Geospatial API in development
   - URL: https://www.shovels.ai/

4. **Municipal Open Data Portals**
   - Direct access to local jurisdiction data
   - BLDS (Building & Land Development Specification) standard
   - Free but requires integration with multiple endpoints
   - Key cities: Chicago, Austin, NYC, LA

### Energy Regulations & Climate Data
1. **ClimateZones.us API**
   - IECC climate zones by ZIP code
   - DOE Building America designations
   - Token-based authentication
   - Endpoint: https://climatezone.us/api/locations/<zipcode>

2. **ASHRAE Standards**
   - County-level climate zone assignments
   - Manual mapping required for ZIP codes that cross counties
   - Challenge: 1,413 ZIP codes overlap multiple climate zones

3. **RESNET National Registry**
   - HERS Index requirements by jurisdiction
   - Energy code compliance mappings
   - Registry: https://www1.resnet.us/registry/

## Implementation Architecture

### Backend Service Design
```
1. Code Compliance Service
   - ZIP Code → Jurisdiction mapping
   - Jurisdiction → Building codes lookup
   - Code version tracking
   - Amendment management

2. Energy Regulation Service
   - ZIP → Climate zone determination
   - Energy efficiency requirements
   - Renewable energy mandates
   - Local utility programs

3. Data Aggregation Layer
   - API orchestration
   - Response caching
   - Fallback logic
   - Data normalization
```

### Database Schema
```sql
-- Core jurisdiction mapping
CREATE TABLE jurisdictions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(50), -- city, county, state
    state VARCHAR(2),
    county VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ZIP to jurisdiction mapping (many-to-many)
CREATE TABLE zip_jurisdictions (
    zip VARCHAR(10),
    jurisdiction_id INT REFERENCES jurisdictions(id),
    is_primary BOOLEAN DEFAULT false,
    coverage_percent DECIMAL(5,2),
    PRIMARY KEY (zip, jurisdiction_id)
);

-- Building codes by jurisdiction
CREATE TABLE building_codes (
    id SERIAL PRIMARY KEY,
    jurisdiction_id INT REFERENCES jurisdictions(id),
    code_type VARCHAR(50), -- residential, commercial, mechanical
    code_standard VARCHAR(50), -- IECC, IBC, IMC
    version VARCHAR(20),
    effective_date DATE,
    amendments JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Climate zones by ZIP
CREATE TABLE climate_zones (
    zip VARCHAR(10) PRIMARY KEY,
    zone_iecc VARCHAR(10),
    zone_ashrae VARCHAR(10),
    zone_doe VARCHAR(20),
    heating_degree_days INT,
    cooling_degree_days INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Energy requirements by jurisdiction
CREATE TABLE energy_requirements (
    id SERIAL PRIMARY KEY,
    jurisdiction_id INT REFERENCES jurisdictions(id),
    requirement_type VARCHAR(50),
    requirement_value JSON,
    effective_date DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Track data sources and freshness
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100),
    source_type VARCHAR(50),
    last_updated TIMESTAMP,
    reliability_score DECIMAL(3,2),
    api_endpoint VARCHAR(500),
    notes TEXT
);
```

## Data Collection Strategy

### Phase 1: Core Coverage (Months 1-2)
1. Integrate ICC Code Connect API for model codes
2. Set up ClimateZones.us for climate data
3. Build ZIP → Jurisdiction mapping database
4. Cover top 100 metro areas (70% of US population)

### Phase 2: Expanded Coverage (Months 3-4)
1. Add BuildZoom or Shovels.ai integration
2. Integrate municipal open data feeds
3. Add RESNET HERS requirements
4. Reach 90% population coverage

### Phase 3: Complete Coverage (Months 5-6)
1. Manual data entry for remaining jurisdictions
2. Crowdsourcing verification system
3. Regular update cycles established

## Technical Implementation

### API Integration Service
```python
# Example structure for API adapters
class CodeComplianceAdapter:
    def get_jurisdiction_by_zip(self, zip_code: str) -> Jurisdiction
    def get_building_codes(self, jurisdiction_id: int) -> List[BuildingCode]
    def get_climate_zone(self, zip_code: str) -> ClimateZone

class ICCAdapter(CodeComplianceAdapter):
    # Implementation for ICC Code Connect

class BuildZoomAdapter(CodeComplianceAdapter):
    # Implementation for BuildZoom API

class ClimateZonesAdapter(CodeComplianceAdapter):
    # Implementation for ClimateZones.us
```

### Caching Strategy
- Building codes: Cache for 30 days (changes are annual)
- Climate zones: Cache indefinitely (rarely change)
- Jurisdiction mappings: Cache for 90 days
- API responses: Cache based on source update frequency

### Data Quality Assurance
- Cross-reference multiple sources
- Flag conflicting data for manual review
- Track data freshness and accuracy
- Implement user feedback mechanism

## Cost Estimates

### API Subscriptions (Monthly)
- ICC Code Connect: ~$500-1000
- BuildZoom/Shovels: ~$1000-2500
- ClimateZones.us: ~$100-300
- Municipal APIs: Mostly free
- **Total: $1,600-3,800/month**

### Development Resources
- Initial integration: 3-4 months
- Ongoing maintenance: 0.5 FTE
- Data quality team: 1-2 contractors

## Challenges & Solutions

### Challenge 1: ZIP codes crossing jurisdictions
**Solution**: Primary jurisdiction assignment with coverage percentages

### Challenge 2: Local code amendments
**Solution**: JSON storage for amendments with manual review process

### Challenge 3: Update frequency
**Solution**: Webhook subscriptions where available, scheduled polling elsewhere

### Challenge 4: Data conflicts
**Solution**: Source reliability scoring and manual arbitration

## MVP Simplifications
For the MVP, we will:
1. Hardcode top 20 metro areas
2. Use only IECC 2018/2021 standards
3. Implement manual override for any location
4. Focus on residential only
5. Skip local amendments

## Future Enhancements
1. Real-time permit fee calculations
2. Local contractor licensing requirements
3. Utility rebate program integration
4. Solar/renewable requirements
5. Historic district restrictions
6. HOA regulation database

## Resources & References
- ICC: https://www.iccsafe.org/
- ASHRAE: https://www.ashrae.org/
- RESNET: https://www.resnet.us/
- DOE Building America: https://www.energy.gov/eere/buildings/building-america
- BLDS Specification: https://permitdata.org/

## Implementation Priority
1. **MVP**: Manual data entry for top metros
2. **Post-MVP Phase 1**: ClimateZones.us integration
3. **Post-MVP Phase 2**: ICC Code Connect
4. **Post-MVP Phase 3**: Full jurisdiction coverage