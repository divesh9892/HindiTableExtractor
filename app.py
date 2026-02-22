import streamlit as st
import json
import os
import tempfile
import traceback
import re
from core.logger import log
from core.config import MASTER_PROMPT, SAMPLE_JSON
from core.excel_builder import ExcelBuilder
from core.ai_extractor import AIExtractor

# --- UI Configuration ---
st.set_page_config(page_title="Hindi Document Extractor", page_icon="📄", layout="wide")

st.title("📄 Enterprise Hindi Document Extractor")
st.markdown("Convert unstructured government WhatsApp images into perfectly formatted Excel reports.")

def sanitize_filename(name):
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    return clean_name.strip().replace(" ", "_")[:50]

# 🚀 NEW: Deep Security & Size Validation
def validate_security_and_size(uploaded_file):
    """Checks the 5MB limit and verifies the file's raw Magic Bytes."""
    # 1. Size Check (5MB = 5 * 1024 * 1024 bytes)
    if uploaded_file.size > 5242880:
        raise ValueError("File exceeds the 5MB strict limit.")
    
    # 2. Magic Bytes Check (Defeats fake file extensions)
    header = uploaded_file.read(4)
    uploaded_file.seek(0) # Reset the file pointer back to the start!
    
    is_pdf = header.startswith(b'%PDF')
    is_jpeg = header.startswith(b'\xff\xd8')
    is_png = header.startswith(b'\x89PNG')
    
    if is_pdf:
        return "application/pdf"
    elif is_jpeg:
        return "image/jpeg"
    elif is_png:
        return "image/png"
    else:
        raise ValueError("Security Alert: Invalid file signature. This is not a genuine Image or PDF.")

tab1, tab2 = st.tabs(["🧩 Option 1: Paste JSON (Manual)", "📸 Option 2: Upload File (API)"])

# ==========================================
# TAB 1: MANUAL JSON TO EXCEL (Unchanged)
# ==========================================
with tab1:
    st.subheader("Generate Excel from Structured JSON")
    with st.expander("📌 How to use this tool (Click to view Master Prompt)"):
        st.info(MASTER_PROMPT)
    with st.expander("👀 View Expected JSON Structure"):
        st.code(SAMPLE_JSON, language="json")
    st.markdown("---")
    user_json_input = st.text_area(
        "Paste Gemini JSON Payload Here:", 
        height=300, 
        max_chars=100000, 
        placeholder='{\n  "recommended_filename": "Report_Name",\n  "document": {\n    "main_title": ...\n  }\n}'
    )
    
    if st.button("🚀 Generate Excel Report", type="primary"):
        if not user_json_input.strip():
            st.warning("⚠️ Please paste a JSON payload before generating.")
        else:
            try:
                log.info("User initiated Option 1: Manual JSON Extraction")
                parsed_json = json.loads(user_json_input)
                
                if "document" not in parsed_json:
                    raise ValueError("Schema Error: Missing 'document' root key.")
                
                raw_filename = parsed_json.get("recommended_filename", "Structured_Hindi_Report")
                safe_filename = sanitize_filename(raw_filename) + ".xlsx"
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_json_path = os.path.join(temp_dir, "input.json")
                    temp_excel_path = os.path.join(temp_dir, safe_filename)
                    
                    with open(temp_json_path, 'w', encoding='utf-8') as f:
                        json.dump(parsed_json, f)
                        
                    with st.spinner(f"Building {safe_filename}..."):
                        builder = ExcelBuilder(json_path=temp_json_path, output_path=temp_excel_path)
                        builder.build()
                        
                        with open(temp_excel_path, "rb") as f:
                            excel_data = f.read()
                            
                    log.info(f"Successfully generated {safe_filename}")
                    st.success(f"✅ Report successfully generated as **{safe_filename}**!")
                    st.download_button(label="📥 Download Excel File", data=excel_data, file_name=safe_filename)
            
            except Exception as e:
                log.error(f"Failed to generate report: {str(e)}\n{traceback.format_exc()}")
                st.error(f"❌ Error: {str(e)}")
                with st.expander("🔍 View Technical Details"):
                    st.code(traceback.format_exc(), language="python")

