# HVAC Floor Plan Layout Design Guidebook

## Purpose
This guidebook serves as training data and reference material for creating optimal HVAC floor plan layouts from building blueprints. It provides systematic approaches, best practices, and decision-making frameworks for both AI systems and human designers.

## 1. Blueprint Analysis Phase

### Room Identification & Classification
Properly identifying and classifying rooms is crucial for determining HVAC requirements:

- **Living Spaces** (High Priority): Living rooms, bedrooms, dens, home offices
  - Require precise temperature control
  - Prioritize quiet operation
  - Consider occupancy patterns

- **Wet Areas**: Kitchens, bathrooms, laundry rooms
  - Need exhaust ventilation
  - Higher latent heat loads
  - Moisture control critical

- **Utility Spaces**: Garages, basements, attics, mechanical rooms
  - Potential equipment locations
  - May not require conditioning
  - Consider as duct routing paths

- **Transition Areas**: Hallways, stairwells, foyers
  - Ideal for duct routing
  - Return air locations
  - Air circulation paths

### Critical Measurements to Extract
When analyzing blueprints, extract these key measurements:

1. **Room Dimensions**
   - Length × Width × Height
   - Calculate square footage and volume
   - Note irregular shapes or alcoves

2. **Window Data**
   - Location on each wall
   - Size (width × height)
   - Type (single/double pane)
   - Orientation (N/S/E/W)

3. **Door Locations**
   - Size and swing direction
   - Critical for airflow patterns
   - Affects register placement

4. **Structural Elements**
   - Wall thickness (insulation indicator)
   - Beam locations (duct routing obstacles)
   - Ceiling types (vaulted, tray, standard)

## 2. Load Calculation Rules

### Room-by-Room BTU Requirements

**Base Calculation**:
```
Base BTU = Square Footage × 25 (moderate climate)
Base BTU = Square Footage × 30 (hot climate)
Base BTU = Square Footage × 35 (cold climate)
```

**Adjustment Factors**:
- South-facing exposure: +10%
- East/West exposure: +5%
- North-facing: 0%
- Kitchen: +1,200 BTU (appliances)
- Each occupant: +400 BTU
- High window ratio (>15%): +15%
- Top floor location: +20%
- Corner room (2 exterior walls): +15%
- Basement: -10%
- High ceilings (>9 ft): +10% per foot

### Quick Tonnage Sizing
```
Total BTU/hr ÷ 12,000 = Tons
Add 10% safety factor
Round up to nearest 0.5 ton
```

**Example**:
- 32,000 BTU/hr ÷ 12,000 = 2.67 tons
- With 10% safety: 2.93 tons
- Select: 3.0 ton system

## 3. Equipment Placement Guidelines

### Outdoor Unit Placement Priority

**Ideal Locations** (in order of preference):
1. **North Side**: Coolest, best efficiency
2. **East Side**: Morning sun only
3. **West Side**: Avoid if possible (hot afternoon sun)
4. **South Side**: Last resort, requires shading

**Clearance Requirements**:
- 2 feet minimum from walls
- 3 feet between multiple units
- 5 feet from air intakes/exhausts
- 10 feet from bedroom windows (noise)
- 4 feet service access in front

**Surface Requirements**:
- Level concrete pad or brackets
- 3 inches above grade minimum
- Vibration isolation pads
- Proper drainage away from unit

### Indoor Equipment Placement

**Central Ducted Systems**:

*Best Locations*:
1. **Central Basement**: Ideal for even distribution
2. **Central Utility Room**: Good access, minimal duct runs
3. **Garage**: Easy service, noise isolation
4. **Attic**: Last choice (heat, access issues)

*Requirements*:
- 30" minimum front clearance
- 6" side clearances
- Combustion air access
- Condensate drain access
- 240V electrical (heat pumps)

**Ductless Mini-Split Indoor Units**:

*Wall-Mounted Units*:
- 6-8 feet high on wall
- Central to room area
- Away from direct sunlight
- 3 feet from ceiling
- Avoid corners (poor air distribution)

*Ceiling Cassettes*:
- Center of room ideal
- Minimum 8' ceiling height
- Access for filter cleaning
- Consider furniture layout

## 4. Ductwork Design Principles

### Main Trunk Line Design

**Sizing Guidelines**:
- Start with total CFM requirement
- Size for 900 FPM maximum velocity
- Reduce size after each branch takeoff
- Maintain aspect ratio under 3:1

**Routing Priorities**:
1. Central spine along hallway
2. Straight runs when possible
3. Gradual transitions (no abrupt size changes)
4. Avoid unconditioned spaces
5. Minimize length

### Branch Duct Rules

**Maximum Lengths**:
- 6" duct: 15 feet
- 7" duct: 20 feet
- 8" duct: 25 feet
- 10" duct: 35 feet

**Design Standards**:
- One register per branch
- Maximum two 90° bends
- Smooth radius elbows
- Proper takeoff angles (45° ideal)
- Seal all connections

### Register Placement Strategy

**Supply Registers**:

*Cooling Priority Climates*:
- High on interior walls
- Aim across room toward exterior wall
- Away from return paths

*Heating Priority Climates*:
- Under windows (counteract drafts)
- Low on exterior walls
- Perimeter distribution

*Universal Rules*:
- Not behind doors
- Away from thermostats
- Consider furniture placement
- Even room coverage

