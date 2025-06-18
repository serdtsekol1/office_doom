import json
import os
from datetime import datetime

# Default values
Failsafe_flag = False
invoices_being_updated = False
invoices_last_update_at = None
invoices_next_update_at = None
global_document_update_at = None
init = False
debug = True
log_filename = None  # Назва поточного лог файлу

# File to store persistent values
PERSISTENT_STORAGE_FILE = 'persistent_vars.json'

def save_persistent_vars():
    """Save persistent variables to JSON file"""
    persistent_vars = {
        'invoices_last_update_at': invoices_last_update_at.isoformat() if invoices_last_update_at else None,
        'invoices_next_update_at': invoices_next_update_at.isoformat() if invoices_next_update_at else None,
        'global_document_update_at': global_document_update_at.isoformat() if global_document_update_at else None,
    }
    
    try:
        with open(PERSISTENT_STORAGE_FILE, 'w') as f:
            json.dump(persistent_vars, f)
    except Exception as e:
        print(f"Error saving persistent variables: {e}")

def load_persistent_vars():
    """Load persistent variables from JSON file"""
    global invoices_last_update_at, invoices_next_update_at, global_document_update_at
    
    if not os.path.exists(PERSISTENT_STORAGE_FILE):
        return
        
    try:
        with open(PERSISTENT_STORAGE_FILE, 'r') as f:
            persistent_vars = json.load(f)
            
        if persistent_vars.get('invoices_last_update_at'):
            invoices_last_update_at = datetime.fromisoformat(persistent_vars['invoices_last_update_at'])
        if persistent_vars.get('invoices_next_update_at'):
            invoices_next_update_at = datetime.fromisoformat(persistent_vars['invoices_next_update_at'])
        if persistent_vars.get('global_document_update_at'):
            global_document_update_at = datetime.fromisoformat(persistent_vars['global_document_update_at'])

    except Exception as e:
        print(f"Error loading persistent variables: {e}")

# Load persistent variables when module is imported
load_persistent_vars()
