import json
from agent.core import UserInfo, Message, executor
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

user_info = UserInfo(user_id="cfo", preferences= {"currency":"USD"})
st.title("Finai Cfo Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
    
# Display chat history
for message in st.session_state.messages:   
    with st.chat_message(message.role):
        st.markdown(message.content)
        
query = st.chat_input("Question....")
if query:
    user_message = Message(role="user", content=query)
    st.session_state.messages.append(user_message)
    #financial_data_path = Path(__file__).parent.joinpath("fixtures","data.xlsx").as_posix()
    financial_data_path = os.getenv("FINANCIAL_DATASET_PATH")
    with st.chat_message("user"):
        st.markdown(query)
        
    # Generating Response 
    with st.chat_message("Finai Cfo Assistant"):
        response_text = executor(
            user_info = user_info,
            messages= st.session_state.messages,
            financial_data_path=financial_data_path
        )
        
        try:
            response_json = json.loads(response_text)
            st.markdown(response_json["response"])
            chart = response_json.get("chart")
            if chart:
                if chart["type"] == "line":
                    df_chart = pd.DataFrame({
                        "x": chart["x"],
                        "y": chart["y"]
                    })
                    fig = px.line(df_chart, x="x", y="y", title=chart["title"])
                    fig.update_yaxes(title_text=chart.get("ylabel", ""))
                    st.plotly_chart(fig)
                elif chart["type"] == "bar":
                    df_chart = pd.DataFrame(
                        {
                            "categories": chart["categories"],
                            "values": chart["values"]
                        }
                    )
                    fig = px.bar(df_chart, x="categories", y="values", title=chart["title"])
                    st.plotly_chart(fig)
        except json.JSONDecodeError:
            st.markdowm(response_text)
    assistant_message = Message(role= "Assistant", content=response_text)
    st.session_state.messages.append(assistant_message)