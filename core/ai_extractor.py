import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv
from core.logger import log
from core.config import MASTER_PROMPT, SAMPLE_JSON

load_dotenv()

class AIExtractor:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            log.error("API Key missing.")
            raise ValueError("No API Key provided. Please enter a valid Gemini API Key.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'

    def _clean_json_response(self, raw_text):
        clean_text = raw_text.strip()
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', clean_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return clean_text

    # 🚀 NEW: Handles both PDFs and Images dynamically
    def process_document(self, file_path, mime_type):
        log.info(f"Initiating AI extraction for document: {file_path} ({mime_type})")
        try:
            # Read the file as raw bytes
            with open(file_path, "rb") as f:
                doc_bytes = f.read()
            
            # Package it for the Gemini API
            document_part = types.Part.from_bytes(data=doc_bytes, mime_type=mime_type)
            full_prompt = f"{MASTER_PROMPT}\n\nEXPECTED JSON SCHEMA:\n{SAMPLE_JSON}"
            
            log.info(f"Sending payload to {self.model_name} via new SDK...")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt, document_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            raw_output = response.text
            clean_json_string = self._clean_json_response(raw_output)
            parsed_data = json.loads(clean_json_string)
            
            if "document" not in parsed_data:
                log.warning("AI missed the 'document' wrapper. Auto-healing...")
                if "tables" in parsed_data:
                    filename = parsed_data.pop("recommended_filename", "AI_Extracted_Report")
                    parsed_data = {
                        "recommended_filename": filename,
                        "document": parsed_data 
                    }
                else:
                    raise ValueError(f"AI returned unreadable structure. Keys found: {list(parsed_data.keys())}")
                    
            log.info("Successfully extracted and parsed JSON from Gemini.")
            return parsed_data

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse Gemini output as JSON: {e}")
            raise ValueError("The AI returned invalid JSON format. Try again.")
        except Exception as e:
            log.error(f"Gemini API Error: {str(e)}")
            raise RuntimeError(f"API Communication Error: {str(e)}")