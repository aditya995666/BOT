import streamlit as st
import tempfile
import os
import sys
import pandas as pd
from datetime import datetime
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from memory.memory_manager import MemoryManager
from utils.nlp_utils import extract_docx_text
from utils.ocr_utils import extract_text_from_pdf_ocr
from tools.screen_reader import read_screen

memory = MemoryManager()

st.set_page_config("Shiva.AI Memory Loader", layout="wide")
st.title("🤖 Shiva.AI Marketing OS — Memory Loader")
st.markdown("### Store Marketing Data → Auto-Generate Questions")

# Helper function to auto-generate question based on content
def auto_generate_question(content, content_type="text"):
    """Auto-generate question based on content type and context"""
    content_lower = content.lower()
    
    # Detect content type and generate question
    if "lead" in content_lower or "customer" in content_lower:
        return "Customer/Lead details kya hain?"
    
    elif "campaign" in content_lower or "marketing" in content_lower:
        return "Marketing campaign details kya hain?"
    
    elif "revenue" in content_lower or "sales" in content_lower:
        return "Revenue/Sales data kya hai?"
    
    elif "seo" in content_lower or "keyword" in content_lower:
        return "SEO keywords aur strategy kya hai?"
    
    elif "whatsapp" in content_lower or "message" in content_lower:
        return "WhatsApp message/bot flow kya hai?"
    
    elif "pipeline" in content_lower or "deal" in content_lower:
        return "CRM pipeline aur deal stages kya hain?"
    
    elif "score" in content_lower or "prediction" in content_lower:
        return "AI score/prediction kya hai?"
    
    elif "blog" in content_lower or "content" in content_lower:
        return "Blog/content generation kya hai?"
    
    elif "analytics" in content_lower or "metric" in content_lower:
        return "Analytics metrics kya hain?"
    
    else:
        # Default: first 50 chars as question
        preview = content[:50].strip()
        return f"Information about: {preview}..."

st.info(
    "🎯 **Smart Memory Store:** Har data automatically question ke saath store hoga.\n\n"
    "📌 **Auto Questions:** Lead details, Campaign data, Revenue info, SEO keywords, WhatsApp flows, etc.\n\n"
    "💡 **Manual override:** Agar specific question dena hai to neeche diye gaye field mein likho."
)

# MANUAL TEXT / ANSWER INSERT
st.subheader("📝 Manual Data Entry")

col1, col2 = st.columns([1, 2])

with col1:
    manual_question = st.text_area(
        "🎯 **Custom Question (Optional):**",
        height=100,
        placeholder="Jaise:\n- Customer lead details?\n- Campaign performance?\n- Revenue prediction?\n\n**Leave empty for auto-generate**"
    )

with col2:
    manual_answer = st.text_area(
        "📄 **Data / Knowledge Paste karein:**",
        height=200,
        placeholder="Yahan koi bhi marketing data paste karein...\n\nExamples:\n- Lead: John, 25, Mumbai, interested in AI tools\n- Campaign: WhatsApp campaign open rate 45%\n- Revenue: Q4 predicted revenue ₹50L"
    )

if st.button("💾 Store Data", type="primary"):
    if manual_answer.strip():
        # Auto-generate question if user didn't provide
        if manual_question.strip():
            question = manual_question.strip()
        else:
            question = auto_generate_question(manual_answer.strip())
        
        with st.spinner("Storing in memory..."):
            memory.store(
                question=question,
                answer=manual_answer.strip(),
                source_agent="user",
                content_type="marketing_data",
                confidence=0.9
            )
        
        st.success("✅ **Data Stored Successfully!**")
        st.info(f"📌 **Auto Question:** {question}")
    else:
        st.warning("⚠️ Kuch data likho bhai!")

# FILE UPLOAD (PDF / DOCX / TXT)
st.set_page_config("Dataset → Memory Loader", layout="wide")
st.title("Dataset Loader (Memory + RAG Ready)")

st.info(
    "Yahan jo bhi data add hoga, **sirf TEXT/ANSWER form me** database + vector DB me store hoga.\n\n"
    "PDF / Image / Voice raw data store nahi hota."
)
st.subheader(" Manual Text / Answer Insert")

