import os
import sys

def main():
    """
    Entry point to run the Streamlit app.
    """
    # Get the directory where main.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct absolute path to app.py
    app_path = os.path.join(current_dir, "ui", "app.py")
    
    # Ensure project root is in sys.path (parent of src)
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    print(f"Starting New Product Listing Fee Calculator...")
    print(f"Run command: streamlit run {app_path}")
    
    os.system(f'streamlit run "{app_path}"')

if __name__ == "__main__":
    main()
