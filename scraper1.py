import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

# Page config
st.set_page_config(
    page_title="DSA Project Scraper",
    layout="wide"
)

# Header
st.title("DSA Project Scraper")
st.markdown("""
#### Built by Stephen Clare | 619.977.3020
*A tool for extracting project information from the Division of State Architect (DSA) website*
""")

# Input section
st.subheader("Enter District Information")
client_id = st.text_input("DSA Client ID (e.g., 36-67)", help="Enter the DSA Client ID from the URL")

def get_project_list(client_id):
    """Get the initial list of projects for a district"""
    base_url = f"https://www.apps2.dgs.ca.gov/dsa/tracker/ProjectList.aspx?ClientId={client_id}"
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main project table
        table = soup.find('table', {'id': 'ProjectList'})
        if not table:
            return None
        
        projects = []
        rows = table.find_all('tr')[1:]  # Skip header row
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:  # Ensure we have enough columns
                link = cols[0].find('a')
                if link:
                    project = {
                        'Link': 'https://www.apps2.dgs.ca.gov' + link['href'],
                        'App ID': cols[0].text.strip(),
                        'PTN': cols[1].text.strip(),
                        'Project Name': cols[2].text.strip(),
                        'Project Scope': '',
                        'Project Cert Type': ''
                    }
                    projects.append(project)
        
        return projects
    except Exception as e:
        st.error(f"Error fetching project list: {str(e)}")
        return None

def get_project_details(url):
    """Get Project Scope and Certification Type for a single project"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Project Scope
        scope_element = soup.find('span', {'id': 'ProjectScope'})
        scope = scope_element.text.strip() if scope_element else ""
        
        # Extract Certification Type
        cert_element = soup.find('span', {'id': 'ProjectCertification'})
        cert_type = cert_element.text.strip() if cert_element else ""
        
        return {
            'Project Scope': scope,
            'Project Cert Type': cert_type
        }
    except Exception as e:
        st.warning(f"Error fetching project details: {str(e)}")
        return {
            'Project Scope': '',
            'Project Cert Type': ''
        }

if st.button("Start Scraping"):
    if not client_id:
        st.error("Please enter a DSA Client ID")
    else:
        with st.spinner("Fetching initial project list..."):
            projects = get_project_list(client_id)
            
        if projects:
            st.info(f"Found {len(projects)} projects. Starting detailed scraping...")
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process each project
            for i, project in enumerate(projects):
                status_text.text(f"Processing project {i+1} of {len(projects)}: {project['Project Name']}")
                time.sleep(1)  # Rate limiting
                
                details = get_project_details(project['Link'])
                project.update(details)
                
                # Update progress
                progress_bar.progress((i + 1) / len(projects))
            
            # Create DataFrame and download button
            df = pd.DataFrame(projects)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%m%d%y")
            filename = f"DSA_Projects_{client_id.replace('-', '')}_{timestamp}.csv"
            
            # Create download button
            st.download_button(
                label="Download CSV",
                data=df.to_csv(index=False),
                file_name=filename,
                mime="text/csv"
            )
            
            # Display preview
            st.subheader("Preview of Results")
            st.dataframe(df)