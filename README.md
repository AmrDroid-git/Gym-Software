Youtube video explaining how to use the software:
https://youtu.be/YdGPt5cKwbk

# Gym Management Software

## 📌 Overview

This is a **desktop-based Gym Management System** built using **Python** and **PyQt6**, with SQLite for database storage.  
It helps gym owners manage clients, memberships, and membership plans in an intuitive and user-friendly interface.

---

## ✨ Features

- **Client Management**
  - Add, edit, view, and delete clients
  - Upload and display client pictures
  - Assign roles (Owner, Coach, Client)
- **Membership Management**
  - Add memberships for clients
  - Link memberships to predefined membership plans
  - Track membership start and end dates
  - Automatic status indicator: _Allowed to enter_ / _Not allowed_
- **Membership Plans**
  - Create, edit, and delete membership plans
  - Define plan duration (in months) and price
- **Reporting**
  - Generate income reports for a given date range
  - Show total income and list all memberships in that period
  - Export reports to PDF
- **Database**
  - SQLite-based storage
  - Simple structure with separate tables for clients, memberships, and plans
- **UI Features**
  - Resizable, full-screen capable windows
  - Minimize, maximize, and close buttons on dialogs
  - Organized interface with separate modules for each functionality

---

## 🛠️ Technologies Used

- **Language:** Python 3
- **GUI Framework:** PyQt6
- **Database:** SQLite
- **PDF Generation:** ReportLab
- **Date Handling:** dateutil

---
