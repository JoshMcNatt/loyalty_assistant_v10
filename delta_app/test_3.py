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

# First, modify the create_bonus_json function to accept bonus_category and bonus_type:
# Update the create_bonus_json function to accept bonus_description
def create_bonus_json(start_date, end_date, bonus_code, bonus_category, bonus_type, bonus_description=None):
    """Create a JSON structure for the bonus configuration"""
    description = bonus_description if bonus_description else f"{bonus_code} - {start_date.strftime('%B')} {start_date.year}"
    
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
        "roundingRule": "Always Up"
    }]

def show_download_section(where_clause, export_key, idx):
    """Helper function to show download and bonus sections"""
    with st.container():
        # Initialize states if not present
        if f"show_buttons_{idx}" not in st.session_state:
            st.session_state[f"show_buttons_{idx}"] = True
        
        # Always show both buttons if state is True
        if st.session_state[f"show_buttons_{idx}"]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Export Audience Data", key=f"export_button_{idx}"):
                    # Only generate data when export button is clicked
                    full_audience_df = generate_full_audience(where_clause)
                    st.session_state[export_key] = full_audience_df.to_csv(index=False)
                    st.session_state[f"show_download_{idx}"] = True
            
            # Show download button only after export is generated
            if st.session_state.get(f"show_download_{idx}", False):
                st.download_button(
                    label="📥 Download Audience Data",
                    data=st.session_state[export_key],
                    file_name="full_audience_data.csv",
                    mime="text/csv",
                    key=f"download_button_{idx}"
                )
            
            with col2:
                if st.button("🎯 Configure Bonus", key=f"bonus_button_{idx}"):
                    st.session_state[f"show_bonus_form_{idx}"] = True
        
        # Bonus form in its own container
        if st.session_state.get(f"show_bonus_form_{idx}", False):
            with st.form(key=f'bonus_form_{idx}'):
                st.subheader("Configure Bonus Template")
                
                # Bonus Code at the top
                st.markdown("##### Bonus Code *(must be unique)*")
                st.markdown("*Example: 2XMILESDEMO*")  # Changed from generate_bonus_code()
                bonus_code = st.text_input(
                    "Enter Bonus Code",
                    value="",  # Leave input blank
                    key=f"bonus_code_input_{idx}"
                )
                
                # Description field
                bonus_description = st.text_area(
                    "Bonus Description",
                    placeholder="Enter a description for this bonus...",
                    key=f"bonus_description_{idx}"
                )
                
                # Bonus Category and Type
                col1, col2 = st.columns(2)
                with col1:
                    bonus_category = st.selectbox(
                        "Bonus Category",
                        options=["Base", "Bonus", "Other"],
                        key=f"bonus_category_{idx}"
                    )
                with col2:
                    bonus_type = st.selectbox(
                        "Bonus Type",
                        options=["Enroll", "Goodwill", "NTE", "Transaction", "TXNBONUS"],
                        key=f"bonus_type_{idx}"
                    )
                
                # Start and End Dates
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "Start Date",
                        min_value=date.today(),
                        key=f"start_date_{idx}"
                    )
                with col2:
                    end_date = st.date_input(
                        "End Date",
                        min_value=start_date,
                        key=f"end_date_{idx}"
                    )
                
                if st.form_submit_button("Create Bonus Template"):
                    # Create bonus data with new parameters
                    bonus_data = create_bonus_json(
                        start_date, 
                        end_date, 
                        bonus_code,
                        bonus_category,
                        bonus_type,
                        bonus_description
                    )
                    
                    # Initialize webhook and send request
                    webhook = WorkfrontWebhook()
                    success, status = webhook.send_request(bonus_data)
                    
                    if success:
                        st.success("✅ Bonus Template Created!")
                        st.info(status)
                    else:
                        st.error(f"❌ {status}")
                    
                    st.session_state[f"show_bonus_form_{idx}"] = False
        
        # Show success message and download button outside the form
        if st.session_state.get(f"show_success_{idx}", False):
            st.success("✅ Bonus Template Created and Sent to Workfront!")
            st.json(st.session_state[f"bonus_data_{idx}"])
            st.info(f"Workfront Response Status: {st.session_state[f'response_{idx}'].status_code}")
            
            # Show download button for JSON template
            st.download_button(
                label="📥 Download Bonus Template",
                data=json.dumps(st.session_state[f"bonus_data_{idx}"], indent=2),
                file_name=f"bonus_template_{st.session_state[f'bonus_code_{idx}']}.json",
                mime="application/json",
                key=f"download_bonus_{idx}"
            )

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

            # Extract WHERE clause
            message["results"] = conn.query(sql)
            st.dataframe(message["results"])

            # Extract WHERE clause
            where_clause_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", sql, re.DOTALL)
            where_clause = where_clause_match.group(0) if where_clause_match else ""

            export_key = "export_final"
            show_download_section(where_clause, export_key, "final")

        st.session_state.messages.append(message)