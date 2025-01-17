import streamlit as st
from tests_handlers._test_cookies import UserAuthCookiesTest

# from streamlit_modular_auth import ModularAuth, DefaultBaseView
from streamlit_modular_auth import Login, ModularAuth

app = ModularAuth()
app.login_expire = 15
app.login_label = "Test Login"
app.plugin_auth_cookies = UserAuthCookiesTest()

login = Login(app)

if login.build_login_ui() is True:
    st.markdown("Your Streamlit Application Begins here!")

    if st.button("Click here..."):
        st.write("Here is some more text.")
