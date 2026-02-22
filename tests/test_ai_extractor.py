import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from core.ai_extractor import AIExtractor

class TestAIExtractor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dummy_image_path = os.path.join(self.temp_dir.name, "dummy.png")
        with open(self.dummy_image_path, "wb") as f:
            f.write(b"")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_api_key(self):
        """Proves the system rejects extraction if no API key is provided."""
        with patch.dict(os.environ, clear=True):
            with self.assertRaises(ValueError):
                AIExtractor(api_key=None)

    def test_json_cleaner_markdown_removal(self):
        """Proves our regex successfully removes Markdown ticks from LLM output."""
        extractor = AIExtractor(api_key="FAKE_KEY")
        
        dirty_json = "```json\n{\"document\": {\"title\": \"test\"}}\n```"
        clean_json = extractor._clean_json_response(dirty_json)
        
        self.assertEqual(clean_json, "{\"document\": {\"title\": \"test\"}}")

    @patch('core.ai_extractor.genai.Client')
    @patch('core.ai_extractor.Image.open')
    def test_successful_api_extraction(self, mock_image_open, mock_client_class):
        """Mocks the new Gemini GenAI Client to prove data is parsed correctly."""
        
        # Set up the Fake API Response
        mock_response = MagicMock()
        mock_response.text = '{"recommended_filename": "Test_Doc", "document": {}}'
        
        # Wire up the new mock client instance
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_response

        # Run the extractor with a fake key
        extractor = AIExtractor(api_key="FAKE_KEY")
        result = extractor.process_image(self.dummy_image_path)
        
        self.assertIn("recommended_filename", result)
        self.assertEqual(result["recommended_filename"], "Test_Doc")

if __name__ == "__main__":
    unittest.main(verbosity=2)