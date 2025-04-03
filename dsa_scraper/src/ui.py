import streamlit as st
import pandas as pd
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import os
import json
import logging
from .scraper import DSAScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperUI:
    def __init__(self):
        self.scraper = DSAScraper(base_url="https://www.apps2.dgs.ca.gov/dsa/tracker/")
        self.data = []
        self.region_data = {}
        
    def setup_page(self):
        """Configure the Streamlit page."""
        st.set_page_config(
            page_title="DSA Project Scraper",
            page_icon="🏗️",
            layout="wide"
        )
        st.title("DSA Project Scraper")
        st.markdown("""
        This application scrapes project data from the DSA website, including neighboring regions to San Diego.
        Use the controls below to start scraping and analyze the results.
        """)

    def show_controls(self):
        """Display control elements."""
        with st.sidebar:
            st.header("Controls")
            client_id = st.text_input("Client ID (optional)", value="")
            use_proxy = st.checkbox("Use Proxy", value=False)
            
            if st.button("Start Scraping"):
                self.start_scraping(client_id, use_proxy)

    def start_scraping(self, client_id: str, use_proxy: bool):
        """Initialize and start the scraping process."""
        try:
            self.scraper = DSAScraper(
                base_url="https://www.apps2.dgs.ca.gov/dsa/tracker/",
                client_id=client_id,
                use_proxy=use_proxy
            )
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(info: Dict):
                if info['status'] == 'processing':
                    status_text.text(f"Processing region: {info['region']}")
                    # Update progress based on regions processed
                    progress = min(info.get('regions_processed', 0) / 20, 1.0)  # Assuming max 20 regions
                    progress_bar.progress(progress)
                elif info['status'] == 'completed':
                    progress_bar.progress(1.0)
                    status_text.text("Scraping completed!")
            
            self.data = self.scraper.get_project_list(callback=update_progress)
            self.region_data = self.organize_by_region()
            
            st.success(f"Successfully scraped {len(self.data)} projects from {len(self.region_data)} regions!")
            
            # Save data
            self.save_results()
            
        except Exception as e:
            st.error(f"Error during scraping: {str(e)}")
            logger.error(f"Scraping error: {str(e)}", exc_info=True)

    def organize_by_region(self) -> Dict[str, List]:
        """Organize scraped data by region."""
        regions = {}
        for project in self.data:
            region = project.get('location', 'Unknown').split(',')[0].strip()
            if region not in regions:
                regions[region] = []
            regions[region].append(project)
        return regions

    def show_results(self):
        """Display scraped results and visualizations."""
        if not self.data:
            st.warning("No data available. Please start scraping first.")
            return

        # Create tabs for different views
        tabs = st.tabs(["Overview", "Regional Analysis", "Project Details", "Raw Data"])
        
        with tabs[0]:
            self.show_overview()
            
        with tabs[1]:
            self.show_regional_analysis()
            
        with tabs[2]:
            self.show_project_details()
            
        with tabs[3]:
            self.show_raw_data()

    def show_overview(self):
        """Display overview statistics and summary visualizations."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Projects", len(self.data))
        with col2:
            st.metric("Total Regions", len(self.region_data))
        with col3:
            stats = self.scraper.get_stats()
            st.metric("Success Rate", f"{(stats['successful_requests'] / max(stats['total_requests'], 1)) * 100:.1f}%")

        # Create a map of project locations
        if self.data:
            df = pd.DataFrame(self.data)
            if 'location' in df.columns:
                st.subheader("Project Locations")
                fig = self.create_location_map(df)
                st.plotly_chart(fig, use_container_width=True)

    def show_regional_analysis(self):
        """Display regional statistics and comparisons."""
        st.subheader("Regional Analysis")
        
        # Region selection
        selected_regions = st.multiselect(
            "Select Regions to Compare",
            options=list(self.region_data.keys()),
            default=list(self.region_data.keys())[:5]
        )
        
        if selected_regions:
            # Create comparison charts
            fig = go.Figure()
            
            for region in selected_regions:
                projects = self.region_data[region]
                prices = [float(p['price'].replace('$', '').replace(',', '')) 
                         for p in projects if p.get('price')]
                
                if prices:
                    fig.add_trace(go.Box(
                        y=prices,
                        name=region,
                        boxpoints='all',
                        jitter=0.3,
                        pointpos=-1.8
                    ))
            
            fig.update_layout(
                title="Project Price Distribution by Region",
                yaxis_title="Price ($)",
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Regional statistics table
            stats_data = []
            for region in selected_regions:
                projects = self.region_data[region]
                prices = [float(p['price'].replace('$', '').replace(',', '')) 
                         for p in projects if p.get('price')]
                
                stats_data.append({
                    'Region': region,
                    'Number of Projects': len(projects),
                    'Average Price': f"${sum(prices) / len(prices):,.2f}" if prices else "N/A",
                    'Min Price': f"${min(prices):,.2f}" if prices else "N/A",
                    'Max Price': f"${max(prices):,.2f}" if prices else "N/A"
                })
            
            st.dataframe(pd.DataFrame(stats_data))

    def show_project_details(self):
        """Display detailed project information with filtering options."""
        st.subheader("Project Details")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            price_range = st.slider(
                "Price Range",
                min_value=0,
                max_value=int(max([float(p['price'].replace('$', '').replace(',', '')) 
                                 for p in self.data if p.get('price')] or [0])),
                value=(0, int(max([float(p['price'].replace('$', '').replace(',', '')) 
                                 for p in self.data if p.get('price')] or [0]))),
                step=1000
            )
        
        with col2:
            selected_region = st.selectbox(
                "Filter by Region",
                options=["All"] + list(self.region_data.keys())
            )
        
        # Filter data
        filtered_data = self.data
        if selected_region != "All":
            filtered_data = self.region_data[selected_region]
        
        filtered_data = [
            p for p in filtered_data
            if p.get('price') and
            price_range[0] <= float(p['price'].replace('$', '').replace(',', '')) <= price_range[1]
        ]
        
        # Display filtered projects
        for project in filtered_data:
            with st.expander(f"{project['title']} - {project['price']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Location:**", project.get('location', 'N/A'))
                    st.write("**Price:**", project.get('price', 'N/A'))
                with col2:
                    st.write("**Features:**")
                    for feature in project.get('features', []):
                        st.write(f"- {feature}")
                
                st.write("**Description:**")
                st.write(project.get('description', 'No description available.'))
                
                if project.get('contact_info'):
                    st.write("**Contact Information:**")
                    contact = project['contact_info']
                    st.write(f"Name: {contact.get('name', 'N/A')}")
                    st.write(f"Phone: {contact.get('phone', 'N/A')}")
                    st.write(f"Email: {contact.get('email', 'N/A')}")

    def show_raw_data(self):
        """Display raw data in table format."""
        st.subheader("Raw Data")
        if self.data:
            df = pd.DataFrame(self.data)
            st.dataframe(df)
            
            # Export options
            if st.button("Export to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "dsa_projects.csv",
                    "text/csv",
                    key='download-csv'
                )

    def create_location_map(self, df: pd.DataFrame) -> go.Figure:
        """Create a map visualization of project locations."""
        # This is a placeholder - you'll need to implement geocoding
        # to convert addresses to coordinates
        return go.Figure()

    def save_results(self):
        """Save scraped results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump({
                    'data': self.data,
                    'stats': self.scraper.get_stats(),
                    'timestamp': timestamp
                }, f, indent=2)
            
            st.sidebar.success(f"Results saved to {filename}")
            
        except Exception as e:
            st.sidebar.error(f"Error saving results: {str(e)}")
            logger.error(f"Error saving results: {str(e)}", exc_info=True)

def main():
    ui = ScraperUI()
    ui.setup_page()
    ui.show_controls()
    ui.show_results()

if __name__ == "__main__":
    main() 