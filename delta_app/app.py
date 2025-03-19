import openai
import re
import streamlit as st
import pandas as pd
import uuid
from prompt import get_system_prompt
import datetime
import random
import string
import json
from datetime import datetime, timezone, date
from wf_webhook import WorkfrontWebhook
import hashlib  # Added for more stable hashing

st.sidebar.image('delta_app/images/Kobie_Alchemy_Loyalty_Cloud.png', use_column_width=True)

st.sidebar.header("Specifications")
st.sidebar.markdown(
"""
Model: OpenAI's GPT-4, leveraged for Natural Language Proessing.

Vertical: Travel & Hospitality

*No data is shared with any model*
""")

def init_session_state():
    """Initialize all required session state variables"""
    if "state_initialized" not in st.session_state:
        st.session_state.state_initialized = True
        st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
        st.session_state.sections = {}  # Store section states here
        st.session_state.section_message_map = {}  # Map message indices to section IDs

# Call this at the very start
init_session_state()

# Function to create a stable section ID 
def create_stable_id(where_clause, export_key):
    """Create a stable ID from where_clause and export_key"""
    # Clean the where clause to make it more stable
    cleaned_clause = re.sub(r'\s+', ' ', where_clause).strip().lower()
    # Use MD5 for more stable hashing
    hash_obj = hashlib.md5(cleaned_clause.encode())
    return f"section_{export_key}_{hash_obj.hexdigest()[:8]}"

# Function to run a different select statement to pull all rows
def generate_full_audience(where_clause=None):
    """Generate full audience without caching"""
    if not where_clause:
        return pd.DataFrame()
    conn = st.experimental_connection("snowpark")
    query = f'SELECT "ACCOUNT ID" FROM KOBIE_BD.PUBLIC.DELTA_DEMO_AUDIENCE_DEMO_MRG {where_clause}'
    df = conn.query(query)
    return df

# Function to check if the message contains an audience summary
def is_audience_summary(content):
    """Check if the message contains an audience summary"""
    return "Audience Summary:" in content and "```sql" in content

# Function to create a JSON structure for the bonus configuration
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

# Helper function to show download and bonus sections with improved state management
def show_download_section(where_clause, export_key, idx, message_idx):
    """Helper function to show download and bonus sections with improved state management"""
    # Create a stable identifier for this section
    section_id = create_stable_id(where_clause, export_key)
    
    # Map message index to section ID for persistence
    st.session_state.section_message_map[message_idx] = section_id
    
    # Initialize section state if not exists
    if section_id not in st.session_state.sections:
        st.session_state.sections[section_id] = {
            "show_form": False,
            "form_submitted": False,
            "where_clause": where_clause
        }
    
    # Create columns
    col1, col2, col3 = st.columns([2, 0.3, 2])
    
    with col1:
        audience_data = generate_full_audience(where_clause)
        st.download_button(
            label="📥 Download Audience Export",
            data=audience_data.to_csv(index=False),
            file_name=f"audience_export_{idx}.csv",
            mime="text/csv",
            key=f"download_{section_id}",
            use_container_width=True
        )
    
    with col3:
        # Use button click to toggle form visibility
        if st.button(
            "🎯 Configure Bonus Template",
            key=f"configure_{section_id}",
            use_container_width=True
        ):
            st.session_state.sections[section_id]["show_form"] = \
                not st.session_state.sections[section_id]["show_form"]

    # Show form based on session state
    if st.session_state.sections[section_id]["show_form"]:
        show_bonus_form(section_id, where_clause)

def show_bonus_form(section_id, where_clause):
    """Separate function to handle bonus form display"""
    with st.form(key=f"bonus_form_{section_id}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        st.markdown("**Bonus Code** _(Must be unique)_")
        st.markdown("_Example: 2XPOINTSDEMO_")
        bonus_code = st.text_input("Bonus Code", key=f"bonus_code_{section_id}")

        st.markdown("_Enter bonus description here_")
        bonus_description = st.text_area("Bonus Description", key=f"description_{section_id}")

        with col1:
            start_date = st.date_input("Start Date", 
                                     value=date.today(), 
                                     key=f"start_date_{section_id}")
        with col2:
            end_date = st.date_input("End Date", 
                                   value=date.today(), 
                                   key=f"end_date_{section_id}")

        bonus_category = st.selectbox(
            "Bonus Category",
            ["Base", "Bonus", "Other"],
            key=f"category_{section_id}"
        )

        bonus_type = st.selectbox(
            "Bonus Type",
            ["Enroll", "Goodwill", "NTE", "Transaction", "TXNBONUS"],
            key=f"type_{section_id}"
        )

        submit_clicked = st.form_submit_button("Submit Bonus Template", 
                                             use_container_width=True)

        if submit_clicked:
            with st.spinner("Creating bonus template..."):
                try:
                    bonus_data = create_bonus_json(
                        start_date, end_date, bonus_code,
                        bonus_category, bonus_type, where_clause,
                        bonus_description
                    )
                    
                    webhook = WorkfrontWebhook()
                    success, status = webhook.send_request(bonus_data)
                    
                    if success:
                        st.session_state.sections[section_id]["form_submitted"] = True
                        st.success("✅ Bonus Template Created!")
                        st.info(f"Workfront Response: {status}")
                except Exception as e:
                    st.error(f"Failed to create bonus template: {str(e)}")

# Process chat input
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display messages and associated sections
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Always show dataframe if results exist, regardless of other conditions
        if message["role"] == "assistant" and "results" in message:
            st.dataframe(message["results"])
        
        # Handle export buttons for audience summaries
        if message["role"] == "assistant" and "results" in message and is_audience_summary(message["content"]):
            sql_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", message["content"], re.DOTALL)
            where_clause = sql_match.group(0) if sql_match else ""
            export_key = f"export_{idx}"
            show_download_section(where_clause, export_key, idx, idx)
        
        # Check if this message has a previously created section
        elif idx in st.session_state.section_message_map:
            section_id = st.session_state.section_message_map[idx]
            if section_id in st.session_state.sections:
                where_clause = st.session_state.sections[section_id]["where_clause"]
                show_download_section(where_clause, f"export_{idx}", idx, idx)

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
            
            # Display dataframe before adding message to state
            st.dataframe(message["results"])
            
            # Add message to state
            st.session_state.messages.append(message)
            message_idx = len(st.session_state.messages) - 1  # Get correct index
            
            # Show download section if appropriate
            where_clause_match = re.search(r"WHERE.*?(?=\b(GROUP BY|ORDER BY|LIMIT|$))", sql, re.DOTALL)
            where_clause = where_clause_match.group(0) if where_clause_match else ""
            export_key = f"export_{message_idx}"
            show_download_section(where_clause, export_key, "final", message_idx)
        else:
            # Just add the message to state
            st.session_state.messages.append(message)