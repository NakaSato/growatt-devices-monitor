# Database Report Generator

This script generates comprehensive reports from the Growatt devices monitoring database, with visualizations of device statuses and energy production. The report is saved as a PDF and can be emailed to specified recipients.

## Features

- Device status analysis with data visualizations
- Energy production data analysis (when available)
- PDF report generation with tables and plots
- Email delivery capability
- Thai language support
- Automatic report scheduling via GitHub Actions

## Requirements

- Python 3.6+
- PostgreSQL database with device data
- Required Python packages (included in project requirements.txt)

## Setup

Ensure your `.env` file has the correct configuration:

```
# Email notification settings
EMAIL_NOTIFICATIONS_ENABLED=True
EMAIL_FROM=noreply@growattmonitor.com
EMAIL_TO=your.email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=True
```

**Important Note for Gmail Users:**
If you're using Gmail as your SMTP server, you'll need to use an App Password instead of your regular Gmail password. This is especially true if you have 2-Factor Authentication enabled.

To generate an App Password:

1. Go to your Google Account at https://myaccount.google.com
2. Go to Security
3. Under "Signing in to Google", select "App passwords" (you may need to enable 2-Step Verification first)
4. Select "Mail" as the app and "Other" as the device (name it "Growatt Monitor")
5. Copy the generated 16-character password
6. Paste this password in your .env file as the SMTP_PASSWORD value

Example Gmail configuration in `.env`:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # The 16-character App Password (spaces will be removed)
SMTP_USE_TLS=True
```

Note: The App Password is a 16-character code that Google generates - it looks like 4 groups of 4 characters. You can enter it with or without spaces in your .env file.

## Usage

Run the script with:

```bash
python script/database_report.py --days 14 --email recipient@example.com
```

Parameters:

- `--days`: Number of days to include in the report (default: 7)
- `--email`: Email address to send the report to (optional, uses EMAIL_TO from .env if not specified)
- `--debug`: Enable debug logging (optional)

## Generated Reports

Reports are stored in the `reports/` directory with filenames including the timestamp, e.g., `device_report_20250511_023129.pdf`.

## Automated Reports

The system is configured to automatically generate reports using GitHub Actions. Reports are generated weekly on Monday at 8:00 AM and can be accessed from the workflow's artifacts. You can also manually trigger a report generation from the Actions tab in the GitHub repository.

## Thai Font Support

The system comes with built-in support for Thai language through the Sarabun font included in the project. If you're still seeing warnings about missing Thai character glyphs, you may need to install additional Thai font packages on your system:

- macOS: Install "Thonburi" or "Arial Unicode" fonts
- Linux: `sudo apt-get install fonts-thai-tlwg`
- Windows: Install "Arial Unicode MS" or "Tahoma" fonts

## Troubleshooting

### Database Issues

If you see errors related to missing tables, make sure the database migration has been run:

```bash
python -m app.db_migration
```

### Email Issues

If emails aren't sending correctly:

1. Check your SMTP settings in .env
2. For Gmail, ensure you're using an App Password, not your regular password
3. Verify your email provider doesn't block automated emails
4. Check network settings if your machine might be behind a firewall

#### Common Gmail Error

If you see an error like: `Username and Password not accepted`, this typically means:

- You're using your regular Gmail password instead of an App Password
- The App Password was entered incorrectly (make sure to copy the full 16 characters without spaces)
- Your Google Account security settings have changed and you need to generate a new App Password

For detailed troubleshooting:

1. Check the logs for specific authentication errors
2. Verify 2FA is enabled on your Google Account
3. Try generating a new App Password
4. Make sure you're not using a Google Workspace account with restricted App Password functionality
5. Verify SMTP_USERNAME exactly matches your Gmail account

- You haven't enabled "Less secure app access" (if not using 2FA)
- Your account has security restrictions that prevent API access

### Font Issues

Thai character warnings can be safely ignored if the PDF report is still readable. The system will try multiple fonts to ensure text is displayed properly.
