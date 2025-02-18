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
from datetime import datetime, timezone

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
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Initialize session state for CSV data if not present
if 'csv_data' not in st.session_state:
    st.session_state.csv_data = {}

# Function to run a different select statement to pull all rows
def generate_full_audience(where_clause=None):
    conn = st.experimental_connection("snowpark")
    query = f'SELECT "ACCOUNT ID" FROM KOBIE_BD.PUBLIC.DELTA_DEMO_AUDIENCE_DEMO_MRG {where_clause}'
    df = conn.query(query)  # Convert Snowpark DataFrame to Pandas DataFrame
    return df

# Function to handle the export and provide immediate download
def generate_and_download(where_clause, key):
    if key not in st.session_state.csv_data:
        full_audience_df = generate_full_audience(where_clause)
        st.session_state.csv_data[key] = full_audience_df.to_csv(index=False)
    return st.session_state.csv_data[key]

def handle_export_click(where_clause, key):
    """Callback function to handle export button click"""
    full_audience_df = generate_full_audience(where_clause)
    st.session_state[key] = full_audience_df.to_csv(index=False)
    st.session_state[f"show_download_{key}"] = True

def generate_bonus_code():
    """Generate a random 5-letter bonus code"""
    return ''.join(random.choices(string.ascii_uppercase, k=5))

# Add this function near your other helper functions
def is_audience_summary(content):
    """Check if the message contains an audience summary"""
    return "Audience Summary:" in content and "```sql" in content

def create_bonus_json(start_date, end_date, bonus_code):
    """Create a JSON structure for the bonus configuration"""
    bonus_data = [{
        "description": f"{bonus_code} - {start_date.strftime('%B')} {start_date.year}",
        "bonusType": "TXNBONUS",
        "programCode": "SKYMILES",
        "startDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
        "calcType": "VARSKU",
        "rewardAmount": 1,
        "roundingRule": "UP",
        "roundingScale": 0,
        "baseInd": False,
        "expireOnMergeInd": False,
        "canManuallyAward": False,
        "tqvInd": False,
        "trackingBonusInd": False,
        "endDate": end_date.strftime("%Y-%m-%dT23:59:59.999"),
        "maxAwardAccount": None,
        "maxCurrencyAccount": None,
        "maxCurrencyAccountTimeFrame": None,
        "maxAwardTxn": None,
        "maxCurrencyTxn": None,
        "dailyAccountsLow": 0,
        "dailyAccountsMax": None,
        "dailyAmountLow": 0,
        "dailyAmountMax": None,
        "totalAccountsMax": None,
        "totalAmountMax": None,
        "orgId": None,
        "flexCode": None,
        "eventType": None,
        "trackingCode": None,
        "offerCode": None,
        "cumulativeInd": False,
        "cumlEligUnitsThreshold": None,
        "cumlSpendThreshold": None,
        "cumlVisitThreshold": None,
        "spendThreshold": None,
        "bonusId": 2,
        "bonusCode": bonus_code,
        "rewardType": "FP",
        "releaseStatus": "D",
        "approvalUser": None,
        "status": "I",
        "bonusRules": [{
            "operatorCode": "!=",
            "exprValue": "0",
            "ruleKey": "TIELREV",
            "attributeCode": None,
            "trackingCode": None,
            "startDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
            "endDate": end_date.strftime("%Y-%m-%dT23:59:59.999"),
            "ruleId": 1,
            "releaseStatus": "D",
            "status": "I"
        }]
    }]
    return bonus_data

def show_download_section(where_clause, export_key, idx):
    """Helper function to show download and bonus sections"""
    # Container for all buttons and forms
    with st.container():
        # Generate data if not already in session state
        if export_key not in st.session_state:
            full_audience_df = generate_full_audience(where_clause)
            st.session_state[export_key] = full_audience_df.to_csv(index=False)
        
        # Button row
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Audience Data",
                data=st.session_state[export_key],
                file_name="full_audience_data.csv",
                mime="text/csv",
                key=f"download_button_{idx}"
            )
        
        with col2:
            if st.button("🎯 Create Bonus", key=f"bonus_button_{idx}"):
                st.session_state[f"show_bonus_form_{idx}"] = True
        
        # Bonus form in its own container
        if st.session_state.get(f"show_bonus_form_{idx}", False):
            with st.form(key=f'bonus_form_{idx}'):
                st.subheader("Create Bonus Configuration")
                col1, col2 = st.columns(2)
                
                with col1:
                    start_date = st.date_input(
                        "Start Date",
                        min_value=datetime.date.today(),
                        key=f"start_date_{idx}"
                    )
                
                with col2:
                    end_date = st.date_input(
                        "End Date",
                        min_value=start_date,
                        key=f"end_date_{idx}"
                    )
                
                bonus_code = st.text_input(
                    "Bonus Code",
                    value=generate_bonus_code(),
                    key=f"bonus_code_{idx}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Bonus Category", value="BONUS", disabled=True)
                with col2:
                    st.text_input("Bonus Type", value="TXNBONUS", disabled=True)
                
                submitted = st.form_submit_button("Create Bonus Configuration")
                if submitted:
                    bonus_data = create_bonus_json(start_date, end_date, bonus_code)
                    bonus_json = json.dumps(bonus_data, indent=2)
                    
                    st.success("✅ Bonus Configuration Created!")
                    st.download_button(
                        label="📥 Download Bonus Configuration",
                        data=bonus_json,
                        file_name=f"bonus_config_{bonus_code}.json",
                        mime="application/json",
                        key=f"download_bonus_{idx}"
                    )
                    st.session_state[f"show_bonus_form_{idx}"] = False

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# Initialize bonus form state
if 'show_bonus_form' not in st.session_state:
    st.session_state.show_bonus_form = False

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

            # Extract WHERE clause
            where_clause_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", sql, re.DOTALL)
            where_clause = where_clause_match.group(0) if where_clause_match else ""

            export_key = "export_final"
            show_download_section(where_clause, export_key, "final")

        st.session_state.messages.append(message)