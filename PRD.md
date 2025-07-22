# AutoHVAC Product Requirements Document (PRD)

## Executive Summary

AutoHVAC is an AI-powered HVAC system design platform that revolutionizes how contractors, engineers, architects, and builders create heating, ventilation, and air conditioning layouts. By automating complex calculations and design processes, AutoHVAC reduces HVAC planning time from days to minutes while ensuring building code compliance and optimal system performance.

### Vision Statement
To become the industry standard for automated HVAC design and permitting, making professional-grade HVAC system planning accessible to both professionals and informed consumers.

### Key Value Proposition
- **10x faster** than traditional HVAC design methods
- **100% code-compliant** designs with automated Manual J/D/S calculations
- **Brand-agnostic** solutions optimized for performance, not sales
- **Instant permit-ready** documentation generation

## Product Overview

### Problem Statement
Current HVAC design processes are:
- Time-intensive (2-5 days per project)
- Error-prone due to manual calculations
- Inconsistent across contractors
- Often oversized, leading to inefficiency and increased costs
- Difficult to optimize for different budget tiers
- Challenging to keep compliant with changing local codes

### Solution
AutoHVAC provides an intelligent, automated platform that:
1. Analyzes building blueprints using AI/ML
2. Performs accurate load calculations per ACCA standards
3. Generates optimal equipment placement and routing
4. Produces permit-ready documentation
5. Offers tiered design options (economy, mid-tier, luxury)

## Target Users

### Primary Users

#### 1. HVAC Contractors & Engineers
- **Profile**: Licensed professionals designing systems for residential/commercial projects
- **Needs**: Fast, accurate designs; reduced callbacks; competitive bidding
- **Value**: Save 20+ hours per project; win more bids with professional documentation

#### 2. Homebuilders & Developers
- **Profile**: Companies building multiple homes/units annually
- **Needs**: Standardized HVAC designs; predictable costs; code compliance
- **Value**: Streamlined coordination; reduced change orders; faster project completion

#### 3. Architects
- **Profile**: Design professionals integrating mechanical systems
- **Needs**: Early-stage HVAC planning; space allocation; aesthetic integration
- **Value**: Better mechanical coordination; fewer design conflicts

### Secondary Users

#### 4. HVAC Product Representatives
- **Profile**: Sales reps for major HVAC brands
- **Needs**: Quick, accurate quotes; competitive system comparisons
- **Value**: Faster quote turnaround; increased close rates

#### 5. DIY Homeowners/Designers
- **Profile**: Informed consumers planning renovations or new construction
- **Needs**: Professional guidance; permit documentation; contractor validation
- **Value**: Confidence in system sizing; negotiation leverage with contractors

## Use Cases

### Primary Use Cases

1. **New Construction Design**
   - Upload architectural plans
   - Generate complete HVAC layout
   - Export permit-ready documents

2. **Retrofit/Renovation Planning**
   - Input existing structure details
   - Receive equipment upgrade recommendations
   - Compare ducted vs. ductless options

3. **Permit Documentation**
   - Generate Manual J load calculations
   - Create code-compliant drawings
   - Produce equipment schedules

4. **Multi-Option Bidding**
   - Generate economy/mid/luxury tiers
   - Compare different equipment brands
   - Provide detailed cost breakdowns

### Secondary Use Cases

5. **Energy Efficiency Analysis**
   - Compare system efficiencies
   - Calculate operating costs
   - Identify optimization opportunities

6. **Contractor Validation**
   - Verify proposed system sizing
   - Check code compliance
   - Validate equipment selection

## Feature Requirements

### Core Features (MVP)

#### 1. Project Setup
- **ZIP Code Integration**
  - Auto-populate climate data
  - Load local building codes
  - Apply energy requirements
  - Identify permit requirements

#### 2. Blueprint Analysis
- **File Upload**
  - Support PDF, PNG, JPG, DWG formats
  - Auto-detect room boundaries
  - Identify ceiling heights
  - Locate mechanical spaces
- **Manual Input Alternative**
  - Room-by-room square footage
  - Window/door specifications
  - Insulation values
  - Orientation data

#### 3. Load Calculation Engine
- **Manual J Compliance**
  - Room-by-room heat gain/loss
  - Whole-house load summary
  - Safety factor application
  - Documentation generation
- **Advanced Factors**
  - Occupancy patterns
  - Internal heat sources
  - Infiltration rates
  - Solar heat gain

#### 4. System Design Generation
- **Equipment Selection**
  - Right-sized capacity
  - Efficiency recommendations
  - Brand-agnostic options
  - Cost-tier alternatives
- **Layout Optimization**
  - Duct routing (forced air)
  - Mini-split placement (ductless)
  - Equipment location
  - Thermostat positioning

#### 5. Documentation Export
- **File Formats**
  - PDF (permit-ready)
  - DXF/DWG (CAD integration)
  - SVG (web viewing)
  - Excel (calculations)
- **Contents**
  - Equipment schedules
  - Load calculation reports
  - System diagrams
  - Compliance checklists

### Advanced Features (Post-MVP)

#### 6. Manual D Integration
- Duct sizing calculations
- Static pressure analysis
- Airflow optimization
- Noise reduction planning

#### 7. Manual S Module
- Detailed equipment matching
- Performance curve analysis
- Dehumidification capacity
- Multi-stage optimization

#### 8. 3D Visualization
- Interactive system view
- Clash detection
- Installation sequencing
- VR/AR support

