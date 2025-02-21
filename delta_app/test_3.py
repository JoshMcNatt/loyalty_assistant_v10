import openai
import re
import streamlit as st
import pandas as pd
import uuid
from delta_prompt import get_system_prompt
import datetime
import random
import string
import json
from datetime import datetime, timezone, date
from wf_webhook import WorkfrontWebhook

st.sidebar.image('delta_app/images/Kobie_Alchemy_Loyalty_Cloud.png', use_column_width=True)

st.sidebar.header("Specifications")
st.sidebar.markdown(
"""
Model: OpenAI's GPT-4, leveraged for Natural Language Proessing.

Vertical: Travel & Hospitality  

*No data is shared with any model*
""")

class StateManager:
    """Centralized state management"""
    @staticmethod
    def init_state():
        if "state_initialized" not in st.session_state:
            st.session_state.state_initialized = True
            st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
            st.session_state.csv_data = {}
            st.session_state.button_states = {}
            st.session_state.form_states = {}

# At the very top of the script, after imports
def init_session_state():
    """Initialize all required session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
    if "csv_data" not in st.session_state:
        st.session_state.csv_data = {}

# Call this at the very start
init_session_state()

# Function to run a different select statement to pull all rows
@st.cache_data(ttl=3600)  # Cache for 1 hour
def generate_full_audience(where_clause=None):
    """Generate full audience with caching"""
    conn = st.experimental_connection("snowpark")
    query = f'SELECT "ACCOUNT ID" FROM KOBIE_BD.PUBLIC.DELTA_DEMO_AUDIENCE_DEMO_MRG {where_clause}'
    df = conn.query(query)
    return df

# Add this function near your other helper functions
def is_audience_summary(content):
    """Check if the message contains an audience summary"""
    return "Audience Summary:" in content and "```sql" in content

# First, modify the create_bonus_json function to accept bonus_category and bonus_type:
# Update the create_bonus_json function to accept bonus_description
def create_bonus_json(start_date, end_date, bonus_code, bonus_category, bonus_type, where_clause, bonus_description=None):
    """Create a JSON structure for the bonus configuration"""
    description = bonus_description if bonus_description else f"{bonus_code} - {start_date.strftime('%B')} {start_date.year}"
    
    # Get audience data
    audience_df = generate_full_audience(where_clause)
    
    return [{
        # Using consistent field names
        "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "bonusCode": bonus_code,
        "bonusType": bonus_type,
        "bonusCategory": bonus_category,
        "description": description,
        "programCode": "SKYMILES",
        "calcType": "Fixed Amount",
        "rewardAmount": 2,
        "roundingRule": "Always Up",
        "documents": {
            "audience": audience_df.to_dict(orient='records'),
            "where_clause": where_clause,
            "created_at": datetime.now().isoformat(),
            "total_accounts": len(audience_df)
        }
    }]

# Update the show_download_section function
def show_download_section(where_clause, export_key, idx):
    """Helper function to show download and bonus sections"""
    # Initialize states if not present
    if f"show_bonus_form_{idx}" not in st.session_state:
        st.session_state[f"show_bonus_form_{idx}"] = False
    if f"audience_data_{idx}" not in st.session_state:
        st.session_state[f"audience_data_{idx}"] = generate_full_audience(where_clause)
        
    with st.container():
        col1, buff, col2 = st.columns([2, 0.3, 2])
        
        # First column: Download button - use cached data
        with col1:
            st.download_button(
                label="📥 Download Audience Export",
                data=st.session_state[f"audience_data_{idx}"].to_csv(index=False),
                file_name="audience_data.csv",
                mime="text/csv",
                key=f"download_button_{idx}",
                use_container_width=True
            )
        
        # Second column: Configure Bonus button
        with col2:
            if st.button(
                "🎯 Configure Bonus Template", 
                key=f"bonus_button_{idx}",
                use_container_width=True,
                on_click=lambda: setattr(st.session_state, f"show_bonus_form_{idx}", not st.session_state[f"show_bonus_form_{idx}"])
            ):
                pass
        
        # Show form below if button was clicked
        if st.session_state[f"show_bonus_form_{idx}"]:
            with st.form(key=f'bonus_form_{idx}', clear_on_submit=True):
                st.markdown("**Bonus Code** _(Must be unique)_")
                st.markdown("_Example: 2XMILESDEMO_")
                bonus_code = st.text_input("Bonus Code")
                
                st.markdown("_Enter bonus description here_")
                bonus_description = st.text_area("Bonus Description")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=date.today())
                with col2:
                    end_date = st.date_input("End Date", value=date.today())
                
                bonus_category = st.selectbox(
                    "Bonus Category",
                    ["Base", "Bonus", "Other"]
                )
                
                bonus_type = st.selectbox(
                    "Bonus Type",
                    ["Enroll", "Goodwill", "NTE", "Transaction", "TXNBONUS"]
                )
                
                # Single submit button
                submit_basic = st.form_submit_button("Submit Bonus Template", use_container_width=True)
                
            # Handle form submission outside the form
            if submit_basic:
                with st.spinner("Creating bonus template..."):
                    audience_df = generate_full_audience(where_clause)
                    
                    bonus_data = create_bonus_json(
                        start_date, end_date, bonus_code,
                        bonus_category, bonus_type, where_clause,
                        bonus_description
                    )
                    
                    webhook = WorkfrontWebhook()
                    success, status = webhook.send_request(bonus_data)
                    
                    if success:
                        st.session_state[f"bonus_data_{idx}"] = bonus_data
                        st.session_state[f"workfront_status_{idx}"] = status
                        st.success("✅ Bonus Template Created!")
                        st.info(f"Workfront Response: {status}")

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# Modify the message display section
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        # If this is an audience summary response with results, handle export
        if "results" in message and is_audience_summary(message["content"]):
            st.dataframe(message["results"])
            sql_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", message["content"], re.DOTALL)
            where_clause = sql_match.group(0) if sql_match else ""
            export_key = f"export_{idx}"
            show_download_section(where_clause, export_key, idx)

# Generate a new assistant response if needed
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = ""
        resp_container = st.empty()
        for delta in openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True,
            temperature=0.5,
        ):
            response += delta.choices[0].delta.get("content", "")
            resp_container.markdown(response)

        message = {"role": "assistant", "content": response}

        # Extract SQL from response
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1)
            conn = st.experimental_connection("snowpark")
            message["results"] = conn.query(sql)
            
            st.dataframe(message["results"])
            where_clause_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", sql, re.DOTALL)
            where_clause = where_clause_match.group(0) if where_clause_match else ""
            export_key = "export_final"
            show_download_section(where_clause, export_key, "final")

        st.session_state.messages.append(message)
