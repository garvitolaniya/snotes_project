# File: run_extractor.py
# Location: snotes_project/run_extractor.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
import threading
from snotes_reader.sdoc_importer import SdocImporter

def extract_handwriting_data(sdocx_path):
    """Uses the s-notes-reader library to extract detailed stroke data."""
    try:
        importer = SdocImporter()
        document = importer.import_sdoc(sdocx_path)
        all_strokes = []
        for page in document.pages:
            for stroke in page.strokes:
                stroke_points = [
                    {'x': p.x, 'y': p.y, 'p': p.pressure, 't': p.timestamp} 
                    for p in stroke.points
                ]
                all_strokes.append(stroke_points)
        return all_strokes
    except Exception as e:
        # Provide more detailed error information
        import traceback
        return f"An error occurred: {e}\n\nTraceback:\n{traceback.format_exc()}"

# --- GUI Application Class ---
class FinalExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Samsung Notes Extractor")
        self.root.geometry("500x250")
        self.root.resizable(False, False)
        self.input_file_path = ""
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10), padding=5)
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("Status.TLabel", font=("Helvetica", 9))
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        select_button = ttk.Button(main_frame, text="1. Select .sdocx File", command=self.select_file)
        select_button.pack(fill=tk.X, pady=5)
        self.file_label = ttk.Label(main_frame, text="No file selected", anchor="center", wraplength=450)
        self.file_label.pack(fill=tk.X, pady=5)
        extract_button = ttk.Button(main_frame, text="2. Extract & Save Data", command=self.start_extraction)
        extract_button.pack(fill=tk.X, pady=10)
        self.status_label = ttk.Label(main_frame, text="Ready", style="Status.TLabel", anchor="center")
        self.status_label.pack(fill=tk.X, pady=10)

    def select_file(self):
        path = filedialog.askopenfilename(title="Select a Samsung Notes File", filetypes=[("Samsung Notes File", "*.sdocx"), ("All files", "*.*")])
        if path:
            self.input_file_path = path
            self.file_label.config(text=os.path.basename(path))
            self.status_label.config(text="File selected. Ready to extract.")

    def start_extraction(self):
        if not self.input_file_path:
            messagebox.showerror("Error", "Please select a file first.")
            return
        save_path = filedialog.asksaveasfilename(title="Save Extracted Data As", defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not save_path:
            self.status_label.config(text="Save operation cancelled.")
            return
        self.status_label.config(text="Processing... Please wait.")
        self.root.update_idletasks()
        thread = threading.Thread(target=self.run_extraction_logic, args=(save_path,))
        thread.start()

    def run_extraction_logic(self, save_path):
        result = extract_handwriting_data(self.input_file_path)
        if isinstance(result, list):
            if not result:
                messagebox.showwarning("Warning", "Extraction was successful, but no handwriting strokes were found in this file.")
                self.status_label.config(text="✅ Success, but no strokes found.")
                return
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4)
                self.status_label.config(text=f"✅ Success! Data saved to {os.path.basename(save_path)}")
                messagebox.showinfo("Success", "Handwriting data was successfully extracted and saved.")
            except Exception as e:
                self.status_label.config(text=f"❌ Error saving file: {e}")
                messagebox.showerror("File Error", f"Could not save the file.\n\nError: {e}")
        else:
            error_message = result if isinstance(result, str) else "Unknown error."
            self.status_label.config(text=f"❌ Extraction Failed.")
            messagebox.showerror("Extraction Error", f"Failed to parse the file.\n\nDetails: {error_message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FinalExtractorApp(root)
    root.mainloop()