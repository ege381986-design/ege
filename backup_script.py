import os
import subprocess
from datetime import datetime

def backup_database():
    """Railway PostgreSQL backup"""
    if os.environ.get('DATABASE_URL'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_{timestamp}.sql"
        
        subprocess.run([
            'pg_dump', 
            os.environ.get('DATABASE_URL'),
            '-f', backup_file
        ])
        print(f"Backup created: {backup_file}")

if __name__ == '__main__':
    backup_database() 