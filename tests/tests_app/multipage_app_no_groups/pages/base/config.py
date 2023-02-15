from streamlit_modular_auth import ModularAuth
from handlers._test_user_storage import UserAuthTest, UserStorageTest
from handlers._test_cookies import UserAuthCookiesTest


app = ModularAuth(
    plugin_user_auth=UserAuthTest(),
    plugin_user_storage=UserStorageTest(),
    plugin_auth_cookies=UserAuthCookiesTest(),
    login_expire=15,
)

# app.plugin_user_auth = UserAuthTest()
# app.plugin_user_storage = UserStorageTest()
# app.plugin_auth_cookies = UserAuthCookiesTest()
# app.login_expire = 15