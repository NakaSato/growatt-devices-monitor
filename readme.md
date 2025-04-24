# Growatt Devices Monitor

A web application for monitoring Growatt solar devices and energy production.

## Setup

### Prerequisites

- Python 3.7+
- Node.js 14+ and npm

### Installation

1. Clone the repository

   ```
   git clone <repository-url>
   cd growatt-devices-monitor
   ```

2. Set up Python environment

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install Node.js dependencies

   ```
   npm install
   ```

4. Build the CSS
   ```
   npm run build:css
   ```

### Development

Run the development server:

```
flask run
```

Watch for CSS changes:

```
npm run watch:css
```

Or run both simultaneously:

```
npm run dev & flask run
```

## Features

- Real-time monitoring of solar energy production
- Device status tracking
- Energy analytics and data visualization
- Weather data integration
- Interactive maps of solar installations

## Technology Stack

- Flask (Python web framework)
- Tailwind CSS (Utility-first CSS framework)
- Alpine.js (JavaScript framework)
- Chart.js (JavaScript charting library)
