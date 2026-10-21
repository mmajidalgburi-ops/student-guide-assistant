import streamlit as st
import docx
import os
import google.generativeai as genai

st.set_page_config(page_title="المستشار الإداري", layout="wide")
st.title("🧑‍💼 المستشار الإداري - دليل الطلبة")

# إعداد مفتاح API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("❌ لم يتم العثور على المفتاح في إعدادات Secrets.")
    st.stop()

# قراءة الملف (الفقرات والجداول)
@st.cache_resource
def load_text():
    import glob
    files = glob.glob("*.docx")
    if not files: return ""
    doc = docx.Document(files[0])
    text_list = []
    for p in doc.paragraphs:
        if p.text.strip(): text_list.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip(): text_list.append(cell.text)
    return "\n".join(text_list)

document_text = load_text()
st.caption(f"📄 تم تحميل الملف بنجاح | عدد الأحرف: {len(document_text)}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("اكتب سؤالك هنا..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("⏳ يقرأ الدليل ويجيب..."):
            try:
                # تم تغيير اسم النموذج هنا إلى النموذج المتاح حالياً
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # تمرير النص كاملاً إلى Gemini
                context = document_text[:150000] 
                
                instruction = f"أنت مستشار إداري ذكي. أجب على سؤال المستخدم باللغة العربية بناءً على النص المرفق. إذا لم تجد الإجابة، قل (لا يوجد نص صريح).\n\nالنص:\n{context}\n\nسؤال المستخدم: {prompt}"
                
                response = model.generate_content(instruction)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
