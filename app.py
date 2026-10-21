import os
from pathlib import Path
import streamlit as st
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import time

st.set_page_config(page_title="المستشار الإداري", layout="wide")
st.title("🧑‍💼 المستشار الإداري - دليل الطلبة")

BASE = Path(__file__).parent

# قراءة المفتاح
key = ""
for name in ["key.txt", "api_key.txt", "مفتاح.txt"]:
    p = BASE / name
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

# البحث عن ملف الوورد
docx_files = [f for f in BASE.glob("*.docx") if not f.name.startswith("~$")]
if not docx_files:
    st.error("❌ لم أجد أي ملف وورد في المجلد.")
    st.stop()
FILE = docx_files[0]

@st.cache_resource
def build():
    doc = docx.Document(str(FILE))
    text_list = []
    
    # قراءة الفقرات النصية
    for p in doc.paragraphs:
        if p.text.strip():
            text_list.append(p.text)
            
    # قراءة الجداول (هذا هو الحل السحري)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_list.append(cell.text)
                    
    text = "\n".join(text_list)
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=150)
    chunks = splitter.split_documents([Document(page_content=text, metadata={"source": FILE.name})])
    
    # استخدام التضمين المحلي
    emb = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
    return Chroma.from_documents(chunks, emb), len(chunks)

db, n = build()
st.caption(f"📄 {FILE.name} | 🧠 {n} مقطع جاهز")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def generate_answer(q):
    # 1. إعادة صياغة السؤال
    rewrite_prompt = (
        "أنت خبير في الشؤون الأكاديمية. أعد صياغة السؤال التالي ليكون سؤالاً رسمياً دقيقاً للبحث في الوثائق الرسمية.\n"
        "صحح الأخطاء الإملائية وافهم المعنى.\n"
        f"السؤال: {q}"
    )
    try:
        rw_llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
        formal_q = rw_llm.invoke(rewrite_prompt).content
        if isinstance(formal_q, list): formal_q = formal_q[0].get('text', str(formal_q))
    except:
        formal_q = q

    # 2. البحث
    results = db.similarity_search("query: " + formal_q, k=8)
    context = "\n\n---\n\n".join([d.page_content for d in results])

    # 3. الإجابة
    prompt = (
        "أنت مستشار إداري ذكي. أجب على سؤال المستخدم بالعربية بناءً على النص المرفق.\n"
        "إذا لم يوجد النص، اعتذر بلباقة.\n\n"
        f"النص:\n{context}\n\nسؤال المستخدم: {q}"
    )
    
    # النماذج التي استجابت معنا في المقدمة
    MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]
    for model_name in MODELS:
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_retries=1)
            response = llm.invoke(prompt)
            if isinstance(response.content, list) and len(response.content) > 0:
                return response.content[0].get('text', str(response.content))
            return response.content
        except Exception:
            continue # ننتقل للنموذج التالي فوراً بدون انتظار
            
    return "عذراً، النماذج مشغولة حالياً."

# واجهة الدردشة
if q := st.chat_input("اكتب سؤالك هنا..."):
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("⏳ يبحث في الملف ويجيب..."):
            ans = generate_answer(q)
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
