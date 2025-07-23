# Yokatlas University Scraper

A Python scraper that extracts university program data from YÖK Atlas (yokatlas.yok.gov.tr), including rankings, quotas, and score requirements for all score types.

## Features

- 📊 **Complete Data Extraction**: Scrapes all university programs with detailed information
- 🎯 **Multiple Score Types**: Supports all YÖK Atlas score types (sayısal, eşit ağırlık, sözel, dil)
- 🔄 **Resume Capability**: Can resume from where it left off if interrupted
- 💾 **Incremental Saving**: Saves data after each page to prevent data loss
- 🚀 **Optimized Performance**: Automatically sets page size to 100 items for efficiency
- 🎯  **Duplicate Prevention**: Avoids scraping already collected data
- 📱 **Browser Automation**: Uses Selenium to handle JavaScript-rendered content
- 🖥️ **Headless Mode**: Optional headless browser operation
- 📋 **Command Line Interface**: Flexible CLI with various options

## Installation

1. Make sure you have Python 3.13+ installed
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Make sure Chrome browser is installed (required for Selenium)

## Usage

### Basic Usage

Scrape universities with default settings (sayısal score type):
```bash
python main.py
```

### Advanced Usage

```bash
# Scrape specific score type
python main.py --score-type dil

# Run in headless mode (no browser window)
python main.py --headless

# Specify custom output file
python main.py --output my_universities.json

# Scrape all score types in one go
python main.py --all-types

# Combine options
python main.py --score-type ea --headless --output ea_universities.json
```

### Command Line Options

- `--score-type {say,ea,soz,dil}`: Choose score type to scrape (default: say)
  - `say`: Sayısal (Numerical)
  - `ea`: Eşit Ağırlık (Equal Weight)
  - `soz`: Sözel (Verbal)
  - `dil`: Dil (Language)

- `--output FILE`: Specify output JSON file (default: `universities_data_{score_type}.json`)
- `--headless`: Run browser in headless mode (no visible window)
- `--all-types`: Scrape all four score types sequentially

### Score Type URLs

The scraper automatically constructs URLs for different score types:
- **Sayısal (say)**: `tercih-sihirbazi-t4-tablo.php?p=say`
- **Eşit Ağırlık (ea)**: `tercih-sihirbazi-t4-tablo.php?p=ea`
- **Sözel (soz)**: `tercih-sihirbazi-t4-tablo.php?p=soz`
- **Dil (dil)**: `tercih-sihirbazi-t4-tablo.php?p=dil`

## Output Format

The scraper generates separate JSON files for each score type with the following structure:

```json
{
  "code": "203910830",
  "university_name": "KOÇ ÜNİVERSİTESİ",
  "name": "Karşılaştırmalı Edebiyat",
  "attributes": [
    "İngilizce",
    "Burslu",
    "4 Yıllık"
  ],
  "city": "İSTANBUL",
  "university_type": "Vakıf",
  "scholarship_type": "Burslu",
  "education_type": "Örgün",
  "total_quota": [
    "3+0",
    "3+0",
    "3+0",
    "3+0"
  ],
  "quota_status": "Doldu",
  "filled_quota": [
    "3",
    "3",
    "3",
    "3"
  ],
  "max_rank": [
    "215",
    "606",
    "516",
    "513"
  ],
  "min_score": [
    "536,38093",
    "503,50496",
    "521,12754",
    "519,65975"
  ],
  "score_type": "dil"
}
```

### Data Fields Explained

- **code**: Unique program identifier
- **university_name**: Name of the university
- **name**: Program/department name
- **attributes**: Program characteristics (language, scholarship status, duration)
- **city**: University location
- **university_type**: Type of university (State/Private)
- **scholarship_type**: Scholarship status
- **education_type**: Education format
- **total_quota**: Available quotas for different categories [Red, Purple, Blue, Green]
- **quota_status**: Whether quotas are filled
- **filled_quota**: Actually filled quotas for each category
- **max_rank**: Maximum rank for admission in each category
- **min_score**: Minimum score for admission in each category
- **score_type**: Type of score system used (say/ea/soz/dil)

## Quota Categories

The colored quota data represents different admission categories:
- **Red**: General quota + special categories (Genel + Okul Birincisi + Şehit-Gazi Yakını + 34 Yaş Üstü Kadın + Depremzede Aday)
- **Purple**: Alternative quota calculation
- **Blue**: Different quota type
- **Green**: Another quota variant

## Recovery and Resumption

If the scraper is interrupted:
1. The existing JSON file will be preserved
2. When restarted with the same score type, it will load existing data and continue from where it left off
3. It will skip already scraped programs to avoid duplicates

## Batch Processing

To scrape all score types and create comprehensive dataset:

```bash
# Scrape all types with progress monitoring
python main.py --all-types

# Or scrape each type separately in headless mode
python main.py --score-type say --headless
python main.py --score-type ea --headless
python main.py --score-type soz --headless
python main.py --score-type dil --headless
```

This will create four separate files:
- `universities_data_say.json`
- `universities_data_ea.json`
- `universities_data_soz.json`
- `universities_data_dil.json`

## Performance Tips

- Use `--headless` for faster scraping without GUI overhead
- Use `--all-types` to scrape all score types in one session with automatic delays
- The scraper automatically sets page size to 100 for optimal performance
- Data is saved after each page to prevent loss during long scraping sessions

## Configuration

You can modify the scraper by:
- Using command line arguments for most common options
- Editing the `YokatlasUniversityScraper` class for advanced customization
- Adjusting timeouts and delays in the respective methods
- Modifying the score type mappings for different languages

## Notes

- Each score type creates a separate output file by default
- Chrome browser will open visibly by default (use `--headless` to hide)
- Each page is saved immediately after scraping to prevent data loss
- The scraper respects rate limits with built-in delays
- When using `--all-types`, there's a 10-second delay between different score types

## Troubleshooting

- **Chrome driver issues**: The scraper automatically downloads the appropriate ChromeDriver
- **Timeout errors**: The scraper includes retry logic and will continue with the next page
- **Network issues**: Data is saved after each page, so progress is not lost
- **Permission issues**: Make sure you have write permissions in the project directory
- **Memory issues**: Use `--headless` mode for lower resource usage
- **Multiple score types**: Each score type can be scraped independently if `--all-types` fails
