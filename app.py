import streamlit as st
import docx
import os
import google.generativeai as genai

st.set_page_config(page_title="المستشار الإداري", layout="wide")
st.title("🧑‍💼 المستشار الإداري - دليل الطلبة")

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("❌ لم يتم العثور على المفتاح في إعدادات Secrets.")
    st.stop()

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
                context = document_text[:150000] 
                instruction = f"أنت مستشار إداري ذكي. أجب على سؤال المستخدم باللغة العربية بناءً على النص المرفق. إذا لم تجد الإجابة، قل (لا يوجد نص صريح).\n\nالنص:\n{context}\n\nسؤال المستخدم: {prompt}"
                
                # قائمة النماذج التي سيجربها النظام واحداً تلو الآخر
                models_to_try = ['gemini-3.8-flash', 'gemini-3.6-flash', 'gemini-3.5-flash-lite', 'gemini-1.5-flash']
                response = None
                last_error = None
                
                for m in models_to_try:
                    try:
                        model = genai.GenerativeModel(m)
                        response = model.generate_content(instruction)
                        break 
                    except Exception as e:
                        last_error = e
                        continue 
                
                if response:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                else:
                    st.error(f"حدث خطأ في جميع النماذج: {last_error}")
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
