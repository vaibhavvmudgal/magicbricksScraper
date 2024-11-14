import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import os
import streamlit as st
from io import BytesIO

# Set up logging configuration
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(filename="logs/scraper.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_error(e):
    logging.error(f"An error occurred: {e}")

# Fetch HTML content from the website
def fetch_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        log_error(f"Failed to fetch page: {response.status_code}")
        return None

# Parse HTML content with BeautifulSoup
def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    properties = []

    # Selector based on MagicBricks' structure - inspect elements carefully
    listings = soup.find_all('div', class_='mb-srp__list')

    for listing in listings:
        try:
            # Location: Extract the part after 'in' from the title attribute
            property_title = listing.find('h2', class_='mb-srp__card--title')
            property_title_text = property_title.get('title') if property_title else ""
            location = property_title_text.split(" in ")[-1] if " in " in property_title_text else "Location Not Available"
            
            # Extracting the property type from between 'BHK' and 'for'
            property_type = "Property Type Not Available"
            if "BHK" in property_title_text and "for" in property_title_text:
                start_index = property_title_text.find("BHK") + 3  # Start just after "BHK"
                end_index = property_title_text.find("for")  # End just before "for"
                property_type = property_title_text[start_index:end_index].strip()

            # Price (using the price amount from 'mb-srp__card__price--amount')
            price = listing.find('div', class_='mb-srp__card__price--amount')
            price = price.get_text(strip=True) if price else "Price Not Available"
            
            # Size (Using the Carpet Area data from 'mb-srp__card__summary__list--item')
            size = listing.find('div', class_='mb-srp__card__summary__list--item', attrs={'data-summary': 'carpet-area'})
            size = size.find('div', class_='mb-srp__card__summary--value').get_text(strip=True) if size else "Size Not Available"
            
            # Bedrooms (The property title contains the number of bedrooms)
            bedrooms = property_title_text.split(' ')[0] if property_title_text else "Bedrooms Not Available"
            
            # Sold By (Using the seller's name from 'mb-srp__card__ads__info--name')
            sold_by = listing.find('div', class_='mb-srp__card__ads__info--name')
            sold_by = sold_by.get_text(strip=True) if sold_by else "Sold By Not Available"

            # Append the data to the properties list
            properties.append({
                "location": location,
                "price": price,
                "property_type": property_type,
                "size": size,
                "bedrooms": bedrooms,
                "sold_by": sold_by
            })
        except AttributeError as e:
            log_error(f"Failed to parse listing: {e}")

    return properties

# Convert data to Excel format and return a downloadable link
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Properties')
    output.seek(0)
    return output.getvalue()

# Streamlit app settings and layout
st.set_page_config(
    page_title="Real Estate Web Scraper",
    page_icon="🏡",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Add custom CSS for styling
st.markdown(
    """
    <style>
    body {
        background-color: #f0f2f6;
        font-family: 'Segoe UI', sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .header-title {
        font-size: 48px;
        color: #FF5733;
        font-weight: bold;
        text-align: center;
    }
    .sub-header {
        font-size: 24px;
        color: #333;
        text-align: center;
        margin-bottom: 20px;
    }
    .css-1oe6wy4 {
        justify-content: center;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit interface
st.markdown('<div class="header-title">🏡 MagicBricks Web Scraper 🏡</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Scrape property data easily from MagicBricks</div>', unsafe_allow_html=True)

# URL input
url = st.text_input("Enter URL of the real estate page:")

# "Get Data" button
if st.button("Get Data"):
    if url:
        html = fetch_html(url)
        if html:
            properties = parse_page(html)
            if properties:
                df = pd.DataFrame(properties)
                st.write("### Scraped Property Data")
                st.dataframe(df)

                # Store data in session state for download
                st.session_state['data'] = df
            else:
                st.error("No properties found or parsed. Check selectors.")
        else:
            st.error("Failed to retrieve the HTML content.")
    else:
        st.warning("Please enter a valid URL.")

# "Download" button
if 'data' in st.session_state and st.session_state['data'] is not None:
    df = st.session_state['data']
    excel_data = to_excel(df)
    st.download_button(
        label="📥 Download data as Excel",
        data=excel_data,
        file_name='properties_data.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
