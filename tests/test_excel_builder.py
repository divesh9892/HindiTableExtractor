import unittest
import os
import json
import tempfile
from core.excel_builder import ExcelBuilder

class TestExcelBuilder(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dummy_json_path = os.path.join(self.temp_dir.name, "input.json")
        self.dummy_excel_path = os.path.join(self.temp_dir.name, "output.xlsx")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_dummy_json(self, data):
        with open(self.dummy_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def test_standard_build(self):
        """Proves a perfectly formatted JSON builds an Excel file."""
        perfect_json = {
            "document": {
                "main_title": {"text": "Title", "is_bold": True, "font_size": 14},
                "tables": [{"headers": [{"column_name": "Col 1"}], "rows": [["Val 1"]]}],
                "footer": {"text": "Valid Footer", "is_bold": False, "font_size": 11}
            }
        }
        self.write_dummy_json(perfect_json)
        builder = ExcelBuilder(self.dummy_json_path, self.dummy_excel_path)
        builder.build()
        self.assertTrue(os.path.exists(self.dummy_excel_path))

    def test_defensive_footer_list(self):
        """Proves the builder doesn't crash if the AI returns the footer as a list."""
        broken_json = {
            "document": {
                "tables": [],
                "footer": ["Line 1 of footer", "Line 2 of footer"] # AI hallucinated a list!
            }
        }
        self.write_dummy_json(broken_json)
        builder = ExcelBuilder(self.dummy_json_path, self.dummy_excel_path)
        
        try:
            builder.build()
            self.assertTrue(os.path.exists(self.dummy_excel_path))
        except Exception as e:
            self.fail(f"ExcelBuilder crashed on a list footer! Error: {e}")

    def test_defensive_footer_string(self):
        """Proves the builder doesn't crash if the AI returns the footer as a raw string."""
        broken_json = {
            "document": {
                "tables": [],
                "footer": "Just a raw string footer" # AI hallucinated a string!
            }
        }
        self.write_dummy_json(broken_json)
        builder = ExcelBuilder(self.dummy_json_path, self.dummy_excel_path)
        
        try:
            builder.build()
            self.assertTrue(os.path.exists(self.dummy_excel_path))
        except Exception as e:
            self.fail(f"ExcelBuilder crashed on a string footer! Error: {e}")

if __name__ == "__main__":
    unittest.main(verbosity=2)