# ==========================================
# TAB 2: VLM API INTEGRATION
# ==========================================
with tab2:
    st.subheader("Upload Document for Auto-Extraction")
    st.markdown("Upload a WhatsApp image or PDF (Max 5MB).")
    
    with st.container(border=True):
        use_custom_key = st.toggle("🔑 Use my own Gemini API Key (Bypass App Rate Limits)")
        custom_api_key = None
        if use_custom_key:
            custom_api_key = st.text_input("Enter your Gemini API Key:", type="password")
            st.info("🔒 **Zero-Trust Security:** Your API key is never stored. It exists purely in your browser's temporary memory.")

    # 🚀 NEW: The Tables-Only Toggle
    st.markdown("---")
    extract_tables_only = st.checkbox("📊 **Extract Tables Only** (Ignore paragraphs, headers, and footers)", value=False)
    
    uploaded_file = st.file_uploader("Upload Document (JPG/PNG/PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])
    
    if st.button("✨ Auto-Extract & Build Excel", type="primary", key="extract_btn"):
        if not uploaded_file:
            st.warning("⚠️ Please upload a document first.")
        elif use_custom_key and not custom_api_key:
            st.error("❌ You selected 'Use my own key' but didn't enter one.")
        else:
            try:
                detected_mime_type = validate_security_and_size(uploaded_file)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_doc_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_doc_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    with st.spinner("🤖 AI is analyzing the document... (This takes 5-15 seconds)"):
                        extractor = AIExtractor(api_key=custom_api_key)
                        # Pass the new toggle state to the extractor!
                        extracted_json = extractor.process_document(temp_doc_path, detected_mime_type, extract_tables_only)
                    
                    with st.spinner("📊 Building Smart Excel File..."):
                        if "document" not in extracted_json:
                            raise ValueError("AI Output Error: Missing 'document' root key.")
                        
                        raw_filename = extracted_json.get("recommended_filename", "AI_Extracted_Report")
                        safe_filename = sanitize_filename(raw_filename) + ".xlsx"
                        
                        temp_json_path = os.path.join(temp_dir, "ai_output.json")
                        temp_excel_path = os.path.join(temp_dir, safe_filename)
                        
                        with open(temp_json_path, 'w', encoding='utf-8') as f:
                            json.dump(extracted_json, f)
                            
                        builder = ExcelBuilder(json_path=temp_json_path, output_path=temp_excel_path)
                        builder.build()
                        
                        with open(temp_excel_path, "rb") as f:
                            excel_data = f.read()
                            
                    st.success(f"✅ Report successfully generated as **{safe_filename}**!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(label="📥 Download Excel File", data=excel_data, file_name=safe_filename)
                    with col2:
                        with st.expander("👀 View Raw AI JSON Data"):
                            st.json(extracted_json)

            except ValueError as ve:
                st.error(f"❌ {str(ve)}")
            except Exception as e:
                error_str = str(e)
                # 🚀 NEW: Smart Error Interception for Rate Limits
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    st.error("🛑 **API Rate Limit Exceeded**")
                    st.warning("""
                    **The server is currently processing too many requests. How to proceed:**
                    1. **Toggle 'Use my own Gemini API Key'** above to bypass the app's limits entirely.
                    2. **Use Option 1 (Paste JSON):** Generate the JSON directly in Google AI Studio and paste it in the first tab.
                    3. Wait 60 seconds and try clicking extract again.
                    """)
                else:
                    log.error(f"Option 2 Failed: {error_str}\n{traceback.format_exc()}")
                    st.error(f"❌ An unexpected error occurred: {error_str}")

# Footer
st.markdown("---")
st.caption("Powered by Smart VLM Decoupled Architecture")