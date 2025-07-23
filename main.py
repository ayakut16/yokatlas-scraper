import json
import time
import os
import re
import argparse
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class YokatlasUniversityScraper:
    def __init__(self, score_type: str = "say", output_file: Optional[str] = None, headless: bool = False):
        self.score_type = score_type
        self.output_file = output_file or f"universities_data_{score_type}.json"
        self.base_url = f"https://yokatlas.yok.gov.tr/tercih-sihirbazi-t4-tablo.php?p={score_type}"
        self.headless = headless
        self.driver = None
        self.scraped_codes = set()
        self.data = []

        # Score type mapping for better naming
        self.score_type_names = {
            "say": "sayısal",
            "ea": "eşit ağırlık",
            "soz": "sözel",
            "dil": "dil"
        }

        # Load existing data if file exists
        self.load_existing_data()

    def load_existing_data(self):
        """Load existing scraped data to avoid duplicates and enable resuming"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    self.scraped_codes = {item['code'] for item in self.data}
                    print(f"Loaded {len(self.data)} existing records for {self.score_type_names.get(self.score_type, self.score_type)} score type")
            except (json.JSONDecodeError, KeyError):
                print("Could not load existing data, starting fresh")
                self.data = []
                self.scraped_codes = set()

    def save_data(self):
        """Save current data to JSON file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.data)} records to {self.output_file}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")

        if self.headless:
            chrome_options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)

    def set_page_length_to_100(self):
        """Set the page length dropdown to 100 items"""
        try:
            # Wait for the page length dropdown to be present
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "mydata_length"))
            )

            # Select 100 from dropdown
            select = Select(dropdown_element)
            select.select_by_value("100")

            # Wait for table to reload
            time.sleep(3)
            print("Set page length to 100 items")
            return True

        except TimeoutException:
            print("Could not find page length dropdown")
            return False

    def extract_colored_values(self, cell_html: str) -> List[str]:
        """Extract values from colored font tags (red, purple, blue, green)"""
        soup = BeautifulSoup(cell_html, 'html.parser')
        values = []

        # Look for font tags with color attributes in order: red, purple, blue, green
        colors = ['red', 'purple', 'blue', 'green']
        for color in colors:
            font_tag = soup.find('font', {'color': color})
            if font_tag:
                # Clean up the text to remove extra formatting
                text = font_tag.get_text(strip=True)
                # Remove parentheses content for filled quota (like "8(6+0+1+0+1)" -> "8")
                if '(' in text and ')' in text:
                    text = text.split('(')[0]
                values.append(text)
            else:
                values.append("")

        return values

    def parse_attributes(self, program_cell: str) -> List[str]:
        """Parse attributes from program cell (e.g., İngilizce, Burslu, 4 Yıllık)"""
        soup = BeautifulSoup(program_cell, 'html.parser')
        attributes = []

        # Find the font tag with color="#CC0000" that contains attributes
        font_tag = soup.find('font', {'color': '#CC0000'})
        if font_tag:
            text = font_tag.get_text(strip=True)
            # Remove parentheses and split by ) (
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]  # Remove outer parentheses
                # Split by ) ( pattern
                parts = re.split(r'\)\s*\(', text)
                attributes = [part.strip() for part in parts if part.strip()]

        return attributes

    def extract_university_and_faculty(self, university_cell: str) -> str:
        """Extract university name from the university cell"""
        soup = BeautifulSoup(university_cell, 'html.parser')
        strong_tag = soup.find('strong')
        if strong_tag:
            return strong_tag.get_text(strip=True)
        return ""

    def extract_program_name(self, program_cell: str) -> str:
        """Extract program name from program cell"""
        soup = BeautifulSoup(program_cell, 'html.parser')
        # Find the strong tag with the program name
        strong_tag = soup.find('strong')
        if strong_tag:
            link = strong_tag.find('a')
            if link:
                return link.get_text(strip=True)
        return ""

    def parse_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single table row into university data"""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 12:  # Skip if not enough columns
                return None

            # Extract code from first column link (accounting for hidden control column)
            code_cell = cells[1].get_attribute('innerHTML')
            code_soup = BeautifulSoup(code_cell, 'html.parser')
            code_link = code_soup.find('a')
            if not code_link:
                return None
            code = code_link.get_text(strip=True)

            # Skip if already scraped
            if code in self.scraped_codes:
                return None

            # Extract university name
            university_cell = cells[2].get_attribute('innerHTML')
            university_name = self.extract_university_and_faculty(university_cell)

            # Extract program name and attributes
            program_cell = cells[3].get_attribute('innerHTML')
            program_name = self.extract_program_name(program_cell)
            attributes = self.parse_attributes(program_cell)

            # Extract basic text fields
            city = cells[4].get_text(strip=True)
            university_type = cells[5].get_text(strip=True)
            scholarship_type = cells[6].get_text(strip=True)
            education_type = cells[7].get_text(strip=True)

            # Extract quota data (colored values)
            total_quota_html = cells[8].get_attribute('innerHTML')
            total_quota = self.extract_colored_values(total_quota_html)

            # Extract quota status
            quota_status = cells[9].get_text(strip=True)

            # Extract filled quota (colored values)
            filled_quota_html = cells[10].get_attribute('innerHTML')
            filled_quota = self.extract_colored_values(filled_quota_html)

            # Extract max rank (colored values)
            max_rank_html = cells[11].get_attribute('innerHTML')
            max_rank = self.extract_colored_values(max_rank_html)

            # Extract min score (colored values)
            min_score_html = cells[12].get_attribute('innerHTML')
            min_score = self.extract_colored_values(min_score_html)

            # Create the data structure
            university_data = {
                "code": code,
                "university_name": university_name,
                "name": program_name,
                "attributes": attributes,
                "city": city,
                "university_type": university_type,
                "scholarship_type": scholarship_type,
                "education_type": education_type,
                "total_quota": total_quota,
                "quota_status": quota_status,
                "filled_quota": filled_quota,
                "max_rank": max_rank,
                "min_score": min_score,
                "score_type": self.score_type
            }

            return university_data

        except Exception as e:
            print(f"Error parsing row: {e}")
            return None

    def scrape_current_page(self) -> int:
        """Scrape data from current page, returns number of new records"""
        try:
            # Wait for table to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mydata"))
            )

            # Find all table rows
            table = self.driver.find_element(By.ID, "mydata")
            tbody = table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            new_records = 0
            for row in rows:
                try:
                    university_data = self.parse_row(row)
                    if university_data:
                        self.data.append(university_data)
                        self.scraped_codes.add(university_data['code'])
                        new_records += 1
                        print(f"Scraped: {university_data['code']} - {university_data['name']}")
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue

            return new_records

        except Exception as e:
            print(f"Error scraping page: {e}")
            return 0

    def has_next_page(self) -> bool:
        """Check if there's a next page button available"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, "a.paginate_button.next:not(.disabled)")
            return True
        except NoSuchElementException:
            return False

    def go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paginate_button.next:not(.disabled)"))
            )
            next_button.click()

            # Wait for page to load
            time.sleep(3)
            return True

        except (TimeoutException, NoSuchElementException):
            return False

    def scrape_all_pages(self):
        """Scrape all pages of data"""
        try:
            self.setup_driver()
            print(f"Loading initial page for {self.score_type_names.get(self.score_type, self.score_type)} score type...")
            print(f"URL: {self.base_url}")
            self.driver.get(self.base_url)

            # Set page length to 100
            if not self.set_page_length_to_100():
                print("Warning: Could not set page length to 100")

            page_num = 1
            total_new_records = 0

            while True:
                print(f"\nScraping page {page_num}...")

                # Scrape current page
                new_records = self.scrape_current_page()
                total_new_records += new_records

                print(f"Page {page_num}: {new_records} new records")
                print(f"Total records so far: {len(self.data)}")

                # Save data after each page
                self.save_data()

                # Check if there's a next page
                if not self.has_next_page():
                    print("No more pages available")
                    break

                # Go to next page
                if not self.go_to_next_page():
                    print("Could not navigate to next page")
                    break

                page_num += 1

                # Add a small delay between pages
                time.sleep(2)

            print(f"\nScraping completed for {self.score_type_names.get(self.score_type, self.score_type)} score type!")
            print(f"Total records: {len(self.data)}")
            print(f"New records this session: {total_new_records}")
            print(f"Data saved to: {self.output_file}")

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("Browser closed")


