import streamlit as st

from streamlit_modular_auth import Login, ModularAuth

app = ModularAuth()
app.set_database_storage(hide_admin=True)
login = Login(app)


st.markdown("## Streamlit Modular Auth")
st.markdown("### Default SQLite Configuration")

st.warning(
    "To initialize sqlite database: "
    "\n\n(1) run this app using the following format: "
    "`streamlit run <app>.py init_storage`"
    "\n\n(2) stop the app"
    "\n\n(3) start it again without `init_storage`"
)


if login.build_login_ui():
    st.success("You're logged in!")
else:
    st.info("You're not logged in yet...")