#### 9. Cost Estimation
- Equipment pricing (API integration)
- Labor hour estimates
- Material takeoffs
- ROI calculations

#### 10. Collaboration Tools
- Multi-user projects
- Comment/markup system
- Version control
- Change tracking

## Technical Architecture

### Frontend
- **Framework**: React/Next.js for responsive web application
- **UI Components**: Material-UI or custom design system
- **Blueprint Viewer**: Canvas-based with WebGL for performance
- **State Management**: Redux or Zustand
- **File Handling**: Client-side processing for security

### Backend
- **API**: RESTful with GraphQL consideration for complex queries
- **Server**: Node.js with Express or Python with FastAPI
- **Authentication**: JWT-based with OAuth2 integration
- **File Storage**: AWS S3 or similar for blueprints
- **Database**: PostgreSQL for relational data, Redis for caching

### Core Processing
- **Blueprint Analysis**
  - OpenCV for image processing
  - TensorFlow/PyTorch for room detection
  - OCR for text extraction
- **Calculation Engine**
  - Python-based for complex mathematics
  - Parallel processing for performance
  - Validation against ACCA standards
- **Layout Generation**
  - Graph algorithms for routing
  - Constraint satisfaction for placement
  - Multi-objective optimization

### Integrations
- **Building Codes**: ICC, local jurisdiction APIs
- **Weather Data**: NOAA, Weather.gov APIs
- **Equipment Databases**: AHRI directory, manufacturer APIs
- **CAD Systems**: AutoCAD, Revit via IFC
- **Permit Systems**: Local government portals

## Non-Functional Requirements

### Performance
- Blueprint processing: < 30 seconds
- Load calculations: < 10 seconds
- System generation: < 20 seconds
- Export generation: < 5 seconds

### Security
- SOC 2 Type II compliance
- End-to-end encryption for blueprints
- GDPR/CCPA compliance
- Regular security audits

### Scalability
- Support 10,000+ concurrent users
- Process 100,000+ projects/month
- Multi-region deployment
- Auto-scaling infrastructure

### Reliability
- 99.9% uptime SLA
- Automated backups
- Disaster recovery plan
- Redundant calculation servers

## Success Metrics

### Business Metrics
- **User Acquisition**
  - 1,000 contractors in Year 1
  - 25% MoM growth rate
  - 60% user retention at 6 months
- **Revenue**
  - $2M ARR by end of Year 1
  - 80% gross margins
  - <$50 CAC

### Product Metrics
- **Usage**
  - 10+ projects per user/month
  - 90% calculation accuracy
  - <5% support ticket rate
- **Quality**
  - 100% code compliance rate
  - <1% design revision rate
  - 95% user satisfaction

### Technical Metrics
- **Performance**
  - <2s average response time
  - 99.9% API availability
  - <0.1% error rate
- **Efficiency**
  - 90% blueprint recognition accuracy
  - 80% first-time export success
  - 50% reduction in design time

## Competitive Analysis

### Direct Competitors
1. **Wrightsoft** - Desktop-based, complex UI, expensive
2. **Cool Calc** - Web-based, limited features, manual input
3. **ACCA Approved Software** - Various vendors, mostly desktop
4. **ConduitTech** - https://getconduit.com/

### Competitive Advantages
- First fully automated blueprint-to-design solution
- Brand-agnostic recommendations
- Instant multi-tier options
- Modern web-based interface
- Competitive pricing model

## Business Model

### Pricing Strategy
- **Freemium Tier**: 3 projects/month, basic features
- **Professional**: $149/month, unlimited projects, all features
- **Enterprise**: Custom pricing, API access, white-labeling

### Revenue Streams
1. SaaS subscriptions (primary)
2. API access for integrators
3. White-label partnerships
4. Training and certification

## Roadmap

### Phase 1: MVP (Months 1-6)
- Core calculation engine
- Basic blueprint upload
- Ducted system design
- PDF export

### Phase 2: Enhancement (Months 7-12)
- Ductless system support
- Advanced blueprint AI
- Multi-tier designs
- CAD export formats

### Phase 3: Scale (Year 2)
- Manual D/S modules
- 3D visualization
- API marketplace
- Mobile applications

### Phase 4: Platform (Year 3)
- Contractor marketplace
- Equipment ordering integration
- Permit submission APIs
- IoT system commissioning

## Risk Assessment

### Technical Risks
- **Blueprint parsing accuracy**: Mitigate with manual override options
- **Calculation complexity**: Extensive testing against known designs
- **Integration challenges**: Phased rollout with key partners

### Market Risks
- **Slow adoption**: Free tier and referral programs
- **Competitor response**: Rapid feature development
- **Regulatory changes**: Flexible code database

### Operational Risks
- **Support burden**: Comprehensive documentation and tutorials
- **Scaling challenges**: Cloud-native architecture
- **Data security**: Industry-standard protections

## Appendices

### A. Glossary
- **Manual J**: ACCA standard for residential load calculation
- **Manual D**: ACCA standard for residential duct design
- **Manual S**: ACCA standard for equipment selection
- **BTU**: British Thermal Unit, measure of heating/cooling capacity
- **SEER**: Seasonal Energy Efficiency Ratio

### B. Regulatory Compliance
- International Building Code (IBC)
- International Energy Conservation Code (IECC)
- Local jurisdiction amendments
- ACCA Quality Installation standards

### C. Technical Standards
- ASHRAE standards for HVAC design
- ACCA manuals J, D, S, T
- EPA regulations for refrigerants
- Energy Star requirements