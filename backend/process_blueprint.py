#!/usr/bin/env python3
"""
Process a blueprint PDF using the AI parser to extract room data
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.blueprint_ai_parser import BlueprintAIParser, BlueprintAIParsingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_blueprint(pdf_path: str, zip_code: str = "99206", demo_mode: bool = False):
    """Process a blueprint PDF and extract room data"""
    
    # Ensure OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY") and not demo_mode:
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.info("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        logger.info("Running in DEMO MODE with sample data...")
        demo_mode = True
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return None
    
    # Get filename
    filename = os.path.basename(pdf_path)
    
    try:
        logger.info(f"Processing blueprint: {pdf_path}")
        
        # Initialize parser
        parser = BlueprintAIParser()
        
        # Parse the PDF
        result = await parser.parse_pdf_with_gpt4v(
            pdf_path=pdf_path,
            filename=filename,
            zip_code=zip_code,
            project_id=None  # Will generate UUID
        )
        
        logger.info(f"Successfully parsed blueprint with {len(result.rooms)} rooms")
        
        # Convert to dict for JSON serialization
        result_dict = result.dict()
        
        # Save to JSON file
        output_path = pdf_path.replace('.pdf', '_parsed.json')
        with open(output_path, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        logger.info(f"Saved parsed data to: {output_path}")
        
        # Print summary
        print("\n=== BLUEPRINT PARSING RESULTS ===")
        print(f"PDF: {filename}")
        print(f"Total Area: {result.sqft_total} sq ft")
        print(f"Stories: {result.stories}")
        print(f"Rooms Found: {len(result.rooms)}")
        print("\n--- Room Details ---")
        
        for room in result.rooms:
            print(f"\n{room.name}:")
            print(f"  - Area: {room.area} sq ft")
            print(f"  - Dimensions: {room.dimensions_ft[0]} x {room.dimensions_ft[1]} ft")
            print(f"  - Floor: {room.floor}")
            print(f"  - Windows: {room.windows}")
            print(f"  - Orientation: {room.orientation}")
            print(f"  - Room Type: {room.room_type}")
            print(f"  - Confidence: {room.confidence}")
            
            # Print HVAC-specific data
            if room.source_elements:
                hvac_data = room.source_elements
                print(f"  - Exterior Doors: {hvac_data.get('exterior_doors', 0)}")
                print(f"  - Exterior Walls: {hvac_data.get('exterior_walls', 0)}")
                print(f"  - Corner Room: {hvac_data.get('corner_room', False)}")
                print(f"  - Ceiling Height: {hvac_data.get('ceiling_height', 'N/A')} ft")
                print(f"  - Thermal Exposure: {hvac_data.get('thermal_exposure', 'N/A')}")
                if hvac_data.get('notes'):
                    print(f"  - Notes: {hvac_data.get('notes')}")
        
        # Print parsing metadata
        if result.parsing_metadata:
            metadata = result.parsing_metadata
            print(f"\n--- Parsing Metadata ---")
            print(f"Processing Time: {metadata.processing_time_seconds:.2f} seconds")
            print(f"PDF Pages: {metadata.pdf_page_count}")
            print(f"Selected Page: {metadata.selected_page}")
            print(f"AI Status: {metadata.ai_status}")
            print(f"Overall Confidence: {metadata.overall_confidence}")
        
        return result_dict
        
    except BlueprintAIParsingError as e:
        logger.error(f"Blueprint parsing failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point"""
    # Default PDF path
    pdf_path = "/Users/austindixon/Documents/AutoHVAC/backend/tests/sample_blueprints/blueprint-example-99206.pdf"
    zip_code = "99206"
    
    # Check command line arguments
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    if len(sys.argv) > 2:
        zip_code = sys.argv[2]
    
    # Run async function
    result = asyncio.run(process_blueprint(pdf_path, zip_code))
    
    if result:
        print("\n✅ Blueprint processing completed successfully!")
    else:
        print("\n❌ Blueprint processing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()