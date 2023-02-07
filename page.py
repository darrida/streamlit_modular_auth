# src.pages.base.page.py

from typing import List
import time
from streamlit import session_state as st_session_state, warning, spinner
from sqlalchemy.engine import Engine
from darrida_library.util import DarridaSecret
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_modular_auth import cookies
from streamlit.components.v1 import html
from src.config import secrets, Config


# @dataclass
class Page:
    title: str  # Full title show on page
    name: str  # short name for state management
    groups: List[str]
    state: st_session_state = st_session_state
    secret: DarridaSecret = secret
    config: Config = Config()
    cookies = cookies
    
    # def check_permissions(self, expected: Union[str, List[str]], provided: str = None) -> bool:
    def check_permissions(self, provided: str = None) -> bool:
        if self.state.get("LOGGED_IN") != True:
            warning("Not logged in...")
            with spinner("Redirecting..."):
                time.sleep(1)
                self.change_page("")

        # if isinstance(expected, str):
        #     # expected = [expected]

        if provided:
            user_groups = provided
        else:
            if "groups" not in self.state.keys():
                user_groups = self.cookies.get("groups")
                if user_groups:
                    self.state["groups"] = user_groups.split(",")
            else:
                user_groups = self.state["groups"]
        if not user_groups:
            return False
        self.groups.append("admin")
        return any(True for x in self.groups if x in user_groups)

    def check_state(self):
        if (
            self.state.get("page")
            and self.state["page"].get("name") == self.name
        ):
            return
        if self.state.get("page"):
            self.state.pop("page")
        self.state["page"] = {"name": self.name}

    def save_upload(self, filename, upload: UploadedFile):
        bytes_data = upload.getvalue()
        with open(filename, "wb") as outfile:
            outfile.write(bytes_data)

    def add_db(self, db: Engine) -> Engine:
        return db

    def change_page(self, page_name, timeout_secs=3):
        """Programmatically changes pages
        - Found in Streamlit GitHub Issue: https://github.com/streamlit/streamlit/issues/4832#issuecomment-1201938174
        - Should be **REPLACED** when Streamlit releases native way to accomplish this

        Example usage (from issue post):
        ```
        if st.button("< Prev"):
            nav_page("Foo")
        if st.button("Next >"):
            nav_page("Bar")
        ```
        """
        nav_script = """
            <script type="text/javascript">
                function attempt_nav_page(page_name, start_time, timeout_secs) {
                    var links = window.parent.document.getElementsByTagName("a");
                    for (var i = 0; i < links.length; i++) {
                        if (links[i].href.toLowerCase().endsWith("/" + page_name.toLowerCase())) {
                            links[i].click();
                            return;
                        }
                    }
                    var elasped = new Date() - start_time;
                    if (elasped < timeout_secs * 1000) {
                        setTimeout(attempt_nav_page, 100, page_name, start_time, timeout_secs);
                    } else {
                        alert("Unable to navigate to page '" + page_name + "' after " + timeout_secs + " second(s).");
                    }
                }
                window.addEventListener("load", function() {
                    attempt_nav_page("%s", new Date(), %d);
                });
            </script>
        """ % (page_name, timeout_secs)
        html(nav_script)
        
        
# src.handlers.auth.py

from sqlmodel import Session, select
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import streamlit as st
from streamlit_modular_auth import cookie
from src.db.db import app_engine as engine
from src.apps.admin.models import User


class SQLModelUserAuth:
    def check_credentials(self, username, password):
        """
        Authenticates using username and password class attributes.
        - Uses password and username from initialized object
        - Queries user in SQLModel database (SQLite)
        - Checks password provided by streamlit_login_auth_ui against hashed password from database.
        Return:
            bool: If password is correct -> "True"; if not -> "False"
        """
        with Session(engine) as session:
            statement = select(User).where(User.username == username)
            user = session.exec(statement).one()
            if user and user.active == True:
                ph = PasswordHasher()
                try:
                    if (
                        self.ldap_auth(username, password)  # Attempt to authenticate using LDAP
                        or ph.verify(user.hashed_password, password)  # Attempt to authenticate using local password hash
                    ):
                        if user.groups:
                            groups = [x.name for x in user.groups]
                            st.session_state["groups"] = groups
                            cookies.set("groups", ",".join(groups))
                        st.session_state["username"] = username
                        return True
                except VerifyMismatchError as e:
                    if str(e) != "The password does not match the supplied hash":
                        raise VerifyMismatchError(e) from e
        return False
      