**Return Air Grilles**:
- Central location each floor
- Low for heating priority
- High for cooling priority
- Not in kitchens/baths
- Size for low velocity (400 FPM)

## 5. System Type Selection Matrix

### Residential Decision Tree

```
Home Size < 1,500 sq ft?
├── Yes → Open floor plan?
│   ├── Yes → Ductless Mini-Split
│   └── No → Many small rooms?
│       ├── Yes → Multi-Zone Mini-Split
│       └── No → Single-Zone Mini-Split
└── No → Existing ductwork?
    ├── Yes → Good condition?
    │   ├── Yes → Central Ducted System
    │   └── No → Hybrid (Ducted + Ductless)
    └── No → Multiple floors?
        ├── Yes → Zoned Central System
        └── No → Standard Central System
```

### Climate Considerations

**Hot, Humid Climates**:
- Prioritize dehumidification
- Oversizing is critical mistake
- Variable speed preferred
- Consider dedicated dehumidification

**Cold Climates**:
- Heat pump with backup heat
- Perimeter heating important
- Consider radiant supplements
- Proper defrost cycles

**Mild Climates**:
- Heat pumps ideal
- Ductless often sufficient
- Natural ventilation integration
- Energy recovery ventilation

## 6. Special Building Considerations

### Multi-Story Homes

**Zoning Requirements**:
- Separate zone per floor minimum
- Consider exposure zones
- Account for stack effect
- Balance dampers essential

**Duct Routing**:
- Vertical chases planned early
- Fire dampers where required
- Return air each level
- Consider sound transmission

### Additions and Renovations

**Integration Strategies**:
- Assess existing system capacity
- Consider separate mini-split
- Avoid overloading ducts
- Maintain proper static pressure

### Historic Preservation

**Sensitive Solutions**:
- High-velocity small duct systems
- Ductless for minimal intrusion
- Hide equipment from street view
- Preserve architectural features

## 7. Efficiency Optimization Strategies

### Zoning Best Practices

**Zone Grouping Logic**:
- Similar sun exposure
- Similar use patterns
- Maximum 1,500 sq ft per zone
- 3-4 rooms maximum per zone

**Control Strategy**:
- Programmable thermostats each zone
- Occupancy sensors considered
- Night setback capabilities
- Remote access options

### Duct System Efficiency

**Sealing Priority Areas**:
1. Supply/return plenums
2. Branch connections
3. Register boots
4. All joints and seams

**Insulation Requirements**:
- R-8 minimum in conditioned space
- R-12 in unconditioned space
- Vapor barrier facing out
- No compressed insulation

## 8. Visual Layout Standards

### Professional Drawing Conventions

**Equipment Symbols**:
```
Outdoor Unit: [===] with tonnage label
Indoor Unit: [:::] with BTU rating
Furnace: [FUR] with BTU input
Air Handler: [AH] with CFM rating
```

**Ductwork Representation**:
```
Supply Duct: ═══ (solid double line)
Return Duct: ┅┅┅ (dashed line)
Flex Duct: ≈≈≈ (wavy line)
```

**Annotations Required**:
- Equipment model and capacity
- Duct dimensions (W×H)
- CFM at each register
- Refrigerant line sizes
- Electrical requirements
- Condensate routing

### Color Coding Standards
- **Blue**: Cooling equipment/lines
- **Red**: Heating elements
- **Green**: Ventilation/fresh air
- **Gray**: Ductwork
- **Yellow**: Electrical connections

## 9. Cost Optimization Framework

### Installation Cost Drivers

**High Impact Factors**:
- Equipment location accessibility
- Duct run lengths
- Number of zones
- Electrical upgrades needed
- Structural modifications

**Cost Reduction Strategies**:
- Centralize equipment location
- Minimize custom transitions
- Standard equipment sizes
- Group multiple projects

### Lifecycle Cost Analysis

**Initial Cost vs. Operating Cost**:
- Higher SEER = Lower operating cost
- Proper sizing prevents cycling
- Zoning reduces waste
- Quality installation critical

## 10. Quality Control Checklist

### Design Review Points

**Comfort Requirements**:
- [ ] Every room has supply and return path
- [ ] BTU capacity meets calculated loads
- [ ] Air distribution promotes mixing
- [ ] Noise levels considered

**Technical Requirements**:
- [ ] Static pressure under 0.5" W.C.
- [ ] Duct velocities under limits
- [ ] Proper equipment clearances
- [ ] Code compliant installation
- [ ] Service accessibility maintained

**Efficiency Verification**:
- [ ] Minimal duct runs
- [ ] Proper insulation specified
- [ ] Sealed system design
- [ ] Right-sized equipment

## Training Data Format

### Example Structure
For each training example, document:

1. **Input Data**:
   - Blueprint image
   - Room types and dimensions
   - Climate zone
   - Special requirements

2. **Output Design**:
   - Complete HVAC layout
   - Equipment specifications
   - Duct routing plan
   - Control zones

3. **Decision Rationale**:
   - Why specific equipment chosen
   - Placement justification
   - Alternative options considered
   - Cost/benefit analysis

4. **Validation Metrics**:
   - Load calculation accuracy
   - Installation cost estimate
   - Operating cost projection
   - Comfort score prediction

## Conclusion

This guidebook provides the foundation for creating professional, efficient HVAC layouts from building blueprints. Following these guidelines ensures comfortable, energy-efficient systems that meet both immediate needs and long-term performance goals while optimizing installation and operating costs.