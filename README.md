# BrightHaven — Smart Home Automation System
## Complete Flask + ESP8266 + Blynk Project (Redesigned)

---

## 📁 Project Structure

```
brighthaven/
├── app.py                          # Main Flask application (all routes & blueprints)
├── run.sh                          # Auto-start script (MariaDB + Flask + Chrome)
├── static/
│   ├── css/
│   │   ├── styles.css              # Public pages (login, signup, contact)
│   │   ├── user.css                # User dashboard & room pages
│   │   └── admin.css               # Admin panel
│   ├── js/
│   │   └── main.js                 # Sidebar, toast notifications, device toggles
│   └── images/
│       ├── pr1.png                 # BrightHaven logo
│       ├── pr11.png
│       ├── pr111.png
│       └── logo.png
└── templates/
    ├── base.html                   # Public base layout (navbar + footer)
    ├── login.html                  # Login page with animated loader
    ├── signup.html                 # Registration page
    ├── forgot_password.html        # Password reset request
    ├── contact_us.html             # Contact form
    ├── users/
    │   ├── user_base.html          # User sidebar layout
    │   ├── dashboard.html          # User dashboard (room cards + stats)
    │   ├── room.html               # Generic room page (all 5 rooms use this)
    │   ├── main_switch.html        # Master room control
    │   ├── profile.html            # User profile management
    │   ├── notifications.html      # Notifications list
    │   ├── reset_credentials.html  # Change password
    │   └── search_results.html     # Device search results
    ├── admin/
    │   ├── admin_base.html         # Admin sidebar layout
    │   ├── dashboard.html          # Admin overview + charts
    │   ├── user_management.html    # Manage all users
    │   ├── device_management.html  # View/control all devices by room
    │   ├── logs.html               # Full activity log
    │   ├── notifications.html      # Contact requests
    │   ├── reports.html            # System reports & analytics
    │   ├── settings.html           # System configuration
    │   ├── monitoring.html         # Real-time CPU/memory charts
    │   ├── privacy.html            # Privacy & Terms
    │   ├── profile.html            # Admin profile
    │   ├── reset_credentials.html  # Admin password change
    │   └── search_results.html     # User search
    └── errors/
        ├── 404.html
        └── 500.html
```

---

## 🚀 Setup & Run

### 1. Install Requirements
```bash
pip install flask pymysql requests --break-system-packages
```

### 2. Setup Database
```sql
CREATE DATABASE brighthaven CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
App auto-creates all tables and default admin on first run.

**Default Admin Login:**
- Username: `admin`
- Password: `admin123`

### 3. Configure Blynk
In `app.py`, update:
```python
BLYNK_TOKEN = "your_blynk_token_here"
```

### 4. Run
```bash
# Easy way:
chmod +x run.sh && ./run.sh

# Manual:
python app.py
```
Open: `http://127.0.0.1:5000`

---

## 🔌 Blynk Virtual Pin Mapping

| Device              | Pin | Room       |
|---------------------|-----|------------|
| Main Fan            | V0  | Main Room  |
| Main Light          | V1  | Main Room  |
| Main TV             | V2  | Main Room  |
| Main AC             | V3  | Main Room  |
| Bedroom 1 Light     | V4  | Bedroom 1  |
| Bedroom 1 Fan       | V5  | Bedroom 1  |
| Bedroom 1 AC        | V6  | Bedroom 1  |
| Bedroom 1 TV        | V7  | Bedroom 1  |
| Bedroom 1 Geyser    | V8  | Bedroom 1  |
| Bedroom 2 Light     | V9  | Bedroom 2  |
| Bedroom 2 Fan       | V10 | Bedroom 2  |
| Bedroom 2 AC        | V11 | Bedroom 2  |
| Bedroom 2 TV        | V12 | Bedroom 2  |
| Bedroom 2 Geyser    | V13 | Bedroom 2  |
| Bedroom 3 Light     | V14 | Bedroom 3  |
| Bedroom 3 Fan       | V15 | Bedroom 3  |
| Bedroom 3 AC        | V16 | Bedroom 3  |
| Bedroom 3 TV        | V17 | Bedroom 3  |
| Bedroom 3 Geyser    | V18 | Bedroom 3  |
| Kitchen Light       | V19 | Kitchen    |
| Kitchen Fan         | V20 | Kitchen    |
| Exhaust Fan         | V21 | Kitchen    |
| Microwave           | V22 | Kitchen    |
| Refrigerator        | V23 | Kitchen    |

---

## 🌐 API Endpoints

| Method | Endpoint                  | Description               |
|--------|---------------------------|---------------------------|
| POST   | `/user/api/toggle`        | Toggle single device      |
| POST   | `/user/api/toggle-room`   | Toggle all devices in room|
| POST   | `/user/api/toggle-all`    | Toggle all devices        |
| GET    | `/user/api/status`        | Get all device statuses   |
| GET    | `/esp/status`             | ESP status (public)       |

---

## 🎨 Design System

- **Colors:** Teal (`#416c6f`) + Gold (`#d4af37`) + Dark (`#0f1419`)
- **Fonts:** Playfair Display (headings) + DM Sans (body)
- **Style:** Dark glassmorphism with gradient backgrounds
- **Framework:** Bootstrap Icons + custom CSS (no Bootstrap dependency)

---

## 🔑 ESP8266 Arduino Setup

Flash your ESP8266 with the Blynk sketch:
```cpp
#define BLYNK_TEMPLATE_ID "TMPL3gDnG4aoL"
#define BLYNK_TEMPLATE_NAME "BrightHaven"
#define BLYNK_AUTH_TOKEN "oMNgTLLthFy33ccjd-3A9fG4889eXd-_"

// V0 = Relay 1 (Main Fan)
// V1 = Relay 2 (Main Light)
// Extend for more pins as needed
```

---

## 📝 Database Tables

- `admin` — Administrator accounts
- `users` — User accounts
- `logs` — Activity/action logs
- `contact_us` — Contact form submissions
- `notifications` — User notifications
- `settings` — System settings key-value store

---

*BrightHaven © 2026 — Smart Home by MK*
