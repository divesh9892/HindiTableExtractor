import streamlit as st
import json
import os
import tempfile
import traceback
import re
from core.logger import log
# 🚀 REMOVED MASTER_PROMPT import to protect your trade secret
from core.config import SAMPLE_JSON
from core.excel_builder import ExcelBuilder
from core.ai_extractor import AIExtractor

# --- UI Configuration ---
st.set_page_config(page_title="HindiScan AI", page_icon="📄", layout="wide")

st.title("📄 HindiScan AI")
st.markdown("Instantly convert Hindi PDFs, scanned documents, and mobile images into perfectly structured Excel spreadsheets. Zero manual data entry required.")

# Progressive Disclosure Export Settings
st.markdown("---")
st.subheader("⚙️ Export Settings")
use_legacy_font = st.toggle("🔤 Enable Legacy Government Fonts (Kruti Dev / DevLys)", value=False)

legacy_font_choice = "Kruti Dev 010" # Default value
if use_legacy_font:
    legacy_font_choice = st.radio(
        "Select Font Format:",
        options=["Kruti Dev 010", "DevLys 010"],
        horizontal=True
    )
    st.warning(f"⚠️ Note: You must have the '{legacy_font_choice}' font installed on your PC to read the final Excel file.")
st.markdown("---")

def sanitize_filename(name):
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    return clean_name.strip().replace(" ", "_")[:50]

# Deep Security & Size Validation
def validate_security_and_size(uploaded_file):
    """Checks the 5MB limit and verifies the file's raw Magic Bytes."""
    if uploaded_file.size > 5242880:
        raise ValueError("File exceeds the 5MB strict limit.")
    
    header = uploaded_file.read(4)
    uploaded_file.seek(0)
    
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
# TAB 1: MANUAL JSON TO EXCEL
# ==========================================
with tab1:
    st.subheader("Generate Excel from Structured JSON")
    
    # 🚀 NEW: Trade Secret Protected. Generic instructions added.
    with st.expander("📌 How to use this tool manually"):
        st.info("Go to an AI like ChatGPT or Gemini, upload your document, and ask it to extract the data using the exact JSON Schema shown below. Paste the resulting JSON here.")
    
    with st.expander("👀 View Expected JSON Structure"):
        st.code(SAMPLE_JSON, language="json")
    st.markdown("---")
    user_json_input = st.text_area(
        "Paste JSON Payload Here:", 
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
                
                # Check for either the old single-page format or new multi-page format
                if "document" not in parsed_json and "pages" not in parsed_json:
                    raise ValueError("Schema Error: Missing 'document' or 'pages' root key.")
                
                raw_filename = parsed_json.get("recommended_filename", "Structured_Hindi_Report")
                safe_filename = sanitize_filename(raw_filename) + ".xlsx"
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_json_path = os.path.join(temp_dir, "input.json")
                    temp_excel_path = os.path.join(temp_dir, safe_filename)
                    
                    with open(temp_json_path, 'w', encoding='utf-8') as f:
                        json.dump(parsed_json, f)
                        
                    with st.spinner(f"Building {safe_filename}..."):
                        builder = ExcelBuilder(
                            json_path=temp_json_path, 
                            output_path=temp_excel_path,
                            use_legacy_font=use_legacy_font,
                            legacy_font_name=legacy_font_choice
                        )
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
        use_custom_key = st.toggle("🔑 Use your own Gemini API Key (Bypass App Rate Limits)", value=False)
        
        custom_api_key = None
        if use_custom_key:
            custom_api_key = st.text_input("Enter your Gemini API Key:", type="password")
            st.info("🔒 **Zero-Trust Security:** Your API key is never stored. It exists purely in your browser's temporary memory.")

    st.markdown("---")
    extract_tables_only = st.checkbox("📊 **Extract Tables Only** (Ignore paragraphs, headers, and footers)", value=False)
    
    uploaded_file = st.file_uploader("Upload Document (JPG/PNG/PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

    st.caption("🔒 **Privacy & Security Notice:** This tool uses Google's Gemini AI to analyze the layout and text of your document. Your file is processed securely in temporary memory and is **instantly deleted** from our servers the moment your Excel file is generated. We do not store your documents.")

    st.info("ℹ️ **AI Confidence Notice:** This system uses advanced Vision AI to process complex layouts and handwriting. While highly accurate, poor image lighting or illegible handwriting may occasionally affect the output. Please perform a quick visual review of the generated Excel file.")
    
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
                    
                    with st.spinner("🤖 AI is analyzing the document... (This takes 30-60 seconds)"):
                        extractor = AIExtractor(api_key=custom_api_key)
                        progress_bar = st.progress(0, text="Preparing pages...")
                        def update_progress(current_page, total_pages):
                            progress_fraction = current_page / total_pages
                            progress_bar.progress(progress_fraction, text=f"Processing page {current_page + 1} of {total_pages}...")
                        extracted_json = extractor.process_document(temp_doc_path, detected_mime_type, extract_tables_only, progress_callback=update_progress)
                        # Clear the progress bar when complete
                        progress_bar.empty()
                    
                    with st.spinner("📊 Building Smart Excel File..."):
                        if "pages" not in extracted_json and "document" not in extracted_json:
                            raise ValueError("AI Output Error: Missing valid root keys.")
                        
                        raw_filename = extracted_json.get("recommended_filename", "AI_Extracted_Report")
                        safe_filename = sanitize_filename(raw_filename) + ".xlsx"
                        
                        temp_json_path = os.path.join(temp_dir, "ai_output.json")
                        temp_excel_path = os.path.join(temp_dir, safe_filename)
                        
                        with open(temp_json_path, 'w', encoding='utf-8') as f:
                            json.dump(extracted_json, f)
                            
                        builder = ExcelBuilder(
                            json_path=temp_json_path, 
                            output_path=temp_excel_path, 
                            use_legacy_font=use_legacy_font,
                            legacy_font_name=legacy_font_choice
                        )
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
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "Made with ❤️ by Divesh | Powered by Gemini VLM Architecture"
    "</div>", 
    unsafe_allow_html=True
)