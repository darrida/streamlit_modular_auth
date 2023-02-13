*** Settings ***
Library  SeleniumLibrary
Library  Process
Library  OperatingSystem
Library  DependencyLibrary

Variables    ../_test_variables.py


*** Variables ***
${URL}             http://localhost:${PORT_HIDE_ACCOUNT_MGMT}/


*** Test Cases ***
No Acc Mgmt - Login Screen
    Open Browser  ${URL}  browser=${BROWSER}  service_log_path=${DRIVER_LOGS}
    Wait Until Page Contains    Username    timeout=${TIMEOUT}
    Page Should Contain     Password
    Page Should Contain     Login
    Select Frame    tag:iframe
    Wait Until Element Is Visible   //*[contains(text(),"Navigation")]
    Page Should Contain     Navigation
    Page Should Contain     Login
    Page Should Not Contain     Create Account
    Page Should Not Contain     Forgot Password?
    Page Should Not Contain     Reset Password
    Close Browser


No Acc Mgmt - Create Account (using webserver w/acc mgmt)
    Open Browser    http://localhost:8001/  browser=${BROWSER}  service_log_path=${DRIVER_LOGS}
    Wait Until Page Contains    Username    timeout=${TIMEOUT}
    Wait Until Element Is Visible   tag:iframe
    Select Frame    tag:iframe
    Wait Until Element Is Visible      //a[contains(text(),'Create Account')]
    Click Element                   //a[contains(text(),'Create Account')]
    Unselect Frame
    Wait Until Element Is Visible   //*[@placeholder="Please enter your name"]
    Input Text      //*[@placeholder="Please enter your name"]    Fname Lname
    Wait Until Element Is Visible   //*[@placeholder="Please enter your email"]
    Input Text      //*[@placeholder="Please enter your email"]    flname8@email.com
    Wait Until Element Is Visible   //*[@placeholder="Enter a unique username"]
    Input Text      //*[@placeholder="Enter a unique username"]    user8
    Wait Until Element Is Visible   //*[@placeholder="Create a strong password"]
    Input Text      //*[@placeholder="Create a strong password"]    password8
    Click Element   //*[contains(text(),'Register')]
    Wait Until Element Is Visible   //*[contains(text(),"Registration Successful!")]
    Page Should Contain     Registration Successful!
    Close Browser


No Acc Mgmt - Login, then Logout
    Open Browser    ${URL}  browser=${BROWSER}  service_log_path=${DRIVER_LOGS}
    Wait Until Page Contains    Username    timeout=${TIMEOUT}
    Wait Until Element Is Visible   //*[@placeholder="Your unique username"]
    Input Text      //*[@placeholder="Your unique username"]    user8
    Wait Until Element Is Visible   //*[@placeholder="Your password"]
    Input Text      //*[@placeholder="Your password"]    password8
    Click Element   //*[contains(text(),'Login')]
    Wait Until Element Is Visible   //*[contains(text(),"Your Streamlit Application Begins here!")]
    Page Should Contain     Your Streamlit Application Begins here!
    Wait Until Element Is Visible   //*[contains(text(),'Logout')]
    Click Element    //*[contains(text(),'Logout')]
    Wait Until Element Is Visible   //*[contains(text(),'Login')]
    Page Should Contain     Login
    Close Browser


No Acc Mgmt - Login Failed - Invalid Password
    Open Browser    ${URL}  browser=${BROWSER}  service_log_path=${DRIVER_LOGS}
    Wait Until Page Contains    Username    timeout=${TIMEOUT}
    Wait Until Element Is Visible   //*[@placeholder="Your unique username"]
    Input Text      //*[@placeholder="Your unique username"]    user8
    Wait Until Element Is Visible   //*[@placeholder="Your password"]
    Input Text      //*[@placeholder="Your password"]    password1
    Wait Until Element Is Visible   //*[contains(text(),'Login')]
    Click Element   //*[contains(text(),'Login')]
    Wait Until Element Is Visible   //*[contains(text(),"Invalid Username or Password!")]
    Page Should Contain     Invalid Username or Password!
    Close Browser


No Acc Mgmt - Login Failed - Invalid Username
    Open Browser    ${URL}  browser=${BROWSER}  service_log_path=${DRIVER_LOGS}
    Wait Until Page Contains    Username    timeout=${TIMEOUT}
    Wait Until Element Is Visible   //*[@placeholder="Your unique username"]
    Input Text      //*[@placeholder="Your unique username"]    user2
    Wait Until Element Is Visible   //*[@placeholder="Your password"]
    Input Text      //*[@placeholder="Your password"]    password1
    Wait Until Element Is Visible   //*[contains(text(),'Login')]
    Click Element   //*[contains(text(),'Login')]
    Wait Until Element Is Visible   //*[contains(text(),"Invalid Username or Password!")]
    Page Should Contain     Invalid Username or Password!
    Close Browser