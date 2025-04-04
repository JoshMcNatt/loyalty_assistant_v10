# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 10:41:25 2023

@author: nate.jermain
"""

import openai
import re
import streamlit as st
from onpoint_prompt_v05 import get_system_prompt



##st.image('LAI.jpg')

st.sidebar.image('Kobie_Alchemy_Loyalty_Cloud.png', use_column_width=True)

st.sidebar.header("Specifications")
st.sidebar.markdown(
##    "This application uses OpenAI's GPT-4 to generate marketing campaign ideas and insights based on client-specific customer segmentations, ML-driven recommendations, and other attributes."
"""
Model: OpenAI's GPT-3.5  
Vertical: Retail  
""")


# api key
openai.api_key = st.secrets.OPENAI_API_KEY

if st.button("Let's Get Started!", type='primary'):
    st.session_state.mystarter=1


if "mystarter" in st.session_state:
    if "messages" not in st.session_state:
        # system prompt includes table information, rules, and prompts the LLM to produce
        # a welcome message to the user.
        st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
    
    # Prompt for user input and save
    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
    
    # display the existing chat messages
    for message in st.session_state.messages:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "results" in message:
                st.dataframe(message["results"])
    
    # If last message is not from assistant, we need to generate a new response
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
                temperature=.5
            ):
                response += delta.choices[0].delta.get("content", "")
                resp_container.markdown(response)
    
            message = {"role": "assistant", "content": response}
            # Parse the response for a SQL query and execute if available
            sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
            if sql_match:
                sql = sql_match.group(1)
                conn = st.experimental_connection("snowpark")
                message["results"] = conn.query(sql)
                st.dataframe(message["results"])
            st.session_state.messages.append(message)   
