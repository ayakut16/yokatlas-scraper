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

        # Handle different URL structure for TYT
        if score_type == "tyt":
            self.base_url = "https://yokatlas.yok.gov.tr/tercih-sihirbazi-t3-tablo.php"
        else:
            self.base_url = f"https://yokatlas.yok.gov.tr/tercih-sihirbazi-t4-tablo.php?p={score_type if score_type != 'soz' else 'söz'}"

        self.headless = headless
        self.driver = None
        self.scraped_codes = set()
        self.data = []

        # Score type mapping for better naming
        self.score_type_names = {
            "say": "sayısal",
            "ea": "eşit ağırlık",
            "soz": "sözel",
            "dil": "dil",
            "tyt": "TYT"
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

        # Additional options for better headless stability
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Speed up by not loading images
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # User agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        if self.headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode
            print("Running in headless mode with enhanced stability options")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)

        # Set additional timeouts for better stability
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)

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

    def click_detailed_view(self):
        """Click the 'Detaylı Görünüm' (Detailed View) button with robust fallback strategies"""
        try:
            # First, wait for the page to be fully loaded
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "mydata"))
            )

            # Additional wait for JavaScript to complete
            time.sleep(2)

            # Strategy 1: Try to find and click normally
            try:
                toggle_view_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "toggle_view"))
                )

                # Scroll to element to ensure it's visible
                self.driver.execute_script("arguments[0].scrollIntoView(true);", toggle_view_button)
                time.sleep(1)

                toggle_view_button.click()
                print("Clicked 'Detaylı Görünüm' button using normal click")

                # Wait for view to change
                time.sleep(3)
                return True

            except (TimeoutException, Exception) as e:
                print(f"Normal click failed")

                # Strategy 2: Try JavaScript click
                try:
                    button = self.driver.find_element(By.ID, "toggle_view")
                    self.driver.execute_script("arguments[0].click();", button)
                    print("Clicked 'Detaylı Görünüm' button using JavaScript")

                    # Wait for view to change
                    time.sleep(3)
                    return True

                except Exception as e:
                    print(f"JavaScript click failed: {e}")

                    # Strategy 3: Try alternative selectors
                    selectors = [
                        "input[type='button'][value*='Detaylı']",
                        "button[id='toggle_view']",
                        "*[onclick*='toggle']",
                        "input[onclick*='toggle']"
                    ]

                    for selector in selectors:
                        try:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            self.driver.execute_script("arguments[0].click();", element)
                            print(f"Clicked button using selector: {selector}")
                            time.sleep(3)
                            return True
                        except:
                            continue

                    # Strategy 4: Check if we're already in detailed view
                    try:
                        # Look for indicators that we're in detailed view
                        table = self.driver.find_element(By.ID, "mydata")
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        if len(rows) > 0:
                            first_row_cells = rows[1].find_elements(By.TAG_NAME, "td") if len(rows) > 1 else []
                            # If we have more than 10 columns, we're likely in detailed view
                            if len(first_row_cells) > 10:
                                print("Already in detailed view, continuing...")
                                return True
                    except:
                        pass

        except Exception as e:
            print(f"Error in click_detailed_view: {e}")

        # If all strategies failed, print debug info
        try:
            # Debug: Check if element exists at all
            elements = self.driver.find_elements(By.ID, "toggle_view")
            if elements:
                element = elements[0]
                print(f"Debug: Button found but not clickable. Displayed: {element.is_displayed()}, Enabled: {element.is_enabled()}")
                print(f"Debug: Button text: {element.get_attribute('value')}")
                print(f"Debug: Button location: {element.location}")
            else:
                print("Debug: Button with ID 'toggle_view' not found")

                # Look for any buttons with similar text
                buttons = self.driver.find_elements(By.XPATH, "//input[@type='button'] | //button")
                print(f"Debug: Found {len(buttons)} buttons on page")
                for i, btn in enumerate(buttons[:5]):  # Show first 5 buttons
                    try:
                        value = btn.get_attribute('value') or btn.text
                        print(f"Debug: Button {i}: '{value}' (id: {btn.get_attribute('id')})")
                    except:
                        pass

        except Exception as debug_error:
            print(f"Debug error: {debug_error}")

        print("Warning: Could not find or click 'Detaylı Görünüm' button with any strategy")
        return False

    def extract_colored_values(self, cell_html: str) -> List[str]:
        """Extract values from colored font tags (red, purple, blue, green)"""
        soup = BeautifulSoup(cell_html, 'html.parser')
        values = []

        if self.score_type == "tyt":
            # For TYT, only extract red and blue values
            colors = ['red', 'blue']
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
        else:
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

        if self.score_type == "tyt":
            # For TYT, look for attributes in font tags with color="#cc0000" (lowercase)
            font_tag = soup.find('font', {'color': '#cc0000'})
            if font_tag:
                text = font_tag.get_text(strip=True)

                # Handle both single attribute and multiple attributes cases
                if '(' in text and ')' in text:
                    # Find all parenthesized content using regex
                    matches = re.findall(r'\(([^)]+)\)', text)
                    for match in matches:
                        if match.strip():
                            attributes.append(match.strip())

        else:
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
            if self.score_type == "tyt":
                # For TYT, the program name is directly in the strong tag without an <a> tag
                return strong_tag.get_text(strip=True)
            else:
                # For other score types, look for <a> tag inside <strong>
                link = strong_tag.find('a')
                if link:
                    return link.get_text(strip=True)
        return ""

    def parse_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single table row into university data"""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")

            # Check minimum column count based on score type
            min_columns = 11 if self.score_type == "tyt" else 12
            if len(cells) < min_columns:  # Skip if not enough columns
                return None

            # Extract code from first column link (accounting for hidden control column)
            code_cell = cells[1].get_attribute('innerHTML')
            code_soup = BeautifulSoup(code_cell, 'html.parser')

            # First try to find code in direct text content (handles both normal and problem cases)
            # Get the text content and look for the first numeric sequence that looks like a code
            cell_text = code_soup.get_text(separator='|', strip=True)
            text_parts = cell_text.split('|')

            code = None
            for part in text_parts:
                part = part.strip()
                # Look for a numeric code that's at least 8 digits
                if part.isdigit() and len(part) >= 8:
                    code = part
                    break

            # If we didn't find a code in text content, try anchor tags as fallback
            if not code:
                anchor_tags = code_soup.find_all('a')
                for anchor in anchor_tags:
                    anchor_text = anchor.get_text(strip=True)
                    if anchor_text.isdigit() and len(anchor_text) >= 8:
                        code = anchor_text
                        break

            # If still no code found, skip this row
            if not code:
                return None

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
            city = cells[4].text.strip()
            university_type = cells[5].text.strip()
            scholarship_type = cells[6].text.strip()
            education_type = str(cells[7].get_attribute('innerHTML')).strip()

            # Extract quota data (colored values)
            total_quota_html = cells[8].get_attribute('innerHTML')
            total_quota = self.extract_colored_values(total_quota_html)

            if self.score_type == "tyt":
                quota_status = ""
                # Extract filled quota (colored values)
                filled_quota_html = cells[9].get_attribute('innerHTML')
                filled_quota = self.extract_colored_values(filled_quota_html)

                # Extract min score (colored values)
                min_score_html = cells[10].get_attribute('innerHTML')
                min_score = self.extract_colored_values(min_score_html)

                # Extract max rank (colored values)
                max_rank_html = cells[11].get_attribute('innerHTML')
                max_rank = self.extract_colored_values(max_rank_html)

            else:
                quota_status = str(cells[9].get_attribute('innerHTML')).strip()

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
            next_button = self.driver.find_element(By.CSS_SELECTOR, "li.paginate_button.next:not(.disabled) a")
            return True
        except NoSuchElementException:
            return False

    def go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.paginate_button.next:not(.disabled) a"))
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

            # Wait for the page to fully load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "mydata"))
            )
            print("Page loaded successfully")

            # Additional wait for JavaScript to complete
            time.sleep(3)

            # Set page length to 100
            if not self.set_page_length_to_100():
                print("Warning: Could not set page length to 100")
            else:
                # Wait for the table to refresh after changing page length
                time.sleep(5)

            # Click detailed view button
            detailed_view_success = self.click_detailed_view()
            if not detailed_view_success:
                print("Warning: Could not click detailed view button, continuing with current view")
                # Check if we can still scrape data
                try:
                    test_scrape = self.scrape_current_page()
                    if test_scrape == 0:
                        print("Error: Cannot scrape data in current view. Stopping.")
                        return
                    else:
                        print(f"Successfully scraped {test_scrape} records without detailed view")
                        # Reset data since we used test scrape
                        if test_scrape > 0:
                            self.data = self.data[:-test_scrape]
                            self.scraped_codes = {item['code'] for item in self.data}
                except Exception as e:
                    print(f"Error: Cannot scrape data - {e}")
                    return

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
        choices=['say', 'ea', 'soz', 'dil', 'tyt'],
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
        for score_type in ['say', 'ea', 'soz', 'dil', 'tyt']:
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
            if score_type != 'tyt':  # Don't delay after last type
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
