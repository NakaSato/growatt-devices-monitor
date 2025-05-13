
import sys
from scripts.reports.database_report import main as db_report_main

# Override sys.argv to include our test arguments
sys.argv = ['database_report.py', '--email', '["enwuft@gmail.com"]']

# Run the main function
sys.exit(db_report_main())
