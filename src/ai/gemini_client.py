#!/usr/bin/env python3
"""
Gemini AI Integration Module

Handles communication with Google's Gemini AI for generating insights.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from tenacity import retry, stop_after_attempt, wait_exponential
from jsonschema import validate, ValidationError

from ..utils.config import get_config
from ..storage import get_storage_adapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InsightRequest:
    """Request for generating insights."""
    insight_type: str  # "channel" or "video"
    data: Dict[str, Any]
    channel_id: str
    video_id: Optional[str] = None

@dataclass
class InsightResponse:
    """Response from insight generation."""
    success: bool
    insights: List[Dict[str, Any]]
    errors: List[str]
    tokens_used: int

class GeminiPromptTemplates:
    """Structured prompt templates for Gemini AI."""
    
    CHANNEL_INSIGHTS_SYSTEM = """
You are an expert YouTube analytics assistant. Your task is to analyze channel performance data and provide actionable insights.

You MUST respond with valid JSON only. Do not include any explanatory text before or after the JSON.

Analyze the provided channel data and return a JSON array of suggested actions. Each action must include:
- action_type: One of ["reindex_videos", "prioritize_promotion", "adjust_upload_schedule", "topic_suggestion", "audience_optimization", "content_strategy"]
- priority: One of ["high", "medium", "low"]
- confidence: A number between 0 and 1
- rationale: A brief explanation (1-2 sentences)
- recommended_videos: Array of video_ids if applicable (can be empty)
- details: Object with specific recommendations

Focus on actionable insights that can improve channel performance.
"""
    
    VIDEO_INSIGHTS_SYSTEM = """
You are an expert YouTube analytics assistant. Your task is to analyze individual video performance and provide optimization recommendations.

You MUST respond with valid JSON only. Do not include any explanatory text before or after the JSON.

Analyze the provided video data and return a JSON object with:
- action_type: One of ["recommend_reindex", "suggest_title_change", "suggest_description_optimization", "flag_low_retention", "recommend_promotion", "suggest_tags_update"]
- priority: One of ["high", "medium", "low"]
- confidence: A number between 0 and 1
- rationale: A brief explanation (1-2 sentences)
- details: Object with specific suggestions (e.g., suggested_title, suggested_tags, etc.)

Focus on specific, actionable recommendations for this video.
"""
    
    @staticmethod
    def format_channel_prompt(channel_data: Dict[str, Any]) -> str:
        """Format channel data for Gemini prompt."""
        return f"""
Channel Performance Summary:
{json.dumps(channel_data, indent=2, default=str)}

Task: Analyze this channel data and provide actionable insights to improve performance. Return JSON only.
"""
    
    @staticmethod
    def format_video_prompt(video_data: Dict[str, Any]) -> str:
        """Format video data for Gemini prompt."""
        return f"""
Video Performance Data:
{json.dumps(video_data, indent=2, default=str)}