def main():
    parser = argparse.ArgumentParser(description='Scrape university data from YÖK Atlas')
    parser.add_argument(
        '--score-type',
        choices=['say', 'ea', 'soz', 'dil'],
        default='say',
        help='Score type to scrape (default: say)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (default: universities_data_{score_type}.json)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--all-types',
        action='store_true',
        help='Scrape all score types (say, ea, soz, dil)'
    )

    args = parser.parse_args()

    if args.all_types:
        print("Scraping all score types...")
        for score_type in ['say', 'ea', 'soz', 'dil']:
            print(f"\n{'='*50}")
            print(f"Starting scrape for {score_type} score type")
            print(f"{'='*50}")

            scraper = YokatlasUniversityScraper(
                score_type=score_type,
                output_file=args.output,
                headless=args.headless
            )
            scraper.scrape_all_pages()

            # Add delay between different score types
            if score_type != 'dil':  # Don't delay after last type
                print(f"Waiting 10 seconds before next score type...")
                time.sleep(10)
    else:
        print(f"Starting yokatlas scraper for {args.score_type} score type...")
        scraper = YokatlasUniversityScraper(
            score_type=args.score_type,
            output_file=args.output,
            headless=args.headless
        )
        scraper.scrape_all_pages()


if __name__ == "__main__":
    main()
