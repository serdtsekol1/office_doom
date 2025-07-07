import json
import os
from datetime import datetime

# Default values
invoices_num = 10
pricing_num = 20
correction_invoices_num = 5
new_invoices_num = None
new_pricing_num = None
new_correction_invoices_num = None
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
        'invoices_num': invoices_num,
        'pricing_num': pricing_num,
        'correction_invoices_num': correction_invoices_num,
    }
    
    try:
        with open(PERSISTENT_STORAGE_FILE, 'w') as f:
            json.dump(persistent_vars, f)
    except Exception as e:
        print(f"Error saving persistent variables: {e}")

def load_persistent_vars():
    """Load persistent variables from JSON file"""
    global invoices_last_update_at, invoices_next_update_at, global_document_update_at, invoices_num, pricing_num, correction_invoices_num
    
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
        if persistent_vars.get('invoices_num'):
            invoices_num = persistent_vars['invoices_num']
        if persistent_vars.get('pricing_num'):
            pricing_num = persistent_vars['pricing_num']
        if persistent_vars.get('correction_invoices_num'):
            correction_invoices_num = persistent_vars['correction_invoices_num']

    except Exception as e:
        print(f"Error loading persistent variables: {e}")

# Load persistent variables when module is imported
load_persistent_vars()
