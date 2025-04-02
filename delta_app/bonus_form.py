import streamlit as st
import random
import string
import datetime

# Function to show bonus form
def show_bonus_form():
    st.session_state.show_bonus_form = True
    st.session_state.bonus_code = ''.join(random.choices(string.ascii_uppercase, k=5))

# Bonus creation form
def create_bonus_form():
    with st.form("bonus_form", clear_on_submit=True):
        st.subheader("Create New Bonus")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", min_value=datetime.today() + datetime.timedelta(days=1))
        with col2:
            end_date = st.date_input("End Date", min_value=start_date + datetime.timedelta(days=1))
        
        st.text_input("Bonus Code", value=st.session_state.bonus_code, disabled=True)
        st.text_input("Bonus Category", value="BONUS", disabled=True)
        st.text_input("Bonus Type", value="TXNBONUS", disabled=True)
        
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.success("Bonus Created!")
            st.session_state.show_bonus_form = False