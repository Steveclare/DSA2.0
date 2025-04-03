# DSA Project Scraper

A Streamlit application that scrapes project data from the DSA (Division of the State Architect) website and organizes it into an Excel workbook.

## Features

- Scrapes project data from DSA website
- Organizes data into three Excel worksheets:
  1. Project List - Standard format with basic project information
  2. Financial Details - Cost information and dates for bid estimation
  3. Technical Requirements - Compliance and technical specifications
- User-friendly interface with progress tracking
- Configurable request delay to avoid rate limiting
- Optional proxy support
- Excel export with formatted columns and data

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/dsa-project-scraper.git
cd dsa-project-scraper
```

2. Install required packages:
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
   - Enter your Client ID (default: 36-67)
   - Adjust request delay if needed
   - Configure proxy settings if required
   - Click "Start Scraping"

3. Download the Excel workbook with the scraped data

## Data Structure

### Project List Tab
- Link
- DSA AppId
- PTN
- Project Name
- Project Scope
- Project Cert Type

### Financial Details Tab
- Cost information
- Important dates
- Project classification
- Location details

### Technical Requirements Tab
- Compliance information
- Safety requirements
- Special project attributes

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 