import pytest
from core.font_converter import unicode_to_krutidev

@pytest.mark.parametrize("original, expected_inclusion, expected_exclusion", [
    # 1. Punctuation Fallback Hack
    ("आई.डी.", ["\u2024"], ["."]),
    ("माता/संरक्षक", ["\u2215"], ["/"]),
    
    # 2. Bracket Translation
    ("(हाँ)", ["¼", "½"], ["(", ")"]),
    ("[नहीं]", ["¼", "½"], ["[", "]"]),
    
    # 3. English Quote Stripping & 'श्' Rendering
    # 🚀 FIX 4: The English quote is stripped, '३' becomes '3', 'अ' becomes 'v', and 'श्' translates cleanly to the '"' key!
    ('"३अश्"', ['3', 'v', '"'], ["'"]), 
    ("'सिंगल'", [], ["'"]),
    
    # 4. Complex Ligatures & Half-Characters
    ("ब्लॉक", ["C"], []),       
    ("ग्रामीण", ["z"], []),    
    ("द्वितीय", ["}"], []),      
    
    # 5. The Advanced Reph and Matra Jumps
    ("सम्बन्धित", ["f"], []),   
    ("लाभार्थियों", ["Z"], [])    
])
def test_font_converter_edge_cases(original, expected_inclusion, expected_exclusion):
    """Dynamically tests the toughest Devanagari edge cases."""
    result = unicode_to_krutidev(original)
    
    for inc in expected_inclusion:
        assert inc in result, f"Expected '{inc}' in '{result}'"
    for exc in expected_exclusion:
        assert exc not in result, f"Did not expect '{exc}' in '{result}'"

# 🚀 FIX 5: Deleted the obsolete test_preprocessing_spell_check function!

@pytest.mark.parametrize("empty_input", ["", None])
def test_empty_string_handling(empty_input):
    """Ensures the algorithm doesn't crash on empty table cells."""
    assert unicode_to_krutidev(empty_input) == ""