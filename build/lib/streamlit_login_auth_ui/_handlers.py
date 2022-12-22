import json
from pathlib import Path
from typing import Optional
import json
from trycourier import Courier
from argon2 import PasswordHasher
import streamlit as st
from streamlit_login_auth_ui.protocols import CookieManager


ph = PasswordHasher()


class DefaultUserAuth:
    def __init__(self, auth_filename: str = "_secret_auth_.json"):
        self.auth_filename = auth_filename

    def check_credentials(self, username, password) -> bool:
        """
        Authenticates using username and password class attributes.
        - Uses password and username from initialized object

        Return:
            bool: If password is correct -> "True"; if not -> "False"
        """
        with open(self.auth_filename, "r") as auth_json:
            authorized_user_data = json.load(auth_json)

        for user in authorized_user_data:
            if user['username'] == username:
                try:
                    if ph.verify(user['password'], password):
                        return True
                except:
                    pass
        return False


class DefaultAuthCookies:
    def check(self, cookies: CookieManager):
        """
        Checks that auth cookies exist and are valid.
        - Exact internal setup isn't important, so long as it takes the specified parameter below, and
          validates existing cookies (if they exist)

        Args:
            cookies (EncryptedCookieManager): Initialized cookies manager provided by streamlit_login_auth_ui
        
        Returns:
            bool: If cookie(s) are valid -> True; if not valid -> False
        """
        if '__streamlit_login_signup_ui_username__' in cookies.keys() and st.session_state['LOGOUT_BUTTON_HIT'] == False:
            if cookies.get('__streamlit_login_signup_ui_username__') not in ("", None): # self.storage.hashed_cookie(extend=True)
                return True
        return False

    def set(self, username, cookies: CookieManager):
        """
        Sets auth cookie using initialized EncryptedCookieManager.
        - Exact internal setup isn't important, so long as it takes the specified parameters, 
          and sets cookies that indicate an authorized session, and can be interacted with by this class.

        Args:
            username (str): Authorized user
            cookies (EncryptedCookieManager): Initialized cookies manager provided by streamlit_login_auth_ui
        
        Returns:
            None
        """
        cookies.set("__streamlit_login_signup_ui_username__", username)

    def expire(self, cookies: CookieManager):
        """
        Expires auth cookie using initialized EncryptedCookieManager.
        - Exact internal setup isn't important, so long as it takes the specified parameters, 
          and changes the existing cookies status to indicate an invalid session.

        Args:
            cookies (EncryptedCookieManager): Initialized cookies manager provided by streamlit_login_auth_ui
        
        Returns:
            None
        """
        cookies.expire("__streamlit_login_signup_ui_username__")

    def get_username(self, cookies: CookieManager):
        if st.session_state['LOGOUT_BUTTON_HIT'] == False:
            if '__streamlit_login_signup_ui_username__' in cookies.keys():
                return cookies.get('__streamlit_login_signup_ui_username__')


class DefaultUserStorage:
    def __init__(self, auth_filename: str = "_secret_auth_.json"):
        self.auth_filename = auth_filename
        self.check_auth_json_file_exists()
    
    def register(self, name: str, email: str, username: str, password: str) -> None:
        """
        Saves the information of the new user in the json auth file.

        Args:
            name (str): name for new account
            email (str): email for new account
            username (str): username for new account
            password (str): password for new account

        Return:
            None
        """
        new_usr_data = {'username': username, 'name': name, 'email': email, 'password': ph.hash(password)}

        with open(self.auth_filename, "r") as auth_json:
            authorized_user_data = json.load(auth_json)

        with open(self.auth_filename, "w") as auth_json_write:
            authorized_user_data.append(new_usr_data)
            json.dump(authorized_user_data, auth_json_write)

    def check_username_exists(self, username: str) -> bool:
        """
        Checks if the username exists in the json auth file.

        Args:
            username (str): username to check

        Return:
            bool: If username exists -> "True"; if not -> "False"
        """
        authorized_user_data_master = list()
        with open(self.auth_filename, "r") as auth_json:
            authorized_users_data = json.load(auth_json)

            for user in authorized_users_data:
                authorized_user_data_master.append(user['username'])
            
        if username in authorized_user_data_master:
            return True
        return False

    def check_email_exists(self, email: str):
        """
        Checks if the email entered is present in the json auth file.

        Args:
            email (str): email connected to forgotten password

        Return:
            Tuple[bool, Optional[str]]: If exists -> (True, <username>); If not, (False, None)
        """
        with open(self.auth_filename, "r") as auth_json:
            authorized_users_data = json.load(auth_json)
            for user in authorized_users_data:
                if user['email'] == email:
                    return True, user['username']
        return False, None

    def get_username_from_email(self, email: str) -> Optional[str]:
        """
        Retrieve username, if it exists, from the json auth file.

        Args:
            email (str): email connected to forgotten password

        Return:
            Optional[str]]: If exists -> <username>); If not -> None
        """
        with open(self.auth_filename, "r") as auth_json:
            authorized_users_data = json.load(auth_json)
        for user in authorized_users_data:
            if user['email'] == email:
                return user['username']
        return None

    def change_password(self, email: str, password: str) -> None:
        """
        Replaces the old password with the newly generated password.

        Args:
            email (str): email connected to account
            password (str): password to set

        Return:
            None
        """
        with open(self.auth_filename, "r") as auth_json:
            authorized_users_data = json.load(auth_json)

        with open(self.auth_filename, "w") as auth_json_:
            for user in authorized_users_data:
                if user['email'] == email:
                    user['password'] = ph.hash(password)
            json.dump(authorized_users_data, auth_json_)

    def check_auth_json_file_exists(self) -> bool:
        """
        Checks if the auth file (where the user info is stored) already exists.
        """
        filename = Path(self.auth_filename)
        if not filename.exists():
            with open(filename, "w") as auth_json:
                json.dump([], auth_json)


class DefaultForgotPasswordMsg:
    def send(self, auth_token: str, username: str, email: str, company_name: str, reset_password: str) -> None:
        """
        Triggers an email to the user containing the randomly generated password.

        Args:
            auth_token (str): Courier api token
            username (str): User's username
            email (str): User's email
            company_name (str): Used in email title ("<company_name>: Login Password")
            reset_password (str): New temporary password to send

        Returns:
            None
        """
        client = Courier(auth_token = auth_token)

        resp = client.send_message(
            message={
                "to": {
                    "email": email
                },
                "content": {
                    "title": company_name + ": Login Password!",
                    "body": "Hi! " + username + "," + "\n" + "\n" + "Your temporary login password is: "
                                   + reset_password  + "\n" + "\n" + "{{info}}"
                },
                "data":{
                    "info": "Please reset your password at the earliest for security reasons."
                }
            }
        )