# src.handlers.cookies.py

import secrets
from datetime import datetime, timedelta
import streamlit as st
import diskcache


dc = diskcache.Cache("cache.db")


if show_typing := True:  # For typing purposes only
    from streamlit_modular_auth.protocols import CookieManager


class DiskcacheAuthCookies:
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
        if "auth_username" not in cookies.keys() and "auth_token" in cookies.keys():
            return False
        local_username = cookies.get("auth_username")
        local_token = cookies.get("auth_token")

        if user_cache := dc.get(local_username):
            if (
                user_cache["auth_token"] == local_token
                and datetime.fromisoformat(user_cache["expires"]) >= datetime.now()
            ):
                return True
            else:
                st.error("Session expired...")
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
        auth_token = secrets.token_urlsafe(48)
        expires = datetime.now() + timedelta(seconds=200)
        user_session_cache = {
            "auth_token": auth_token,
            "expires": expires.isoformat()
        }
        dc.set(username, user_session_cache)
        cookies.set("auth_token", auth_token)
        cookies.set("auth_username", username)

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
        cookies.expire("auth_token")
        cookies.expire("groups")
        st.session_state.pop("groups")
        
# src.handlers.user.py

from typing import Optional
from datetime import datetime
from argon2 import PasswordHasher
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound
from src.apps.admin.models import User
from src.db.db import a_engine as engine


class SQLModelUserStorage:
    def register(self, name: str, email: str, username: str, password: str, first_name: str, last_name: str, ldap: bool = True) -> None:
        """
        Saves the information of the new user in SQLModel database (SQLite)
        Args:
            name (str): name for new account
            email (str): email for new account
            username (str): username for new account
            password (str): password for new account
        Return:
            None
        """
        ph = PasswordHasher()
        user = User(
            username=username, 
            email=email, 
            first_name=first_name,
            last_name=last_name, 
            hashed_password=ph.hash(password),
            active=True,
            ldap=ldap,
            create_date=datetime.now())
        with Session(engine) as session:
            session.add(user)
            session.commit()

    def check_username_exists(self, username: str) -> bool:
        """
        Checks is username already exists in SQLModel database (SQLite)
        Args:
            username (str): username to check
        Return:
            bool: If username exists -> "True"; if not -> "False"
        """
        try:
            with Session(engine) as session:
                statement = select(User).where(User.username == username)
                if user := session.exec(statement).one():
                    return True
        except NoResultFound:
            return False
        return False

    def get_username_from_email(self, email: str) -> Optional[str]:
        """
        Retrieve username, if it exists, from SQLModel database (SQLite) from provided email.
        Args:
            email (str): email connected to forgotten password
        Return:
            Optional[str]: If exists -> <username>; If not -> None
        """
        try:
            with Session(engine) as session:
                statement = select(User).where(User.email == email)
                if user := session.exec(statement).one():
                    return user.username
        except NoResultFound:
            return None
        return None

    def change_password(self, email: str, password: str) -> None:
        """
        Replaces the old password in SQLModel database (SQLite) with the newly generated password.
        Args:
            email (str): email connected to account
            password (str): password to set
        Return:
            None
        """
        ph = PasswordHasher()
        with Session(engine) as session:
            statement = select(User).where(User.email == email)
            if user := session.exec(statement).one():
                user.hashed_password = ph.hash(password)
                session.add(user)
                session.commit()

# src.apps.admin.models.py

from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


class UserGroupsLink(SQLModel, table=True):
    __table_args__ = {
        # 'schema': "apps",
        'keep_existing': True,
        # 'extend_existing': True
    }

    group_id: Optional[int] = Field(
        default=None, foreign_key="streamlit_groups.id", primary_key=True
    )
    user_id: Optional[int] = Field(
        default=None, foreign_key="streamlit_users.id", primary_key=True
    )
    create_date: Optional[datetime] = datetime.now()
    created_by: str = "ADMIN"
    update_date: datetime = datetime.now()
    updated_by: str = "ADMIN"


class Group(SQLModel, table=True):
    __table_args__ = {
        # 'schema': "apps",
        'keep_existing': True,
        # 'extend_existing': True
    }
    __tablename__ = "streamlit_groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    active: bool = True
    create_date: Optional[datetime]
    created_by: str = "ADMIN"
    update_date: datetime = datetime.now()
    updated_by: str = "ADMIN"

    users: List["User"] = Relationship(back_populates="groups", link_model=UserGroupsLink)


