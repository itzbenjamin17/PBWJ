import streamlit as st

form = st.form("my_form")
trello_api_key = form.text_input("Trello API Key")
trello_token = form.text_input("Trello Token", type="password")
github_url = form.text_input("GitHub URL")
submitted = form.form_submit_button("Connect")

if submitted:
    print(trello_api_key, trello_token, github_url)