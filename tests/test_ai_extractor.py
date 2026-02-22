import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from core.ai_extractor import AIExtractor
from core.config import MASTER_PROMPT, TABLES_ONLY_PROMPT

class TestAIExtractor(unittest.TestCase):

    def setUp(self):
        # Create a dummy PDF file to test byte reading
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dummy_doc_path = os.path.join(self.temp_dir.name, "dummy.pdf")
        with open(self.dummy_doc_path, "wb") as f:
            f.write(b"%PDF-1.4 dummy content")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_api_key(self):
        """Proves the system rejects initialization if no API key is provided."""
        with patch.dict(os.environ, clear=True):
            with self.assertRaises(ValueError):
                AIExtractor(api_key=None)

    def test_json_cleaner_markdown_removal(self):
        """Proves our regex successfully removes Markdown ticks and conversational text."""
        extractor = AIExtractor(api_key="FAKE_KEY")
        dirty_json = "Here is your data:\n```json\n{\"document\": {\"title\": \"test\"}}\n```\nHave a good day!"
        clean_json = extractor._clean_json_response(dirty_json)
        self.assertEqual(clean_json, "{\"document\": {\"title\": \"test\"}}")

    @patch('core.ai_extractor.genai.Client')
    def test_successful_api_extraction(self, mock_client_class):
        """Proves standard document extraction works with the Master Prompt."""
        # Set up the Fake API Response
        mock_response = MagicMock()
        mock_response.text = '{"recommended_filename": "Test_Doc", "document": {"tables": []}}'
        
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_response

        extractor = AIExtractor(api_key="FAKE_KEY")
        result = extractor.process_document(self.dummy_doc_path, mime_type="application/pdf")
        
        self.assertIn("document", result)
        self.assertEqual(result["recommended_filename"], "Test_Doc")

    @patch('core.ai_extractor.genai.Client')
    def test_auto_healer(self, mock_client_class):
        """Proves the engine automatically wraps flattened JSON inside a 'document' key."""
        mock_response = MagicMock()
        # AI hallucinates and forgets the "document" root key
        mock_response.text = '{"recommended_filename": "Broken_JSON", "tables": [{"table_id": 1}]}'
        
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_response

        extractor = AIExtractor(api_key="FAKE_KEY")
        result = extractor.process_document(self.dummy_doc_path, mime_type="application/pdf")
        
        # The auto-healer should have fixed it
        self.assertIn("document", result)
        self.assertIn("tables", result["document"])
        self.assertEqual(result["document"]["tables"][0]["table_id"], 1)

    @patch('core.ai_extractor.genai.Client')
    def test_tables_only_prompt_injection(self, mock_client_class):
        """Proves the system injects the Tables-Only prompt when the flag is True."""
        mock_response = MagicMock()
        mock_response.text = '{"document": {}}'
        
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_response

        extractor = AIExtractor(api_key="FAKE_KEY")
        extractor.process_document(self.dummy_doc_path, mime_type="application/pdf", extract_tables_only=True)
        
        # Verify that the API was called with the TABLES_ONLY_PROMPT
        call_args = mock_client_instance.models.generate_content.call_args[1]
        sent_prompt = call_args['contents'][0]
        self.assertIn(TABLES_ONLY_PROMPT, sent_prompt)

if __name__ == "__main__":
    unittest.main(verbosity=2)