class User(SQLModel, table=True):
    __table_args__ = {
        # 'schema': "apps",
        'keep_existing': True,
        # 'extend_existing': True
    }
    __tablename__ = "streamlit_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    first_name: str
    last_name: str
    hashed_password: str
    active: bool
    ldap: bool = True
    admin: bool = False
    create_date: Optional[datetime]
    created_by: str = "ADMIN"
    update_date: datetime = datetime.now()
    updated_by: str = "ADMIN"

    groups: List[Group] = Relationship(back_populates="users", link_model=UserGroupsLink)

      
# src.apps.admin.admin.py

from typing import List
import secrets
import streamlit as st
from sqlmodel import Session, select
from argon2 import PasswordHasher
from sqlalchemy.exc import IntegrityError, NoResultFound
from src.apps.admin.models import User, Group
from src.handlers.user import SQLModelUserStorage
from src.db.db import app_engine
from src.pages.models.page import Page


class AdminPage(Page):
    title = "Admin Tools"
    name = "admin"
    groups = ["admin"]
    db = app_engine


    # CALLABLES FOR INPUT WIDGETS
    def change_user_status(self, username, active):
        if active == True:
            self.user_disable(username)
        else:
            self.user_enable(username)


    def change_group_status(self, name, active):
        print(name, active)
        if active == True:
            print("Attempt to disable")
            self.group_disable(name)
        else:
            print("Attempt to enable")
            self.group_enable(name)


    def change_user_group_status(self, username: str, group: str, granted):
        if not granted:
            self.user_add_groups(username, group)
        else:
            self.user_delete_group(username, group)


    def open_user_info(self, username):
        with Session(self.db) as session:
            statement = select(User).where(User.username == username)
            if user := session.exec(statement).one():
                st.session_state["page"]["open_user"] = user


    # FUNCTIONALITY
    def user_info(self, user: User = None):
        st.markdown("### User Info")

        password = None
        # USER INFORMATION
        col1, _, col2, col3, _ = st.columns((0.4, 0.1, 0.05, 0.2, 0.25), gap="small")#["Information", "Groups"])
        with col1:
            user.username = st.text_input("Username", value=user.username or None)
            user.first_name = st.text_input("First Name", value=user.first_name or None)
            user.last_name = st.text_input("Last Name", value=user.last_name or None)
            user.email = st.text_input("Email", value=user.email or None)
            auth_option = st.selectbox("Authentication", ("LDAP", "Password", "LDAP and Password"))
            if auth_option in ("Password", "LDAP and Password"):
                password = st.text_input("Password", type="password", placeholder="*************")

            user.ldap = auth_option in ("LDAP", "LDAP and Password")

        # USER PERMISSION GROUPS
        all_groups = self.group_get_all()
        permissions = self.user_get_groups(user.username)
        for i, group in enumerate(all_groups, start=1):
            group_checkbox = col2.empty()
            col3.write(group)
            if group:
                granted = group in permissions
            group_checkbox.checkbox(
                label="", value=granted, key=f"{i}_group_list", 
                on_change=self.change_user_group_status, args=[user.username, group, granted]
            )

        # RECORD DATES
        created_col, updated_col, dates_spacer = st.columns(3)
        with created_col:
            st.markdown(f"**Create Date:** {str(user.create_date)[:16] or ''}")
            st.markdown(f"**Create User:** {user.created_by or ''}")
        with updated_col:
            st.markdown(f"**Update Date:** {str(user.update_date)[:16] or ''}")
            st.markdown(f"**Update User:** {user.updated_by or ''}")

        # BUTTONS
        save_col, close_col, button_spacer = st.columns((0.25, 0.25, 2))
        with save_col:
            if st.button("Save"):
                if password:
                    ph = PasswordHasher()
                    user.hashed_password = ph.hash(password)
                self.user_update(user)
                st.experimental_rerun()
        with close_col:
            if st.button("Close"):
                st.session_state["page"].pop("open_user")
                st.experimental_rerun()


    def create_user(self):
        # CREATE USER
        create_user = st.empty()
        with create_user.form("Create User"):
            username = st.text_input("Username", placeholder="Xnumber or Username")
            first_name = st.text_input("First Name", placeholder="User's first name")
            last_name = st.text_input("Last Name", placeholder="User's last name")
            email = st.text_input("Email", placeholder="Unique email")
            ldap = st.checkbox("Authenticate using LDAP", value=True)
            password = st.text_input("Password", type="password", value=secrets.token_urlsafe(45))
            st.markdown("###")
            create_user = st.form_submit_button(label="Create")

        if create_user == True:
            storage = SQLModelUserStorage()
            try:
                storage.register(
                    "", email, username, password=password, first_name=first_name, last_name=last_name, ldap=ldap)
                with Session(self.db) as session:
                    statement = select(User).where(User.username == username)
                    if results := session.exec(statement).one():
                        st.success("User created.")
            except NoResultFound:
                st.error("An error occurred while attempting to create user.")
            except IntegrityError:
                st.warning("User or email address already exists.")
        if st.button("Close"):
            st.session_state["page"].pop("create_user")
            st.experimental_rerun()


    def users_list(self, users: List[User]):        
        st.write("### User List")
        for i, user in enumerate(users, start=1):
            col1, col2, col3, col4, col5 = st.columns((0.5, 1, 1, 1, 1))
            active_checkbox = col1.empty()
            col2.write(user.username)
            col3.write(f"{user.first_name} {user.last_name}")
            col4.write("Active" if user.active else "Inactive")
            open_button = col5.empty()
            
            active_checkbox.checkbox(label="", value=user.active, key=i, on_change=self.change_user_status, args=[user.username, user.active])
            open_button.button("Open", key=f"{i}_open_user", on_click=self.open_user_info, args=[user.username])


    def groups_list(self, groups: List[Group]):        
        page_state = st.session_state["page"]
        
        st.write("### Group List")
        if page_state.get("show_all_groups") != True:
            if st.button("Show Inactive"):
                page_state["show_all_groups"] = True
                st.experimental_rerun()
            groups = [x for x in groups if x.active == True]
        elif page_state["show_all_groups"] == True:
            if st.button("Hide Inactive"):
                page_state.pop("show_all_groups")
                st.experimental_rerun()
        for i, group in enumerate(groups, start=1):
            col1, col2, col3, col4, col5 = st.columns((0.5, 1, 1, 1, 1))
            active_checkbox = col1.empty()
            col2.write(group.name)

            active_checkbox.checkbox(label="", value=group.active, key=f"{i}_groups", on_change=self.change_group_status, args=[group.name, group.active])


    def user_add_groups(self, username: str, groups: str) -> None:
        with Session(self.db) as session:
            group_statement = select(Group).where(Group.name == groups)
            group = session.exec(group_statement).one()
            user_statement = select(User).where(User.username == username)
            if user := session.exec(user_statement).one():
                user.groups.append(group)
                session.add(user)
                session.commit()
                return True
            else:
                import streamlit as st
                st.error("Found no record for user.")


    def user_delete_group(self, username: str, group: str):
        with Session(self.db) as session:
            group_statement = select(Group).where(Group.name == group)
            group = session.exec(group_statement).one()
            user_statement = select(User).where(User.username == username)
            if user := session.exec(user_statement).one():
                if user.groups:
                    user.groups.remove(group)
                    session.add(user)
                    session.commit()
                    return True
            else:
                import streamlit as st
                st.error("Found no record for user.")


    def user_get_groups(self, username: str):
        with Session(self.db) as session:
            statement = select(User).where(User.username == username)
            if user := session.exec(statement).one():
                return [x.name for x in user.groups] if user.groups else []
            else:
                st.error("Found no record for user.")


    def user_get_all(self):
        with Session(self.db) as session:
            statement = select(User)
            if users := session.exec(statement):
                return list(users)
            import streamlit as st
            st.error("Found no users.")


    def user_update(self, user: User) -> None:
        """
        Saves the information of the new user in SQLModel database (SQLite)
        Args:
            name (str): name for new account
            email (str): email for new account
            username (str): username for new account
            password (str): password for new account
        Return:
            None
        """
        with Session(self.db) as session:
            statement = select(User).where(User.username == user.username)
            if saved_user := session.exec(statement).one():
                saved_user.active = user.active
                saved_user.email = user.email
                saved_user.last_name = user.last_name
                saved_user.hashed_password = user.hashed_password
                saved_user.active = user.active
                saved_user.ldap = user.ldap
                saved_user.admin = user.admin
            session.add(saved_user)
            session.commit()


    def user_disable(self, username: str):
        self._user_change_status(False, username)


    def user_enable(self, username: str):
        self._user_change_status(True, username)

    @staticmethod
    def user_refresh_groups(self, username: str) -> None:
        with Session(self.db) as session:
            statement = select(User).where(User.username == username)
            if user := session.exec(statement).one():
                if user.groups:
                    self.cookies.set("groups", user.groups)
                    st.session_state["groups"] = user.groups.split(",")

    def _user_change_status(self, change_to: bool, username: str):
        with Session(self.db) as session:
            statement = select(User).where(User.username == username)
            if user := session.exec(statement).one():
                user.active = change_to
                session.add(user)
                session.commit()
                return True
            else:
                import streamlit as st
                st.error("Found no record for user.")


    ##################################################################
    # GROUPS
    ##################################################################
    def create_group(self, name):
        try:
            group = Group(name=name)
            with Session(self.db) as session:
                session.add(group)
                session.commit()
        except IntegrityError as e:
            if "UNIQUE" not in str(e):
                raise IntegrityError(e) from e
            print(f"Group with name {group.name} already exists.")
            return False
        return True


    def group_get_all(self, return_str=True) -> List["Group"]:
        groups_l = []
        with Session(self.db) as session:
            statement = select(Group)
            groups = session.exec(statement)
            if return_str and groups:
                groups_l = [x.name for x in groups]
            elif groups:
                groups_l = list(groups)
            else:
                import streamlit as st
                st.error("Found no groups.")
        return groups_l


    def group_disable(self, name: str):
        self._change_group_status(False, name)


    def group_enable(self, name: str):
        self._change_group_status(True, name)


    def _change_group_status(self, change_to: bool, name: str):
        with Session(self.db) as session:
            statement = select(Group).where(Group.name == name)
            if group := session.exec(statement).one():
                group.active = change_to
                session.add(group)
                session.commit()
                return True
            else:
                import streamlit as st
                st.error("Found no record for group.")