Task: Analyze this video's performance and provide specific optimization recommendations. Return JSON only.
"""

class GeminiSchemas:
    """JSON schemas for validating Gemini responses."""
    
    CHANNEL_INSIGHTS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["reindex_videos", "prioritize_promotion", "adjust_upload_schedule", 
                            "topic_suggestion", "audience_optimization", "content_strategy"]
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "rationale": {
                    "type": "string",
                    "minLength": 10,
                    "maxLength": 500
                },
                "recommended_videos": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "details": {
                    "type": "object"
                }
            },
            "required": ["action_type", "priority", "confidence", "rationale", "details"]
        },
        "minItems": 1,
        "maxItems": 10
    }
    
    VIDEO_INSIGHTS_SCHEMA = {
        "type": "object",
        "properties": {
            "action_type": {
                "type": "string",
                "enum": ["recommend_reindex", "suggest_title_change", "suggest_description_optimization",
                        "flag_low_retention", "recommend_promotion", "suggest_tags_update"]
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"]
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "rationale": {
                "type": "string",
                "minLength": 10,
                "maxLength": 500
            },
            "details": {
                "type": "object"
            }
        },
        "required": ["action_type", "priority", "confidence", "rationale", "details"]
    }

class GeminiClient:
    """Client for interacting with Gemini AI."""
    
    def __init__(self):
        self.config = get_config()
        self._configure_gemini()
        self.tokens_used = 0
        
    def _configure_gemini(self):
        """Configure Gemini AI client."""
        genai.configure(api_key=self.config.gemini_api_key)
        
        # Configure safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            safety_settings=self.safety_settings
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _generate_content(self, prompt: str) -> str:
        """Generate content with retry logic."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            # Track token usage (approximate)
            self.tokens_used += len(prompt.split()) + len(response.text.split())
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise
    
    def _validate_response(self, response_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and parse Gemini response."""
        try:
            # Clean response text (remove markdown formatting if present)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            parsed_response = json.loads(cleaned_text)
            
            # Validate against schema
            validate(instance=parsed_response, schema=schema)
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        except ValidationError as e:
            raise ValueError(f"Response validation failed: {e.message}")
    
    def generate_channel_insights(self, channel_data: Dict[str, Any]) -> InsightResponse:
        """Generate channel-level insights."""
        errors = []
        insights = []
        
        try:
            # Format prompt
            system_prompt = GeminiPromptTemplates.CHANNEL_INSIGHTS_SYSTEM
            user_prompt = GeminiPromptTemplates.format_channel_prompt(channel_data)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response
            response_text = self._generate_content(full_prompt)
            
            # Validate and parse response
            parsed_insights = self._validate_response(
                response_text, 
                GeminiSchemas.CHANNEL_INSIGHTS_SCHEMA
            )
            
            insights = parsed_insights if isinstance(parsed_insights, list) else [parsed_insights]
            
            return InsightResponse(
                success=True,
                insights=insights,
                errors=errors,
                tokens_used=self.tokens_used
            )
            
        except Exception as e:
            error_msg = f"Error generating channel insights: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return InsightResponse(
                success=False,
                insights=[],
                errors=errors,
                tokens_used=self.tokens_used
            )
    
    def generate_video_insights(self, video_data: Dict[str, Any]) -> InsightResponse:
        """Generate video-level insights."""
        errors = []
        insights = []
        
        try:
            # Format prompt
            system_prompt = GeminiPromptTemplates.VIDEO_INSIGHTS_SYSTEM
            user_prompt = GeminiPromptTemplates.format_video_prompt(video_data)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response
            response_text = self._generate_content(full_prompt)
            
            # Validate and parse response
            parsed_insight = self._validate_response(
                response_text,
                GeminiSchemas.VIDEO_INSIGHTS_SCHEMA
            )
            
            insights = [parsed_insight]
            
            return InsightResponse(
                success=True,
                insights=insights,
                errors=errors,
                tokens_used=self.tokens_used
            )
            
        except Exception as e:
            error_msg = f"Error generating video insights: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return InsightResponse(
                success=False,
                insights=[],
                errors=errors,
                tokens_used=self.tokens_used
            )
    
    def save_insights_to_db(self, insights: List[Dict[str, Any]], channel_id: str, video_id: Optional[str] = None) -> int:
        """Save insights to database."""
        session = get_db_session()
        saved_count = 0
        
        try:
            for insight_data in insights:
                insight = Insight(
                    video_id=video_id,
                    channel_id=channel_id,
                    insight_type="video" if video_id else "channel",
                    action_type=insight_data["action_type"],
                    priority=insight_data["priority"],
                    confidence=insight_data["confidence"],
                    rationale=insight_data["rationale"],
                    payload_json={
                        "details": insight_data["details"],
                        "recommended_videos": insight_data.get("recommended_videos", []),
                        "generated_at": datetime.now().isoformat()
                    }
                )
                session.add(insight)
                saved_count += 1
            
            session.commit()
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving insights to database: {e}")
            raise
        finally:
            session.close()

class InsightGenerator:
    """High-level insight generation orchestrator."""
    
    def __init__(self):
        self.gemini_client = GeminiClient()
    
    def generate_insights_for_channel(self, channel_data: Dict[str, Any]) -> InsightResponse:
        """Generate and save channel insights."""
        response = self.gemini_client.generate_channel_insights(channel_data)
        
        if response.success and response.insights:
            try:
                saved_count = self.gemini_client.save_insights_to_db(
                    response.insights,
                    channel_data["channel_id"]
                )
                logger.info(f"Saved {saved_count} channel insights to database")
            except Exception as e:
                response.errors.append(f"Error saving insights: {e}")
                response.success = False
        
        return response
    
    def generate_insights_for_video(self, video_data: Dict[str, Any]) -> InsightResponse:
        """Generate and save video insights."""
        response = self.gemini_client.generate_video_insights(video_data)
        
        if response.success and response.insights:
            try:
                saved_count = self.gemini_client.save_insights_to_db(
                    response.insights,
                    video_data["channel_id"],
                    video_data["video_id"]
                )
                logger.info(f"Saved {saved_count} video insights to database")
            except Exception as e:
                response.errors.append(f"Error saving insights: {e}")
                response.success = False
        
        return response

# Global insight generator
_insight_generator: Optional[InsightGenerator] = None

def get_insight_generator() -> InsightGenerator:
    """Get the global insight generator instance."""
    global _insight_generator
    if _insight_generator is None:
        _insight_generator = InsightGenerator()
    return _insight_generator