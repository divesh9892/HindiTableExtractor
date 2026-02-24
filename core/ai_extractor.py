import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv
from core.logger import log
# 1. IMPORT THE NEW PROMPT
from core.config import MASTER_PROMPT, SAMPLE_JSON, TABLES_ONLY_PROMPT 

load_dotenv()

class AIExtractor:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key or not self.api_key.strip():
            log.error("API Key missing.")
            raise ValueError("No API Key provided. Please enter a valid Gemini API Key.")     
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'

    def _clean_json_response(self, raw_text):
        clean_text = raw_text.strip()
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', clean_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return clean_text

    # 2. ADD THE BOOLEAN FLAG HERE
    def process_document(self, file_path, mime_type, extract_tables_only=False):
        log.info(f"Initiating AI extraction for document: {file_path} ({mime_type})")
        try:
            with open(file_path, "rb") as f:
                doc_bytes = f.read()
            
            document_part = types.Part.from_bytes(data=doc_bytes, mime_type=mime_type)
            
            # 3. DYNAMIC PROMPT INJECTION
            active_prompt = TABLES_ONLY_PROMPT if extract_tables_only else MASTER_PROMPT
            full_prompt = f"{active_prompt}\n\nEXPECTED JSON SCHEMA:\n{SAMPLE_JSON}"
            
            log.info(f"Sending payload to {self.model_name}. Mode: {'Tables Only' if extract_tables_only else 'Full Document'}")
            
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
                # 🚀 FIX 3: Check for ANY valid root key, not just "tables"
                valid_root_keys = ["tables", "main_title", "subtitles", "footer"]
                if any(key in parsed_data for key in valid_root_keys):
                    filename = parsed_data.pop("recommended_filename", "AI_Extracted_Report")
                    parsed_data = {"recommended_filename": filename, "document": parsed_data}
                else:
                    raise ValueError(f"AI returned unreadable structure. Keys found: {list(parsed_data.keys())}")
                
            log.info("Successfully extracted and parsed JSON from Gemini.")       
            return parsed_data

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse Gemini output as JSON: {e}")
            raise ValueError("The AI returned invalid JSON format. Try again.")
        except Exception as e:
            log.error(f"Gemini API Error: {str(e)}")
            # 4. PASS THE EXACT ERROR MESSAGE UP TO THE UI
            raise RuntimeError(str(e))