# src.pages.Admin.py

import streamlit as st
from src.apps.admin.models import User
from src.apps.admin.admin import AdminPage

page = AdminPage()


st.markdown("## Admin Tools")

st.markdown("---")

if not page.check_permissions():
    st.warning("Insufficient permissions.")
else:
    page.check_state()
    # LIST USERS
    user_tab, edit_tab, group_tab = st.tabs(["Users List", "User Changes", "Groups List"])
    with user_tab:
        if user := st.session_state["page"].get("open_user"):
            page.user_info(user)
        elif st.session_state["page"].get("create_user"):
            page.create_user()
        else:
            users = page.user_get_all()
            page.users_list(users)
            if st.button("Create User"):
                st.session_state["page"]["create_user"] = True
                st.experimental_rerun()

    # ADD GROUP
    with edit_tab:
        add_group = st.empty()
        with add_group.form("Add Group"):
            username = st.text_input("Username")
            groups = st.text_input("Group")
            st.markdown("###")
            add_group_button = st.form_submit_button(label="Add")

        if add_group_button == True:
            if result := page.user_add_groups(username, groups):
                st.success("Added group(s).")
        
        # REMOVE GROUP
        remove_group = st.empty()
        with remove_group.form("Remove Group"):
            username = st.text_input("Username")
            group = st.text_input("Delete Group")
            st.markdown("###")
            remove_group_button = st.form_submit_button(label="Remove")

        if remove_group_button == True:
            if result := page.user_delete_group(username, group):
                st.success("Removed group.")

    with group_tab:
        groups = page.group_get_all(return_str=False)
        # groups = [x.name for x in groups]
        page.groups_list(groups)
        if st.button("Add Group") or page.state["page"].get("add_group"):
            page.state["page"]["add_group"] = True
            name = st.text_input("Group Name")
            col1, col2, spacer = st.columns((0.5, 0.5, 2))
            with col1:
                if st.button("Create"):
                    if not name:
                        st.warning("Name required")
                    else:
                        if group := page.create_group(name):
                            st.success(f"Group {group} created.")
                        page.state["page"].pop("add_group")
                        st.experimental_rerun()
            with col2:
                if st.button("Close"):
                    page.state["page"].pop("add_group")
                    st.experimental_rerun()
