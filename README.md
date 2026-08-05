# Project-Development - Area Aacademy Attendance System

---

# Overview

The Project is a full stack web-application with integerated AI software designed to streamline the attendance process for AREA Academy Company. This project consist of secturiy checks, seamless conversation with AI to provide analysis and sleek dashboard for a clear visual to the user.

## Company Specification

The company consist of 13 branches across Azerbaijan with each branch having their own manager. For each branch, there are employees working and the employee may work in more than one branch.

## Tech Stack and Workflow

The tech stack we will use will be the following:

- Framework and programming language - Django Framework, Python
- Database - Postgresql
- LLM Model - OpenAI GPT Model

As for the workflow it goes as follow:

1. Employees and branch manager scan the QR code physically present in each branch
2. The link directs them to the log in page for AREA Academy
3. The backend Authenticate and Authorize the User(whether they are Employee, Super Admin or Branch Manager)
4. If they are Employee or Branch Manager, they are asked to check in for the attendance using the haversion algorithm. This ensures a safe and fraudulent-proof way to check in
5. Then Based on their role, they are each designated with a dasboard
6. For Super Admin, they can acess every data across all branch and use filtering to filter the branch with highest absentism, highest presence etc
7. For Branch Manager, they are able to access the data belonging to their branch only and can use filtering and querying to check for abnormalities or trends etc.
8. For Employee, They can only check the current month’s attendance.
9. Since all employees have thier own working days, a total working days will be stored inside the database and at the end of each month, the total checkin for each employee will be compared with that of the total working days each employees have. If they fall short, those days will be rendered absent and if they fall above, those extra days will be rendered overtime or substitution.
10. An AI Chatbot on the right side of the dashboard for Branch Manager and Super Admin will also be created that aids in analysis and visualization. To ensure unauthorized acess to all the data via the Chatbot, Branch Manager shall be able to use chatbot for their specific branch.

# Phase by Phase Execution

## Phase 1: Project Set-Up and Initialization

Here are the Agendas we need to have:

- Create a new folder for the project.
- Set up a virtual environment and install pandas, numpy, django and matplotlib for now.
- Using django-admin, start the new project and name it as area_academy.
- Create a new folder in the root directory called apps that is used to develop the application
- Ensure to have .env, .gitignore and a simple README.md file too.
- Create a Brand new Postgresql database and configure it in the settings.py file.
- Connect to Github Repository and commit the project structure.

## Phase 2: Initializing the Core App Strucuture.

Agendas:

- Start three apps under the directory apps using django-admin or python manage.py startapp…
- Name the first app _branch_ that stores information and confiuration consisiting of all the 13 branches including their latitude and longitude.
- Name the Second app _authentication_ for a custom user model consisting of a hierarchy of 3 level: Super Admin, Branch Manager and Employee.
- Name the third app _attendance_ that handles the frontend user interface, API(s) and all the core logics.
- add urls.py in each app
- Change the app directory in the apps.py in each app from thier respective path name to _apps.{thier_name}_.
- Push to code to github

### Phase 3: Model Creation and Migration

- Go to the branch app’s models.py file and add the following model attribute:
  1. Name - Stores the name of the branches
  2. Latitude - Stores the latitutde of the branches
  3. Longitude - Stores the longitude of the branches
  4. Geofencing_Radius - Stores the maximum distance allowed for checking in
- Then go to the Authentication app’s models.py file and create a custom user model called User using the AbstractUser class from django consisting of the three levelled user model.
- Similarly go to the attendance app’s models.py file and create a model consisting of the following attributes:
  1. Name - Name of the User( A foreign Key)
  2. Role - A foreign key connecting to the User model defining the role of the user
  3. Check In Time - A datetime field to auto input the check in time
  4. Check Out Time - A Datetime filed to auto input the check out time
  5. Is Verified - A Boolean value to check if their check in and check out time is verified
  6. Status - To store whether the user is present, absent, late, on leave or is doing a remote work
- After creating all these model, register them from admin.py file for each app. For Authentication app’s ensure to use the UserAdmin class and add the additional fields if any.
- Migrate the model and push to github

#### IMPORTANT NOTE: The feilds in this app can be subjected to change, addition and removal based on project preferences as we go.

### Phase 4: Authentication System and Login Page

### Objectives

Develop a secure authentication system that serves as the entry point of the application and redirects users to their respective interfaces based on their assigned role.

### Agendas

- Create a custom login page inside the **authentication** app.
- Design a clean and responsive user interface for the login page.
- Create a Django Login Form using Django Forms.
- Develop a custom login view that authenticates users using Django's authentication system.
- Validate incorrect usernames and passwords and display appropriate error messages.
- Configure the login URL and connect it to the project-level URL configuration.
- Create a logout functionality that securely terminates the current session.
- Protect all authenticated pages using Django authentication decorators.
- Implement role-based redirection after successful login:
  - Super Admin → Super Admin Dashboard
  - Branch Manager → Branch Manager Dashboard
  - Employee → Attendance Check-in Page
- Create temporary placeholder views for all dashboards to verify that the authentication flow works correctly.
- Prevent unauthorized users from manually accessing dashboards belonging to other roles.
- Configure `LOGIN_URL`, `LOGIN_REDIRECT_URL`, and `LOGOUT_REDIRECT_URL` inside `settings.py`. (Not Done)
- Test the authentication workflow using sample users from each role.
- Push the completed authentication system to GitHub.

### Deliverables

- Functional Login Page
- Authentication Backend
- Role-Based Routing System
- Session Management
- Logout Functionality
- Protected Views
- Placeholder Dashboards for all user roles

