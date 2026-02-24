import os
import pytest
from unittest.mock import patch, MagicMock
from core.ai_extractor import AIExtractor
from core.config import MASTER_PROMPT, TABLES_ONLY_PROMPT

# 🚀 PYTEST FIXTURE: Automatically handles the dummy PDF for any test that needs it
@pytest.fixture
def dummy_pdf(tmp_path):
    doc_path = tmp_path / "dummy.pdf"
    doc_path.write_bytes(b"%PDF-1.4 dummy content")
    return str(doc_path)

# Test 1: Ensure strict API Key validation handles None, empty strings, and spaces
@pytest.mark.parametrize("invalid_key", [None, "", "   "])
def test_missing_api_key(invalid_key):
    """Proves the system rejects initialization if no valid API key is provided."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError):
            AIExtractor(api_key=invalid_key)

# Test 2: Bombard the regex cleaner with multiple types of AI formatting hallucinations
@pytest.mark.parametrize("dirty_json, expected_clean", [
    # Scenario A: Standard Markdown wrapper with conversational text
    ("Here is your data:\n```json\n{\"document\": {\"title\": \"test\"}}\n```\nHave a good day!", '{"document": {"title": "test"}}'),
    # Scenario B: Raw JSON with absolutely no markdown (AI followed instructions perfectly)
    ('{"document": {"title": "test"}}', '{"document": {"title": "test"}}'),
    # Scenario C: AI capitalized the word JSON in the markdown block
    ("```JSON\n{\"test\": 123}\n```", '{"test": 123}'),
    # Scenario D: Deeply nested json block with random trailing dots
    ("Some text... ```json\n{\"data\": \"here\"}\n``` ...end text.", '{"data": "here"}')
])
def test_json_cleaner_markdown_removal(dirty_json, expected_clean):
    """Proves our regex successfully removes various Markdown ticks and conversational text."""
    extractor = AIExtractor(api_key="FAKE_KEY")
    clean_json = extractor._clean_json_response(dirty_json)
    assert clean_json == expected_clean

# Test 3: Standard Success Path
@patch('core.ai_extractor.genai.Client')
def test_successful_api_extraction(mock_client_class, dummy_pdf):
    """Proves standard document extraction works with the Master Prompt."""
    mock_response = MagicMock()
    mock_response.text = '{"recommended_filename": "Test_Doc", "document": {"tables": []}}'
    
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance
    mock_client_instance.models.generate_content.return_value = mock_response

    extractor = AIExtractor(api_key="FAKE_KEY")
    result = extractor.process_document(dummy_pdf, mime_type="application/pdf")
    
    assert "document" in result
    assert result["recommended_filename"] == "Test_Doc"

# Test 4: The Auto-Healer (Testing different flattened structures)
@patch('core.ai_extractor.genai.Client')
@pytest.mark.parametrize("hallucinated_json, expected_key_to_wrap", [
    # Missing 'document' root, but has tables
    ('{"recommended_filename": "Broken_JSON", "tables": [{"table_id": 1}]}', "tables"),
    # Missing 'document' root, but has subtitles and footer
    ('{"subtitles": [{"text": "Hello"}], "footer": {"text": "end"}}', "subtitles")
])
def test_auto_healer(mock_client_class, dummy_pdf, hallucinated_json, expected_key_to_wrap):
    """Proves the engine automatically wraps flattened JSON inside a 'document' key."""
    mock_response = MagicMock()
    mock_response.text = hallucinated_json
    
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance
    mock_client_instance.models.generate_content.return_value = mock_response

    extractor = AIExtractor(api_key="FAKE_KEY")
    result = extractor.process_document(dummy_pdf, mime_type="application/pdf")
    
    # The auto-healer should have caught it and injected the "document" key
    assert "document" in result
    assert expected_key_to_wrap in result["document"]

# Test 5: Context Switcher
@patch('core.ai_extractor.genai.Client')
def test_tables_only_prompt_injection(mock_client_class, dummy_pdf):
    """Proves the system dynamically injects the Tables-Only prompt when the flag is True."""
    mock_response = MagicMock()
    mock_response.text = '{"document": {}}'
    
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance
    mock_client_instance.models.generate_content.return_value = mock_response

    extractor = AIExtractor(api_key="FAKE_KEY")
    extractor.process_document(dummy_pdf, mime_type="application/pdf", extract_tables_only=True)
    
    # Extract exactly what prompt was sent to the Gemini API
    call_args = mock_client_instance.models.generate_content.call_args[1]
    sent_prompt = call_args['contents'][0]
    
    # Verify the TABLES_ONLY_PROMPT is strictly in the payload
    assert TABLES_ONLY_PROMPT in sent_prompt
    assert MASTER_PROMPT not in sent_prompt