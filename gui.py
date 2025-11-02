import streamlit as st
from app import main
st.title("OctoBoard")
form = st.form("my_form")
trello_api_key = form.text_input("Trello API Key")
trello_token = form.text_input("Trello Token", type="password")
github_url = form.text_input("GitHub URL")
submitted = form.form_submit_button("Connect")

if submitted:
    status = st.status("Creating your Trello board...")
    main(trello_api_key, trello_token, status)
    st.success("Trello board created successfully!")
