# Phnom Penh Traffic Insights 🚦

A web analytics platform built with **Django 5**, **pandas**, **Bootstrap 5**, and **Chart.js** that analyzes hourly traffic volumes at intersections across Phnom Penh, Cambodia, and identifies each intersection's critical peak hour, surge ratio, and rush period.

---

## 🌟 Key Features

1. **Interactive Traffic Dashboard (`/`)**
   - **KPI Overview Cards:** Busiest intersection, overall peak hour, weekday vs. weekend average traffic comparison, and total dataset coverage.
   - **Peak-Hour Volume Bar Chart:** Every intersection is represented with its peak hourly volume, labelled directly with its peak range (e.g. `07:00-08:00`), and colored by operational period (Morning rush, Evening rush, Other). Click any bar to drill down into that intersection.
   - **Summary Metrics Table:** Detailed table with peak hour range, peak volume, average hourly volume, surge peak ratio, and direct links to profile and comparison views.

2. **Intersection Detail View (`/intersection/<id>/`)**
   - **24-Hour Volume Line Chart:** Smooth diurnal traffic profile with interactive toggles for **All Days**, **Weekday**, **Weekend**, and **Overlay** comparisons.
   - **Key Performance Table:** Peak hour, peak volume, 24-hour mean volume, peak ratio, rush period badge, and total observations.
   - **24-Hour Profile Breakdown Table:** Hourly table highlighting the exact peak hour.
   - **Quick Switcher Dropdown:** Switch instantly between intersections.

3. **Multi-Intersection Comparison (`/compare/`)**
   - Select 2 to 4 intersections to overlay their 24-hour hourly profiles on a single synchronized line chart.
   - Filter by day type (All / Weekday / Weekend).
   - Side-by-side comparative metrics table.

4. **CSV Data Upload (`/upload/`)**
   - Upload custom traffic CSV files with columns `intersection`, `timestamp`, `volume`.
   - Validates columns, handles timezone awareness, and imports rows using Django's high-speed `bulk_create`.
   - Includes sample template download and optional clean-slate replacement.

5. **Analytical Methodology (`/about/`)**
   - Mathematical formulation for peak hour: $h^* = \arg\max_{h \in [0, 23]} \bar{V}_h$.
   - Rush period taxonomies (Morning rush 06-09, Evening rush 16-19, Other).
   - Peak Ratio surge metric formula and thresholds.

6. **JSON API Endpoints**
   - `/api/peaks/`: Returns peak summary metrics for all intersections.
   - `/api/profile/<id>/?day_type=all|weekday|weekend`: Returns 24-hour volume profile.
   - `/api/compare/?ids=1,2,3&day_type=all`: Multi-series profile for comparative charts.

7. **Theme & UX**
   - Clean, modern data-dashboard styling with custom **Teal (`#2a9d8f`)** and **Coral (`#e76f51`)** accents.
   - Light and Dark mode toggle with instant persistence in `localStorage` and automatic Chart.js color synchronization.
   - **"Simulated data"** badge displayed prominently when demo data is active.

---

## 🏗️ Architecture & Technologies

- **Backend:** Python 3.11+, Django 5 (with Django app `traffic`)
- **Database:** SQLite with composite index on `(intersection, timestamp)` for sub-millisecond query performance
- **Data Analysis Engine:** `traffic/services.py` utilizing vectorized `pandas` routines strictly isolated from HTTP views
- **Frontend:** Bootstrap 5.3.3, Bootstrap Icons, Chart.js 4.4.2
- **Data Ingestion:** Custom Django management command `load_traffic`

---

## 🚀 Quickstart & Run Instructions

### 1. Clone or Open Workspace
Navigate to the project root directory:
```bash
cd "d:\Write Code\DataAnalyze\Final"
```

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Seed Demo Traffic Data
Seed the database from the included Phnom Penh dataset:
```bash
python manage.py load_traffic traffic_hourly_data.csv
```
*(Optional: add `--clear` to wipe existing records before loading: `python manage.py load_traffic traffic_hourly_data.csv --clear`)*

### 6. Run the Development Server
```bash
python manage.py runserver
```
Open your browser and navigate to:
- **Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Compare:** [http://127.0.0.1:8000/compare/](http://127.0.0.1:8000/compare/)
- **Upload:** [http://127.0.0.1:8000/upload/](http://127.0.0.1:8000/upload/)
- **Methodology:** [http://127.0.0.1:8000/about/](http://127.0.0.1:8000/about/)
- **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
  *(Default credentials: `admin` / `admin123`)*

---

## 🧪 Running Unit Tests

Run the test suite covering `peak_summary()`, `hourly_profile()`, CSV validation, and API endpoints:
```bash
python manage.py test
```

---

## 📂 Project Structure

```text
Final/
├── config/                      # Django project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py              # Configured apps, Asia/Phnom_Penh TZ, context processors
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py
├── traffic/                     # Traffic analysis Django app
│   ├── __init__.py
│   ├── admin.py                 # Admin registration for Intersection & TrafficRecord
│   ├── apps.py                  # TrafficConfig
│   ├── context_processors.py    # Demo dataset badge context processor
│   ├── forms.py                 # TrafficUploadForm with validation
│   ├── models.py                # Intersection & TrafficRecord models (with composite index)
│   ├── services.py              # Pure pandas analysis services (hourly_profile, peak_summary, kpis)
│   ├── tests.py                 # Unit tests with fixtures
│   ├── urls.py                  # App routes & API endpoints
│   ├── views.py                 # Views & JSON APIs
│   ├── management/
│   │   └── commands/
│   │       └── load_traffic.py  # Custom command: python manage.py load_traffic <csv_file>
│   └── migrations/
│       └── 0001_initial.py
├── static/
│   ├── css/
│   │   └── style.css            # Custom dashboard styles, Teal/Coral theme, Dark mode
│   └── js/
│       └── theme.js             # Theme switcher & Chart.js theme listener
├── templates/
│   ├── base.html                # Base layout with navbar, theme toggle, and simulated data badge
│   └── traffic/
│       ├── dashboard.html       # KPI cards, peak volume bar chart, summary table
│       ├── detail.html          # 24-hr line chart with weekday/weekend toggle, metrics
│       ├── compare.html         # 2-4 intersection profile overlay chart
│       ├── upload.html          # CSV file upload form & specification
│       └── about.html           # Analytical methodology & formulas
├── requirements.txt             # Python dependencies
├── traffic_hourly_data.csv      # Seed dataset for 10 Phnom Penh intersections
└── README.md
```