manual_text = st.text_area(
    "Answer / Knowledge Text paste karein:",
    height=200,
    placeholder="Yahan koi bhi knowledge / answer / content paste karein..."
)
if st.button(" Store Text"):
    if manual_text.strip():
        memory.store(manual_text.strip())
        st.success(" Text database + vector DB me store ho gaya")
    else:
        st.warning(" Text empty hai")

st.divider()
st.subheader("📄 Upload Files (PDF / DOCX / TXT)")

uploaded_file = st.file_uploader(
    "Marketing reports, lead lists, campaign docs upload karo",
    "File upload karein",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    extracted_text = None
    
    with st.spinner("Extracting text from file..."):
        if uploaded_file.name.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            extracted_text = extract_text_from_pdf_ocr(tmp_path)
            os.remove(tmp_path)
            
        elif uploaded_file.name.endswith(".docx"):
            extracted_text = extract_docx_text(uploaded_file)
            
        elif uploaded_file.name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8")
    
    if extracted_text and len(extracted_text.strip()) > 50:
        st.text_area("📜 Extracted Text (Preview)", extracted_text[:3000], height=200)
        
        # Auto question based on filename and content
        auto_question = auto_generate_question(uploaded_file.name + " " + extracted_text[:200])
        
        col1, col2 = st.columns([1, 1])
        with col1:
            file_question = st.text_input(
                "🎯 **Question for this file (Optional):**",
                value=auto_question,
                placeholder="Auto-generated question above 👆",
                key="file_question"
            )
        
        with col2:
            content_type = st.selectbox(
                "📁 **Content Type:**",
                ["marketing_data", "lead_data", "campaign_data", "seo_data", "revenue_data", "analytics_data"],
                key="file_content_type"
            )
        
        if st.button("📥 Store File Data"):
            question = file_question.strip() if file_question.strip() else auto_question
            
            with st.spinner("Storing file content..."):
                memory.store(
                    question=question,
                    answer=extracted_text.strip(),
                    source_agent="file",
                    content_type=content_type,
                    confidence=0.85
                )
            
            st.success("✅ **File data stored successfully!**")
            st.info(f"📌 **Stored with question:** {question}")
    else:
        st.error("❌ Text extract nahi ho paaya ya bahut chhota hai")

# BULK CSV UPLOAD (Marketing/Lead Data)
st.divider()
st.subheader("📊 Bulk Upload — CSV (Leads, Campaigns, Revenue Data)")

csv_file = st.file_uploader(
    "CSV upload karein — Leads, Campaigns, Analytics Data",

    if uploaded_file.name.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        extracted_text = extract_text_from_pdf_ocr(tmp_path)
        os.remove(tmp_path)

    elif uploaded_file.name.endswith(".docx"):
        extracted_text = extract_docx_text(uploaded_file)

    elif uploaded_file.name.endswith(".txt"):
        extracted_text = uploaded_file.read().decode("utf-8")

    if extracted_text and len(extracted_text.strip()) > 50:
        st.text_area("📜 Extracted Text (Preview)", extracted_text[:3000], height=200)

        if st.button("📥 Store Extracted Text"):
            memory.store(extracted_text.strip())
            st.success("✅ Extracted TEXT database me store ho gaya")
    else:
        st.error("❌ Text extract nahi ho paaya ya bahut chhota hai")

st.divider()
st.subheader("🖼️ Image → Text (OCR)")

st.caption("Screen ya image se text read karke store karega")

if st.button("📸 Read Screen & Store Text"):
    try:
        screen_text = read_screen()
        if screen_text.strip():
            st.text_area("OCR Text", screen_text, height=200)
            memory.store(screen_text.strip())
            st.success("✅ Screen text database me store ho gaya")
        else:
            st.warning("⚠️ Koi readable text nahi mila")
    except Exception as e:
        st.error(f"OCR Error: {e}")

st.divider()
st.subheader("📊 CSV Upload (Row by Row Store)")

csv_file = st.file_uploader(
    "CSV upload karein",
    type=["csv"],
    key="csv_uploader"
)

if csv_file:
    df = pd.read_csv(csv_file)
    st.dataframe(df.head(10))
    
    # Detect column types automatically
    st.markdown("### 🧠 Column Mapping")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_column = st.selectbox(
            "📄 **Data Column** (jo store karna hai):",
            df.columns,
            help="Yeh column ka data memory me store hoga"
        )
    
    with col2:
        question_column = st.selectbox(
            "🎯 **Question Column** (agar hai to):",
            ["[Auto-generate]"] + list(df.columns),
            help="Agar CSV mein question column hai to select karo, nahi to auto-generate hoga"
        )
    
    with col3:
        content_type = st.selectbox(
            "📁 **Content Type:**",
            ["lead_data", "campaign_data", "revenue_data", "seo_data", "analytics_data", "marketing_data"]
        )
    
    if st.button("🚀 Bulk Store Data", type="primary"):
        count = 0
        progress_bar = st.progress(0)
        
        for idx, row in df.iterrows():
            if idx >= 100:  # Limit for performance
                st.warning("Max 100 rows processed at once")
                break
                
            data_value = str(row[data_column]) if pd.notna(row[data_column]) else ""
            
            if len(data_value.strip()) > 10:
                # Generate question
                if question_column != "[Auto-generate]" and pd.notna(row[question_column]):
                    question = str(row[question_column])
                else:
                    question = auto_generate_question(data_value)
                
                # Store in memory
                memory.store(
                    question=question,
                    answer=data_value.strip(),
                    source_agent="csv",
                    content_type=content_type,
                    confidence=0.8
                )
                count += 1
            
            progress_bar.progress((idx + 1) / min(len(df), 100))
        
        st.success(f"✅ **{count} rows successfully stored in memory!**")
        st.balloons()

# QUERY SECTION — Test your stored data
st.divider()
st.subheader("🔍 Query Memory — Ask about your stored data")

test_question = st.text_input(
    "Kuch pooch kar dekho stored data ke baare mein:",
    placeholder="Examples:\n- Leads ka data kya hai?\n- Campaign performance?\n- Revenue prediction?\n- SEO keywords kya hain?",
    key="test_query"
)

if st.button("Ask Memory", type="primary"):
    if test_question.strip():
        with st.spinner("Searching in memory..."):
            result = memory.query(test_question.strip())
            if result:
                st.success("📚 **Memory se jawab mila:**")
                st.info(result)
            else:
                st.warning("❌ Koi relevant memory nahi mili")
    else:
        st.warning("⚠️ Kuch question likho")

# MEMORY STATS & INSIGHTS
st.divider()
with st.expander("📊 Memory Stats & Insights", expanded=False):
    try:
        conn = memory.conn
        cursor = conn.cursor()
        
        # Total count
        total = cursor.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Memories", total)
        
        # Type wise count
        type_counts = cursor.execute("""
            SELECT content_type, COUNT(*) as cnt 
            FROM memory 
            WHERE content_type IS NOT NULL
            GROUP BY content_type
            ORDER BY cnt DESC
        """).fetchall()
        
        if type_counts:
            st.write("**📁 Content Type Distribution:**")
            for t in type_counts:
                st.write(f"- **{t['content_type']}**: {t['cnt']} items")
        
        # Recent 5 memories
        recent = cursor.execute("""
            SELECT content, created_at 
            FROM memory 
            ORDER BY created_at DESC 
            LIMIT 5
        """).fetchall()
        
        if recent:
            st.write("**🕒 Recently Stored:**")
            for r in recent:
                preview = r['content'][:100] + "..." if len(r['content']) > 100 else r['content']
                st.write(f"- {r['created_at'][:19]}: {preview}")
                
    except Exception as e:
        st.error(f"Stats error: {e}")

st.divider()
st.success("🎯 **Shiva.AI Memory is now live!** Har marketing data auto-question ke saath store ho raha hai.")
    import pandas as pd

    df = pd.read_csv(csv_file)
    st.dataframe(df.head())

    col = st.selectbox(
        "Kaunsa column store karna hai (TEXT / ANSWER):",
        df.columns
    )

    if st.button("Store CSV Column"):
        count = 0
        for val in df[col].dropna():
            if isinstance(val, str) and len(val.strip()) > 20:
                memory.store(val.strip())
                count += 1

        st.success(f"{count} rows database me store ho gayi")

st.divider()
st.success("🎯 Tumhara AI memory ab gradually strong ho raha hai (RAG powered)") 