### Success Criteria

- Users can successfully log in using their credentials.
- Users are redirected to the correct interface according to their role.
- Unauthorized dashboard access is denied.
- Sessions are securely managed.
- Authentication system is fully functional and ready for Phase 5.

#### IMPORTANT NOTE:

The dashboard pages developed in this phase are temporary placeholders whose primary purpose is to verify the authentication and routing system. Their actual implementation, analytics, visualization, AI integration, and business logic will be developed in subsequent phases.

## Phase 5: Backend Development(Views) for Super Admin

Here are the agendas for this phase:

- We now create a new app call _class_session_ that ensures instructor are not put absent when they’re having off days. Each instructor will be tied to their own classes and each class will consist of its own schedule( Like Monday from 4:30 pm to 6:00 pm, saturday 11:00 pm to 12:30 pm etc). This way the system doesn’t automatically put absent for employee’s off days.
- In this new app, go to models.py and create a new model named Class_Session that consist of the following attributes:
  - session_name - Name of the course
  - day- Day of the courses each month
  - start_time - When will the course begin
  - end_time - When will the course end
  - instructor - Name of the instructor(s)
  - branch - Name of the Branch
- Configure the app in the settings.py and register the model in admin.py and change the app name to apps.class_session.
- Create class-based view for super admin that is protected using the LoginRequiredMixin. This view should handle the following logics:
  - After the user triggers this view, it should render a template called as _admin_dashboard_ that shows all the 13 branches in a table with the first column having the names of the branch, second column showing the total number of employees, third column showing the total present, the fourth column showing the total_absent, the fiifth column showing the total_leave, sixth row showing the total remote work.”
  - Each branch shown in this, when pressed should redirect to the url _admin_dashboard/{branch_name}_ that shows the complete information about that particular branch in a well-designed mannar.
  - Following informations must be included in each metrics:
    - **Attendance rate**: The total days or classes attended divided by total possible days, shown as a percentage.
    - **Absenteeism rate**: The total days missed divided by total work days, which highlights missing time.
    - **Tardiness rate**: The number of times a person arrives late or leaves early.
    - **Attendance frequency patterns**: Tracking which days of the week or months have the most absences.**Consecutive absences**: Counting back-to-back missed days to spot major issues early.
  - **NOTE THAT THE INFORMATION NEEDED TO PROVIDE IN THE DASHBOARD MAY BE SUBJECTED TO CHANGE IN THE FUTURE. THIS IS JUST FOR EARLY DASHBOARD VERSION.**
  - Develop a clean user interface for this view(Let AI Handle the front end).
  - Configure the settings and push to github.
  ## Phase 6: Attendance Check-In System
  - Since the log in page is already finsihed with role-based access(Super Admin Dashboard has been finished as well) we now add the check in page for branch manager and employees to add their attendance
    - Here are the agendas for this phase:
      - Go to views.py in authentication app and create a new function based view called attendance_check_in. Inside this function, render the form and get the latitude and longitude from the user via javascript from the frontend(Not yet built).
      - Create a new file called haversion_algo.py under a new directory called utils in authenticaion app.
      - In that new file, create a function called dist_check with two parameter that calculates the haversion distance between each of the branch’s location and the user location and stores it inside an numpy array for memory efficieny.
      - Then Take the least distance using np.min() from all the calculated distance and compare it with the geofencing_radius distance that is stored inside the database table under the Branch Model. If the distance exceeds, return an unsuccessful message to the view and rerender the check in page again. However if the distance doesn’t exceed the geofencing radius(Which is in meter by the way), return a success message and redirect them to their dashboard based on their role.(This will already be done when the user are logging in).
      - Then add the frontend by the help of AI that creates a check in button along with beautiful design and the company name(AREA Academy). This frontend should ask location permission and get the latitude and longitude of the user’s device by a precision of 6 decimals at max and send it back to the back end view as mentioned above.
      - Let AI decide what to do with the LocationForm here. See if this is required for anything.
      - Finsih up the final touches and push to github
  ## Phase 7: Optimizing Backend For Attendance Status
  - Now that the attendance Check in System Works. We try to optimze our backend to better meet our company’s need.
  - Here is the problem we must face:
    - Since there are many employees across all branch that work at different time and different days, we cannot simply let people coming after 9:10 AM consider as late.
    - Therefore, we created another app in our project called as class_session. This class session stores and handles all business logic related to timing of all the class sessions, the particular instructor for each class and the branch names.
    - This app is particularly useful in the following ways:
      This app allows us to know which employee belongs to which class in which time at which branch. This way, when a branch manager(They teach as well) or employee checks into the attendance system, the backend will get the branch of the person who checked in, filter with AND operator to check if a class exist (We filter by the username who logged in and the branch they are in). For simplicity right now we may assume that each person has only one class that particular day. If the class exist, we get the start time of that exact class, compare it with the time the check in was finished. Then if check in time is on or before their scheduled time+10minutes, then they may put as present. However if no attendance was made that particular day when the employee was supposed to come, they may be put as absent.
  - Therefore we must do the following in our code:
    1. Prepopulate a dummy data for class_session.
    2. Get the time when the gps location reached the backend using the utils module in django.
    3. Inside the views.py run a function called as status_check()
    4. Inside apps/authentication/service/attendance_status_service.py create a function called as status_check with the parameters: user_check_in_time, user_branch, username.
    5. In the function, include all the filtering process to get the exact time of the class that user(Employee or Branch Manager) Belong to. Then find the time difference and based on the time difference, return a status back in the view function.
    6. Put the returned status inside the attendance model (Attendance) with column named as status.
    7. Push to Github
