# AREA Academy – Role-Based Geofenced Attendance System

A full-stack, enterprise-grade attendance verification system developed for AREA (Azerbaijan Robotics and Engineering Academy). Built with Django and PostgreSQL, the platform features multi-role access control, automated Haversine geofencing to prevent fraudulent check-ins, and dynamic analytics dashboards tailored to organizational hierarchies.

## Key Features

Multi-Role Access Control (RBAC): Custom authentication layer distinguishing between Executive Managers, Branch Managers, and General Employees.

Fraud-Proof Geofencing Check-In: Uses browser-based geolocation and the Haversine formula to compute exact distance between the employee's device and the nearest registered branch office, blocking check-ins outside the perimeter radius.

Dynamic Role-Based Dashboards: Custom analytics interfaces designed specifically for macro-trend executive oversight, branch-level operations, and individual personal logs.

Containerized Deployment: Fully dockerized environment for seamless configuration, database isolation, and production readiness.

## System Architecture & Workflow

The platform operates across three integrated operational layers:

<img src="asset/flow_chart.png" alt="Flow-Chart">

### 1. Secure Authentication Layer

Password and username authentication utilizing Django's underlying security architecture.

Validates active status and user roles upon login to determine session privileges and routing.

### 2. Geofenced Verification Engine

Upon authentication, employees are directed to the verification panel:

Captures real-time device GPS coordinates via the browser location API.

Executes backend distance calculations against company branch coordinates using the Haversine formula.

Verifies role-based attendance rules and geofence radius boundaries before logging the timestamp.

### 3. Role-Based Dashboards

<img src="asset/rbd.png" alt="RBD-Info">

### Monthly Attendance Analytics

Super admins can open Monthly Analytics from the admin dashboard to review and rank all branches. Branch managers can open the same month-by-month view for their assigned branch only. Use the month controls to browse completed months, and use the branch table filter and ranking selector to narrow the branch list.

Analytics are calculated from stored attendance records at request time; no background scheduler is required, and historical attendance is not deleted. A staff member's latest status is counted once per day. Attendance rate is the share of recorded statuses that are present, late, or remote; present and absent percentages are shown separately. Unrecorded workdays are not treated as absences. The existing branch detail dashboard shows this month's counts and rolls over automatically at the calendar-month boundary.

Time-of-day activity is grouped into morning, afternoon, and evening using the local check-in time. The system does not yet have scheduled shift assignments, so these groups indicate check-in activity rather than shift occupancy.

### Tech Stack

Backend Framework: Python / Django (MVT Architecture)

Frontend Design: Tailwind CSS (CDN/Utility-first) & HTML5 Geolocation API

Database: PostgreSQL/Supabase

Math / Algorithms: Haversine Formula (Spherical Distance Calculations)

DevOps / Environment: Neon.Tech & Render with Free Infrastructure
