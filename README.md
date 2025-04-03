# DSA Project Scraper

A powerful web scraping application designed to collect and analyze project data from the Division of the State Architect (DSA) website. Built with Streamlit and featuring MMPV Design branding.

## Features

- **District Data Collection**: Comprehensive database of all California school districts
- **Project Information Scraping**: Collects detailed project information including:
  - Project Links
  - DSA Application IDs
  - Project Names and Scopes
  - Certification Types
  - Project Types
  - Final Project Costs
  - Approval Dates
  - Addresses and Cities

- **User-Friendly Interface**:
  - County and District selection dropdowns
  - "Select All" functionality for districts
  - Real-time progress tracking
  - Configurable request delays
  - Optional proxy support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Steveclare/DSA2.0.git
cd DSA2.0
```

2. Create and activate a conda environment:
```bash
conda create -n jim2 python=3.9
conda activate jim2
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
conda activate jim2
streamlit run app.py
```

2. In the web interface:
   - Select a county from the dropdown
   - Choose specific districts or use "Select All"
   - Configure request delay if needed
   - Click "Start Scraping" to begin data collection

3. Results:
   - Data is saved to CSV files with timestamp and district codes
   - Download option available in the interface
   - Real-time progress updates during scraping

## Output Format

The scraper generates CSV files with the following naming convention:
```
dsa_projects_[district_codes]_[timestamp].csv
```

Example: `dsa_projects_360_3672_3663_20250402_233047.csv`

## Error Handling

- Comprehensive error logging
- Automatic retries for failed requests
- User-friendly error messages in the interface
- Detailed logging to `app.log`

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)

## Credits

Developed by MMPV Design 