from django.core.management.base import BaseCommand
from mainapp.logging_utils import log_manager
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Archives the current session log to the global log and clears the session log'

    def handle(self, *args, **options):
        try:
            # Archive the current session log
            log_manager.archive_session_log()
            
            # Create a backup of the global log if it's getting too large
            global_log_path = log_manager.global_log_path
            if os.path.exists(global_log_path):
                file_size = os.path.getsize(global_log_path)
                if file_size > 10 * 1024 * 1024:  # If larger than 10MB
                    # Create a backup with timestamp
                    backup_path = f"{global_log_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                    os.rename(global_log_path, backup_path)
                    self.stdout.write(self.style.SUCCESS(f'Created backup of global log: {backup_path}'))
            
            self.stdout.write(self.style.SUCCESS('Successfully archived logs'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error archiving logs: {str(e)}')) 