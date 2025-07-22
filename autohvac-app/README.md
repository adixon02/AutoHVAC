# AutoHVAC MVP

A smart HVAC design and load calculation tool that generates professional system recommendations in minutes.

## Features

- **Manual J Load Calculations**: ACCA-compliant heating and cooling load calculations
- **Climate Zone Integration**: Automatic climate data lookup by ZIP code
- **Room-by-Room Analysis**: Detailed load breakdown for each space
- **Tiered System Recommendations**: Economy, Standard, and Premium options
- **Professional Reports**: Downloadable calculation reports
- **Blue-Collar Friendly UI**: Clean, intuitive interface designed for contractors

## Getting Started

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Run Development Server**
   ```bash
   npm run dev
   ```

3. **Open Browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## How to Use

### Step 1: Project Setup
- Enter project name and ZIP code
- Select residential or commercial
- Choose new construction or retrofit

### Step 2: Building Details
- Input square footage and building characteristics
- Specify insulation quality and window types
- Set orientation and foundation details

### Step 3: Room Configuration
- Add rooms using quick templates or custom entries
- Define room areas, windows, and occupancy
- Specify exterior walls for accurate load calculations

### Step 4: Results
- View detailed load calculations (BTU/hr and tonnage)
- Compare system recommendations across price tiers
- Download professional report for permits/quotes

## Sample Climate Zones

The MVP includes climate data for major US metro areas:

- **Miami, FL** (33101) - Zone 1A (Hot-Humid)
- **Houston, TX** (77001) - Zone 2A (Hot-Humid)
- **Phoenix, AZ** (85001) - Zone 2B (Hot-Dry)
- **Las Vegas, NV** (89101) - Zone 3B (Hot-Dry)
- **Atlanta, GA** (30301) - Zone 3A (Mixed-Humid)
- **Nashville, TN** (37201) - Zone 4A (Mixed-Humid)
- **New York, NY** (10001) - Zone 4A (Cold)
- **Chicago, IL** (60601) - Zone 5A (Cold)
- **Denver, CO** (80201) - Zone 5B (Cold-Dry)
- **Seattle, WA** (98101) - Zone 4C (Marine)
- **San Francisco, CA** (94102) - Zone 3C (Marine)
- **Minneapolis, MN** (55401) - Zone 6A (Very Cold)

## Technical Stack

- **Frontend**: Next.js 15 with TypeScript
- **Styling**: Tailwind CSS with custom HVAC theme
- **Calculations**: Manual J implementation with ACCA standards
- **Data**: Local climate zone database for MVP

## Key Calculations

### Manual J Load Factors
- Wall/ceiling heat transfer based on R-values
- Window heat gain/loss using U-values
- Solar heat gain coefficients
- Internal gains (people + equipment)
- Infiltration based on building tightness
- Latent cooling loads for humidity

### System Sizing
- Cooling loads in BTU/hr and tons (12,000 BTU/hr = 1 ton)
- Heating loads in BTU/hr
- Equipment recommendations with safety factors
- Efficiency ratings (SEER/HSPF)

## Future Enhancements

This MVP provides the foundation for:
- Blueprint upload and AI analysis
- Advanced Manual D duct sizing
- Equipment manufacturer integrations
- Permit office API connections
- 3D visualization
- Cost estimation APIs

## Support

For questions or issues with this MVP demo, contact the development team.

## License

Proprietary - AutoHVAC MVP Demo