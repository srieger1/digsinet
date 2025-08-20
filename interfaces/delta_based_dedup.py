import json
from copy import deepcopy

def calculate_delta_diff( oldData, newData):
    """Check if anything changed from the last state"""
    delta = {}
    print("OLDDATA: ", oldData)
    print()
    print("NEWDATA: ", newData)
    try:
        for idx_notif, notif in enumerate(newData.get("notification", [])):
            for idx, update in enumerate(notif.get("update", [])):
                # Create unique key for each update
                path = update.get("path")
                if path is None:
                    path_key = f"NULL_PATH_{idx}"
                else:
                    path_key = path
                
                # Get values for this specific update
                new_values = update.get("val", update.get("values", {}))
                current_values = {}
                # Get the last stored state for this path
                if "notification" in oldData:
                    if len(oldData["notification"]) > idx_notif:
                        if len(oldData["notification"][idx_notif].get("update", [])) > idx:
                            current_update = oldData["notification"][idx_notif].get("update", [])[idx]
                            current_values = current_update.get("val", current_update.get("values", {}))
                            print("CURRENT VALUES: ", current_values)
                            print()
                # Find what changed
                changes = _find_changes(new_values, current_values, path_key)
                
                
                if changes:
                    delta[path_key] = changes
                    print(f"=== CHANGES DETECTED ===")
                    print(f"Path: {path_key}")
                    for change in changes:
                        print(f"  {change}")
                    print("========================")
                else:
                    print(f"=== NO CHANGES ===")
                    print(f"Path: {path_key}")
                    print("==================")
    
    except Exception as e:
        print(f"Error processing notification: {e}")
        return delta  
    
    return delta

def _get_path_key( notification):
    """Extract the path from notification"""
    try:
        for notif in notification.get("notification", []):
            for update in notif.get("update", []):
                # Return the path even if it's None/null
                return update.get("path")
        return None
    except:
        return None

def _get_values_from_notification( notification):
    """Extract all the actual values from the notification"""
    try:
        for notif in notification.get("notification", []):
            for update in notif.get("update", []):
                return update.get("val", update.get("values", {}))
        return {}
    except:
        return {}

def _find_changes(new_values, old_values, path):
    """Find what changed between new and old values"""
    changes = []
    
    # If this is the first time seeing this path, everything is "new"
    if not old_values:
        #changes.append(f"NEW PATH: {path} (all values are new)")
        changes.append({"json_key": path, "new_value": new_values, "type": "ALLNEW"})
        return changes
    
    # Compare all fields recursively
    _compare_dict(new_values, old_values, "", changes)
    
    return changes

def _compare_dict( new_dict, old_dict, prefix, changes):
    """Recursively compare two dictionaries and find changes"""
    # Check for new or changed fields
    for key, new_value in new_dict.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if key not in old_dict:
            # changes.append(f"NEW: {full_key} = {new_value}")
            changes.append({"json_key": full_key, "new_value": new_value, "type": "NEW" })
        elif isinstance(new_value, dict) and isinstance(old_dict[key], dict):
            # Recursively compare nested dictionaries
            _compare_dict(new_value, old_dict[key], full_key, changes)
        elif new_value != old_dict[key]:
            # changes.append(f"CHANGED: {full_key} = {old_dict[key]} → {new_value}")
            changes.append({"json_key": full_key, "new_value": new_value,"old_value": old_dict[key], "type": "CHANGED" })
    
    # Check for removed fields
    for key in old_dict:
        if key not in new_dict:
            full_key = f"{prefix}.{key}" if prefix else key
            # changes.append(f"REMOVED: {full_key}")
            changes.append({"json_key": full_key, "type": "REMOVED" })