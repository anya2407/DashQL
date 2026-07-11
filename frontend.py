import streamlit as st
from main import chatbot
from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessageChunk

if "current_charts" not in st.session_state:
    st.session_state.current_charts = []

import uuid
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = str(uuid.uuid4())
    
CONFIG = {
    "configurable": {
        "thread_id": st.session_state.thread_id
    }
}
  
if 'message_history' not in st.session_state:
    st.session_state['message_history']=[]

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])
         
user_input=st.chat_input('type here')

def extract_text(content):
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return content
 
if user_input:
    st.session_state.current_charts = []

    st.session_state['message_history'].append({'role':'user','content':user_input})
    with st.chat_message('user'):
        st.text(user_input)


    with st.chat_message('ai'):
        def ai_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, AIMessageChunk):
                    text = extract_text(message_chunk.content)
                    if text:
                        yield text

        ai_message = st.write_stream(ai_stream())
        st.write("Frontend charts:", len(st.session_state.current_charts))

        for fig in st.session_state.current_charts:
            st.plotly_chart(fig)

    st.session_state['message_history'].append({'role':'ai','content':ai_message})

        
