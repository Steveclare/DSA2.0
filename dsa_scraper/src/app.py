import streamlit as st
from ui import ScraperUI

def main():
    """Main application entry point."""
    ui = ScraperUI()
    ui.setup_page()
    ui.show_controls()
    ui.show_results()

if __name__ == "__main__":
    main() 