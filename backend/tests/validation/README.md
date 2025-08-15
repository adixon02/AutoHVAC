# Component Validation Test Suite

This directory contains component-by-component validation tests for Manual J calculations.

## Purpose
Validate each calculation component against known Manual J examples to ensure mathematical accuracy independent of blueprint parsing.

## Test Structure
```
validation/
├── README.md
├── test_envelope_loads.py      # Wall, window, roof, foundation calculations
├── test_infiltration.py        # ACH50, AIM-2, infiltration loads
├── test_cooling_loads.py       # Solar gains, internal loads, CLTD
├── test_zone_factors.py        # Multi-story, bonus room, diversity factors
├── fixtures/
│   ├── manual_j_examples.py    # Known Manual J calculation examples
│   └── test_buildings.py       # Standard test building configurations
└── reports/                    # Validation reports and comparisons
```

## Validation Approach
1. **Reference Examples**: Use ACCA Manual J 8th Edition examples as ground truth
2. **Component Isolation**: Test each calculation independently
3. **Cross-Blueprint Validation**: Ensure calculations work across building types
4. **Regression Testing**: Track accuracy improvements over time

## Usage
```bash
# Run all validation tests
python -m pytest tests/validation/ -v

# Run specific component tests
python -m pytest tests/validation/test_envelope_loads.py -v

# Generate validation report
python tests/validation/generate_report.py
```