# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 10:41:25 2023

Author: nate.jermain
"""

import openai
import re
import streamlit as st
import pandas as pd
from delta_prompt import get_system_prompt

st.sidebar.image('delta_app/images/Kobie_Alchemy_Loyalty_Cloud.png', use_column_width=True)

st.sidebar.header("Specifications")
st.sidebar.markdown(
"""
Model: OpenAI's GPT-4   
Vertical: Travel & Hospitality  
""")

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Function to run a different select statement to pull all rows
def generate_full_audience(where_clause=None):
    conn = st.experimental_connection("snowpark")
    query = f'SELECT "ACCOUNT ID" FROM KOBIE_BD.PUBLIC.DELTA_DEMO_AUDIENCE_DEMO_MRG {where_clause}'
    df = conn.query(query)
    return df

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "results" in message:
            st.dataframe(message["results"])
            # Extract the WHERE clause from the SQL query
            sql_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", message["content"], re.DOTALL)
            where_clause = sql_match.group(0) if sql_match else ""
            # Add a download button for the full audience data
            if st.button("Export Full Audience Data"):
                # Generate and download the full audience data
                full_audience_df = generate_full_audience(where_clause)
                
                full_csv = full_audience_df.to_csv(index=False)
                st.download_button(
                    label="Download Full Audience Data",
                    data=full_csv,
                    file_name='full_audience_data.csv',
                    mime='text/csv'
                )

# If last message is not from assistant, we need to generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = ""
        resp_container = st.empty()
        for delta in openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
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
            # Extract the WHERE clause from the SQL query
            where_clause_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", sql, re.DOTALL)
            where_clause = where_clause_match.group(0) if where_clause_match else ""
            # Add a download button for the full audience data
            if st.button("Export Full Audience Data"):
                # Generate and download the full audience data
                full_audience_df = generate_full_audience(where_clause)
                full_csv = full_audience_df.to_csv(index=False)
                label="Download Full Audience Data",
                data=full_csv,
                file_name='full_audience_data.csv',
                mime='text/csv'
        st.session_state.messages.append(message)