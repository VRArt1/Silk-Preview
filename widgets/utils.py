def center_to_parent(dialog, parent):
    """Center dialog window to its parent, hiding it during repositioning."""
    dialog.withdraw()
    dialog.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_w = parent.winfo_width()
    parent_h = parent.winfo_height()
    
    dialog_w = dialog.winfo_width()
    dialog_h = dialog.winfo_height()
    
    center_x = parent_x + (parent_w - dialog_w) // 2
    center_y = parent_y + (parent_h - dialog_h) // 2
    
    dialog.geometry(f"{dialog_w}x{dialog_h}+{center_x}+{center_y}")
    dialog.deiconify()
