"""
Page Scoring Algorithms for Floor Plan Detection
Advanced scoring logic to identify architectural floor plans vs other document types
"""

import re
import math
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class GeometricFeatures:
    """Geometric features extracted from a page"""
    line_count: int
    horizontal_lines: int
    vertical_lines: int
    rectangles: int
    circles: int
    complex_paths: int
    line_length_variance: float
    aspect_ratio: float
    drawing_density: float


@dataclass
class TextFeatures:
    """Text features extracted from a page"""
    total_words: int
    room_labels: int
    dimension_annotations: int
    technical_terms: int
    title_block_indicators: int
    scale_indicators: int
    architectural_abbreviations: int
    text_to_drawing_ratio: float


@dataclass
class PageScoring:
    """Complete scoring analysis for a page"""
    geometric_score: float
    text_score: float
    layout_score: float
    confidence_score: float
    total_score: float
    floor_plan_probability: float
    features: Dict[str, Any]
    reasoning: List[str]


class FloorPlanScorer:
    """
    Advanced scoring system for identifying floor plan pages
    """
    
    # Room type keywords with weights
    ROOM_KEYWORDS = {
        'bedroom': 3, 'living': 3, 'kitchen': 3, 'bathroom': 3, 'dining': 2,
        'master': 2, 'family': 2, 'office': 2, 'utility': 2, 'laundry': 2,
        'guest': 1, 'closet': 1, 'hall': 1, 'foyer': 1, 'pantry': 1,
        'garage': 1, 'basement': 1, 'attic': 1, 'den': 1, 'study': 1,
        'br': 2, 'ba': 2, 'kit': 2, 'lr': 2, 'dr': 2, 'mb': 2  # Abbreviations
    }
    
    # Technical/architectural terms
    ARCHITECTURAL_TERMS = {
        'scale', 'elevation', 'section', 'detail', 'plan', 'floor',
        'north', 'dimensions', 'sq ft', 'sqft', 'square', 'feet',
        'architect', 'drawing', 'sheet', 'project'
    }
    
    # Title block indicators (suggest this is a technical drawing)
    TITLE_BLOCK_TERMS = {
        'drawn by', 'checked by', 'approved', 'date', 'revision',
        'project', 'client', 'drawing number', 'sheet', 'scale'
    }
    
    # Scale indicators
    SCALE_PATTERNS = [
        r'1/4"\s*=\s*1\'',  # 1/4" = 1'
        r'1"\s*=\s*\d+\'',  # 1" = 8'
        r'scale:\s*1:\d+',  # Scale: 1:48
        r'\d+\'\s*=\s*\d+"', # 8' = 1"
    ]
    
    # Dimension patterns with confidence weights
    DIMENSION_PATTERNS = [
        (r"(\d+)'\s*-?\s*(\d+)\"", 1.0),     # 12'-6" (high confidence)
        (r"(\d+)'\s*(\d+)\"", 0.9),          # 12'6"
        (r"(\d+)'(?!\w)", 0.8),              # 12' (avoid matching words)
        (r"(\d+\.?\d*)\s*x\s*(\d+\.?\d*)", 0.7), # 12.5 x 15.0
        (r"(\d+)\s*x\s*(\d+)", 0.6),         # 12 x 15
    ]
    
    def score_page(self, doc: fitz.Document, page_num: int) -> PageScoring:
        """
        Comprehensive scoring of a page for floor plan likelihood
        
        Args:
            doc: PyMuPDF document
            page_num: Zero-based page number
            
        Returns:
            PageScoring with detailed analysis
        """
        page = doc[page_num]
        reasoning = []
        
        try:
            # Extract features
            geometric_features = self._extract_geometric_features(page)
            text_features = self._extract_text_features(page, geometric_features)
            
            # Calculate component scores
            geometric_score = self._score_geometric_features(geometric_features, reasoning)
            text_score = self._score_text_features(text_features, reasoning)
            layout_score = self._score_layout_features(geometric_features, text_features, reasoning)
            
            # Calculate confidence based on feature consistency
            confidence_score = self._calculate_confidence(
                geometric_features, text_features, geometric_score, text_score, reasoning
            )
            
            # Weighted total score
            total_score = (
                geometric_score * 0.4 +  # Geometry is most important
                text_score * 0.3 +       # Text content matters
                layout_score * 0.2 +     # Layout structure
                confidence_score * 0.1   # Confidence adjustment
            )
            
            # Convert to probability (0-1)
            floor_plan_probability = self._score_to_probability(total_score)
            
            return PageScoring(
                geometric_score=round(geometric_score, 2),
                text_score=round(text_score, 2),
                layout_score=round(layout_score, 2),
                confidence_score=round(confidence_score, 2),
                total_score=round(total_score, 2),
                floor_plan_probability=round(floor_plan_probability, 3),
                features={
                    'geometric': geometric_features.__dict__,
                    'text': text_features.__dict__
                },
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error scoring page {page_num + 1}: {str(e)}")
            return PageScoring(
                geometric_score=0.0,
                text_score=0.0,
                layout_score=0.0,
                confidence_score=0.0,
                total_score=0.0,
                floor_plan_probability=0.0,
                features={},
                reasoning=[f"Scoring failed: {str(e)}"]
            )
    
    def _extract_geometric_features(self, page: fitz.Page) -> GeometricFeatures:
        """Extract geometric features from page"""
        drawings = page.get_drawings()
        rect = page.rect
        page_area = rect.width * rect.height
        
        line_count = 0
        horizontal_lines = 0
        vertical_lines = 0
        rectangles = 0
        circles = 0
        complex_paths = 0
        line_lengths = []
        
        for drawing in drawings:
            if 'items' in drawing:
                for item in drawing['items']:
                    item_type = item[0]
                    
                    if item_type == 'l':  # Line
                        line_count += 1
                        # Extract line coordinates
                        if len(item) >= 3:
                            start, end = item[1], item[2]
                            length = math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)
                            line_lengths.append(length)
                            
                            # Classify line orientation
                            angle = math.atan2(end.y - start.y, end.x - start.x)
                            angle_deg = abs(math.degrees(angle))
                            
                            if angle_deg < 10 or angle_deg > 170:
                                horizontal_lines += 1
                            elif 80 < angle_deg < 100:
                                vertical_lines += 1
                    
                    elif item_type == 're':  # Rectangle
                        rectangles += 1
                    
                    elif item_type == 'c':  # Curve/Circle
                        circles += 1
                    
                    else:
                        complex_paths += 1
        
        # Calculate variance in line lengths
        line_length_variance = 0.0
        if line_lengths:
            mean_length = sum(line_lengths) / len(line_lengths)
            variance = sum((l - mean_length)**2 for l in line_lengths) / len(line_lengths)
            line_length_variance = math.sqrt(variance)
        
        # Page aspect ratio
        aspect_ratio = rect.width / rect.height if rect.height > 0 else 1.0
        
        # Drawing density (elements per unit area)
        drawing_density = len(drawings) / page_area if page_area > 0 else 0.0
        
        return GeometricFeatures(
            line_count=line_count,
            horizontal_lines=horizontal_lines,
            vertical_lines=vertical_lines,
            rectangles=rectangles,
            circles=circles,
            complex_paths=complex_paths,
            line_length_variance=line_length_variance,
            aspect_ratio=aspect_ratio,
            drawing_density=drawing_density
        )
    
    def _extract_text_features(self, page: fitz.Page, geo_features: GeometricFeatures) -> TextFeatures:
        """Extract text features from page"""
        text_content = page.get_text().lower()
        words = text_content.split()
        
        # Count room labels with weighted scoring
        room_labels = 0
        for word in words:
            for room_keyword, weight in self.ROOM_KEYWORDS.items():
                if room_keyword in word:
                    room_labels += weight
                    break
        
        # Count dimension annotations
        dimension_annotations = 0
        for pattern, confidence in self.DIMENSION_PATTERNS:
            matches = len(re.findall(pattern, text_content))
            dimension_annotations += matches * confidence
        
        # Count technical/architectural terms
        technical_terms = sum(1 for word in words if word in self.ARCHITECTURAL_TERMS)
        
        # Count title block indicators
        title_block_indicators = sum(1 for term in self.TITLE_BLOCK_TERMS if term in text_content)
        
        # Count scale indicators
        scale_indicators = sum(len(re.findall(pattern, text_content)) for pattern in self.SCALE_PATTERNS)
        
        # Count architectural abbreviations
        architectural_abbreviations = sum(1 for word in words if word in ['br', 'ba', 'kit', 'lr', 'dr', 'mb', 'w/d', 'wic'])
        
        # Text to drawing ratio
        text_to_drawing_ratio = len(words) / max(geo_features.line_count + geo_features.rectangles, 1)
        
        return TextFeatures(
            total_words=len(words),
            room_labels=int(room_labels),
            dimension_annotations=int(dimension_annotations),
            technical_terms=technical_terms,
            title_block_indicators=title_block_indicators,
            scale_indicators=scale_indicators,
            architectural_abbreviations=architectural_abbreviations,
            text_to_drawing_ratio=text_to_drawing_ratio
        )
    
    def _score_geometric_features(self, features: GeometricFeatures, reasoning: List[str]) -> float:
        """Score geometric features for floor plan likelihood"""
        score = 0.0
        
        # Line count scoring (floor plans have moderate to high line counts)
        if 100 <= features.line_count <= 2000:
            score += 25
            reasoning.append(f"Good line count ({features.line_count}) suggests architectural drawing")
        elif 50 <= features.line_count < 100:
            score += 15
            reasoning.append(f"Moderate line count ({features.line_count})")
        elif features.line_count > 2000:
            score += 5
            reasoning.append(f"High line count ({features.line_count}) may be too complex")
        
        # Rectangle count (potential rooms)
        if features.rectangles > 0:
            rectangle_score = min(features.rectangles * 3, 30)
            score += rectangle_score
            reasoning.append(f"Found {features.rectangles} rectangles (potential rooms): +{rectangle_score}")
        
        # Line orientation balance (floor plans have both horizontal and vertical lines)
        total_orthogonal = features.horizontal_lines + features.vertical_lines
        if total_orthogonal > 0:
            balance_ratio = min(features.horizontal_lines, features.vertical_lines) / total_orthogonal
            if balance_ratio > 0.3:  # Good balance
                score += 20
                reasoning.append("Good balance of horizontal/vertical lines suggests floor plan")
            elif balance_ratio > 0.1:
                score += 10
                reasoning.append("Some balance of horizontal/vertical lines")
        
        # Aspect ratio (floor plans typically have reasonable aspect ratios)
        if 0.5 <= features.aspect_ratio <= 2.0:
            score += 10
            reasoning.append("Page aspect ratio suitable for floor plan")
        
        # Drawing density (not too sparse, not too dense)
        if 0.0001 <= features.drawing_density <= 0.01:
            score += 15
            reasoning.append("Good drawing density for floor plan")
        
        return min(score, 100)  # Cap at 100
    
    def _score_text_features(self, features: TextFeatures, reasoning: List[str]) -> float:
        """Score text features for floor plan likelihood"""
        score = 0.0
        
        # Room labels (strong indicator)
        if features.room_labels > 0:
            room_score = min(features.room_labels * 4, 40)
            score += room_score
            reasoning.append(f"Found room labels: +{room_score}")
        
        # Dimension annotations (strong indicator)
        if features.dimension_annotations > 0:
            dim_score = min(features.dimension_annotations * 5, 30)
            score += dim_score
            reasoning.append(f"Found dimension annotations: +{dim_score}")
        
        # Technical terms (moderate indicator)
        if features.technical_terms > 0:
            tech_score = min(features.technical_terms * 2, 15)
            score += tech_score
            reasoning.append(f"Found architectural terms: +{tech_score}")
        
        # Scale indicators (good indicator)
        if features.scale_indicators > 0:
            scale_score = min(features.scale_indicators * 8, 20)
            score += scale_score
            reasoning.append(f"Found scale indicators: +{scale_score}")
        
        # Architectural abbreviations
        if features.architectural_abbreviations > 0:
            abbrev_score = min(features.architectural_abbreviations * 3, 15)
            score += abbrev_score
            reasoning.append(f"Found architectural abbreviations: +{abbrev_score}")
        
        # Title block (suggests technical drawing but not necessarily floor plan)
        if features.title_block_indicators > 0:
            score += 5
            reasoning.append("Found title block elements")
        
        # Text to drawing ratio (floor plans should have moderate text)
        if 0.1 <= features.text_to_drawing_ratio <= 2.0:
            score += 10
            reasoning.append("Good text-to-drawing ratio for floor plan")
        elif features.text_to_drawing_ratio > 5.0:
            score -= 10
            reasoning.append("Too much text relative to drawings")
        
        return min(score, 100)  # Cap at 100
    
    def _score_layout_features(self, geo_features: GeometricFeatures, 
                             text_features: TextFeatures, reasoning: List[str]) -> float:
        """Score overall page layout characteristics"""
        score = 0.0
        
        # Feature combination bonuses
        if geo_features.rectangles > 0 and text_features.room_labels > 0:
            score += 20
            reasoning.append("Strong combination: rectangles + room labels")
        
        if text_features.dimension_annotations > 0 and geo_features.line_count > 50:
            score += 15
            reasoning.append("Good combination: dimensions + geometric detail")
        
        if text_features.scale_indicators > 0 and geo_features.line_count > 100:
            score += 10
            reasoning.append("Technical drawing with scale information")
        
        # Complexity penalties
        if geo_features.line_count > 5000:
            score -= 15
            reasoning.append("Overly complex geometry may not be floor plan")
        
        if text_features.text_to_drawing_ratio > 10:
            score -= 20
            reasoning.append("Too text-heavy for typical floor plan")
        
        return max(min(score, 100), -50)  # Cap between -50 and 100
    
    def _calculate_confidence(self, geo_features: GeometricFeatures, 
                            text_features: TextFeatures, geo_score: float, 
                            text_score: float, reasoning: List[str]) -> float:
        """Calculate confidence in the scoring"""
        confidence = 50.0  # Base confidence
        
        # High confidence indicators
        if text_features.room_labels > 2 and geo_features.rectangles > 2:
            confidence += 20
            reasoning.append("High confidence: multiple rooms and rectangles")
        
        if text_features.dimension_annotations > 3:
            confidence += 15
            reasoning.append("High confidence: multiple dimensions found")
        
        if text_features.scale_indicators > 0:
            confidence += 10
            reasoning.append("Scale information increases confidence")
        
        # Low confidence indicators
        if geo_score < 20 and text_score < 20:
            confidence -= 25
            reasoning.append("Low confidence: weak geometric and text indicators")
        
        if geo_features.line_count < 20:
            confidence -= 15
            reasoning.append("Low confidence: very few geometric elements")
        
        return max(min(confidence, 100), 0)  # Keep between 0-100
    
    def _score_to_probability(self, total_score: float) -> float:
        """Convert total score to probability using sigmoid function"""
        # Sigmoid function to convert score to probability
        # Adjusted to give reasonable probabilities for floor plan detection
        normalized_score = (total_score - 50) / 30  # Center around 50, scale by 30
        probability = 1 / (1 + math.exp(-normalized_score))
        return probability


def score_page_for_floor_plan(pdf_path: str, page_num: int) -> PageScoring:
    """
    Convenience function to score a single page
    
    Args:
        pdf_path: Path to PDF file
        page_num: Zero-based page number
        
    Returns:
        PageScoring results
    """
    scorer = FloorPlanScorer()
    
    try:
        doc = fitz.open(pdf_path)
        try:
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num + 1} does not exist (PDF has {len(doc)} pages)")
            
            return scorer.score_page(doc, page_num)
        finally:
            doc.close()
    except Exception as e:
        logger.error(f"Error scoring page {page_num + 1}: {str(e)}")
        return PageScoring(
            geometric_score=0.0,
            text_score=0.0,
            layout_score=0.0,
            confidence_score=0.0,
            total_score=0.0,
            floor_plan_probability=0.0,
            features={},
            reasoning=[f"Scoring failed: {str(e)}"]
        )