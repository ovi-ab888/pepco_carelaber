# ================================================================
# PART 1 — PAGE CONFIG + IMPORTS + THEME + PASSWORD + CONSTANTS
# ================================================================

# ---------- PAGE CONFIG (must be at top) ----------
import streamlit as st
st.set_page_config(
    page_title="PEPCO",
    page_icon="🧾",
    layout="wide"
)

# ---------- Imports ----------
import fitz  # PyMuPDF
import pandas as pd
import re
from io import StringIO
import csv as pycsv
from datetime import datetime, timedelta
import os
import requests


# ================================================================
#  LOGO & THEME
# ================================================================
LOGO_PNG = "logo.png"
LOGO_SVG = "logo.svg"

THEME_CSS = """
<style>
:root{
  --card-bg: rgba(255,255,255,.04);
  --card-br: rgba(255,255,255,.12);
  --input-bg: rgba(255,255,255,.08);
  --input-br: rgba(255,255,255,.25);
  --txt:      #E9ECF6;
  --muted:    #C2C8DF;
}

.block-container{max-width:1120px; padding-top:1rem; padding-bottom:3rem;}

h1,h2,h3{font-weight:700;}
h1{letter-spacing:.2px;} h2,h3{letter-spacing:.1px;}

section[data-testid="stFileUploader"],
div[data-testid="stDataFrameContainer"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stDataEditor"]){
  background:var(--card-bg)!important;
  border:1px solid var(--card-br)!important;
  border-radius:14px!important;
  padding:12px 14px;
  box-shadow:0 1px 8px rgba(0,0,0,.12);
}

label, .stMultiSelect label, .stSelectbox label, .stNumberInput label, .stTextInput label{
  color:var(--txt)!important; font-weight:500;
}

input, textarea{
  color:var(--txt)!important;
  background:var(--input-bg)!important;
  border-color:var(--input-br)!important;
}
input::placeholder, textarea::placeholder{
  color:var(--muted)!important; opacity:.95;
}

div[data-baseweb="select"] > div{
  background:var(--input-bg)!important;
  border-color:var(--input-br)!important;
  border-radius:12px!important;
}
div[data-baseweb="select"] input{ color:var(--txt)!important; }
div[data-baseweb="select"] svg{ opacity:.9; }

div[data-testid="stNumberInput"] input{
  color:var(--txt)!important;
  background:var(--input-bg)!important;
  border-color:var(--input-br)!important;
}

.stButton > button{
  border-radius:12px; padding:.55rem 1rem;
}

[data-testid="stTable"] td,[data-testid="stTable"] th{
  padding:.45rem .6rem;
}
</style>
"""


# ================================================================
#  PASSWORD CHECK SYSTEM
# ================================================================
def check_password():
    """Simple password gate using secrets or environment."""
    expected = None

    # Prefer streamlit secrets
    try:
        expected = st.secrets.get("app_password", None)
    except Exception:
        expected = None

    # Fallback env variable
    if expected is None:
        expected = os.environ.get("PEPCO_APP_PASSWORD")

    # If not found → error
    if expected is None:
        st.error("App password not configured. Please set 'app_password' in secrets or PEPCO_APP_PASSWORD env var.")
        return False

    # When password typed
    def _password_entered():
        if st.session_state.get("password") == expected:
            st.session_state["password_correct"] = True
            try:
                del st.session_state["password"]
            except Exception:
                pass
        else:
            st.session_state["password_correct"] = False

    # Already correct?
    if st.session_state.get("password_correct", None) is True:
        return True

    # Input box
    st.text_input("Enter Your Access Code", type="password", key="password", on_change=_password_entered)

    # Wrong
    if st.session_state.get("password_correct") is False:
        st.error("Your password Incorrect,  Please contact Mr. Ovi")

    return False


# ================================================================
#  CONSTANTS & MAPPINGS
# ================================================================
WASHING_CODES = {
    '1': '১২৩৪৫', '2': '১৪৭৮৫', '3': 'djnst', '4': 'djnpt', '5': 'djnqt',
    '6': 'djnqt', '7': 'gjnpt', '8': 'gjnpu', '9': 'gjnqt', '10': 'gjnqu',
    '11': 'ijnst', '12': 'ijnsu', '13': 'ijnpu', '14': 'ijnsv', '15': 'djnsw'
}

COLLECTION_MAPPING = {
    # ---------------- Baby Girls ----------------
    "a": {  # baby girls outerwear
        "CUTE BEAR": "MODERN 1",
        "SUMMER CHERRY": "ROMANTIC 1",
        "AUTUMN": "ROMANTIC 2",
    },

    "d_girls": {  # baby girls essentials
        "FLOWER MOUSE": "MODERN 1",
        "LITTEL FOREST": "ROMANTIC 1",
    },

    # ---------------- Baby Boys ----------------
    "b": {  # baby boys outerwear
        "DOGS&FRIENDS": "MODERN 1",
        "EXPOLORE THE MOUNTINE": "MODERN 2",
        "SUMMER FUN": "MODERN 4",
        "COOL TRIP": "CLASSIC 1",
        "COLLEGE BEARS": "CLASSIC 1",
    },

    "d": {  # baby boys essentials
        "DOGS FRIENDS": "CLASSIC 1",
        "FOREST STORY": "MODERN 1",
        "LITTLE DREAMER": "MODERN 1",
        "X-MAS": "CLASSIC 2",
    },

    # ---------------- Younger Girls ----------------
    "yg": {  # younger girls outerwear
        "PONNY_RAINBOW": "COLLECTION 1",
        "MEOW_STORY": "COLLECTION 2",
        "BTS": "COLLECTION 3",
        "COZY AUTUMN": "COLLECTION 4",
        "WINTER BALLET": "COLLECTION 5",
        "XMAS": "COLLECTION 6",
        "PARTY": "COLLECTION 7",
    },

    # ---------------- Older Girls ----------------
    "og": {  # older girls outerwear
        "TRANSITIONAL_GRAFFITI VIBES": "COLLECTION_0",
        "COOL STYLE": "COLLECTION_1",
        "COOL COLLEGE LEAGUE": "COLLECTION_2",
        "GLAMROCK GIRL": "COLLECTION_3",
        "COZYTIME": "COLLECTION_4",
        "XMAS & PARTY": "COLLECTION_5",
    },

    # ---------------- Younger Boys ----------------
    "yb": {  # younger boys outerwear
        "XXXXX_1": "COLLECTION_1",
        "XXXXX_2": "COLLECTION_2",
        "XXXXX_3": "COLLECTION_3",
        "XXXXX_4": "COLLECTION_4",
        "XXXXX_5": "COLLECTION_5",
    },

    # ---------------- Older Boys ----------------
    "ob": {  # older boys outerwear
        "STREET RACING": "COLLECTION_1",
        "CAMPUS LIFE": "COLLECTION_2",
        "DIGITAL RIDE": "COLLECTION_3",
        "XMAS": "COLLECTION_4",
    },

    # ---------------- Ladies ----------------
    "l": {  # ladies outerwear
        "XXXXX_1": "COLLECTION_1",
        "XXXXX_2": "COLLECTION_2",
        "XXXXX_3": "COLLECTION_3",
        "XXXXX_4": "COLLECTION_4",
        "XXXXX_5": "COLLECTION_5",
    },

    # ---------------- Mens ----------------
    "m": {  # mens outerwear
        "XXXXX_1": "COLLECTION_1",
        "XXXXX_2": "COLLECTION_2",
        "XXXXX_3": "COLLECTION_3",
        "XXXXX_4": "COLLECTION_4",
        "XXXXX_5": "COLLECTION_5",
    },
}


# ================================================================
# PART 2 — DATA LOADERS + HELPER FUNCTIONS
# ================================================================

# ================================================================
#  CARE LABEL LOADER (3 sheets from Google Sheet - WORKING)
# ================================================================
@st.cache_data(ttl=600)
def load_care_label_data_full():
    """Load all 3 sheets from PEPCO Care Label Google Sheet"""
    
    # Export ID (পাবলিশ করা লিংক থেকে)
    EXPORT_ID = "2PACX-1vQtV5x4B3Sf_CCIMLCfvPtSP8nYru5BMAh5Xe4wWkqcrzZqT2cRJ7JYlvaHrsXql0h9Dnqohvq2mrKM"
    
    # Sheet configuration with gids
    sheets_config = {
        "comp_instructions": {"name": "Composition Instructions", "gid": "0"},
        "composition": {"name": "Composition", "gid": "1935147264"},
        "care_instructions": {"name": "Care Instructions", "gid": "21483732"}
    }
    
    result = {}
    
    for key, config in sheets_config.items():
        try:
            # Correct CSV export URL using gid
            url = f"https://docs.google.com/spreadsheets/d/e/{EXPORT_ID}/export?format=csv&gid={config['gid']}"
            
            st.write(f"Loading: {config['name']}")  # Debug - you can remove later
            df = pd.read_csv(url)
            
            if df.empty:
                st.warning(f"⚠️ Sheet '{config['name']}' is empty")
                result[key] = pd.DataFrame()
            else:
                st.success(f"✅ Loaded '{config['name']}' - {len(df)} rows")
                result[key] = df
                
        except Exception as e:
            st.error(f"❌ Failed to load '{config['name']}': {str(e)}")
            result[key] = pd.DataFrame()
    
    return result

# ================================================================
#  PRICE DATA LOADER (Google Sheet)
# ================================================================
@st.cache_data(ttl=600)
def load_price_data():
    """Load currency price ladder from Google Sheet."""
    try:
        url = (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRdAQmBHwDEWCgmLdEdJc0HsFYpPSyERPHLwmr2tnTYU1BDWdBD6I0ZYfEDzataX0wTNhfLfnm-Te6w/"
            "pub?gid=583402611&single=true&output=csv"
        )
        df = pd.read_csv(url)

        if df.empty:
            st.error("Price data sheet is empty")
            return None

        # Convert to dictionary {currency: [values]}
        price_data = {}
        for currency in df.columns:
            price_data[currency] = df[currency].dropna().tolist()

        return price_data

    except Exception as e:
        st.error(f"Failed to load price data: {str(e)}")
        return None


# ================================================================
#  PRODUCT TRANSLATION LOADER
# ================================================================
@st.cache_data(ttl=600)
def load_product_translations():
    """Load product name translations from Google Sheet."""
    try:
        sheet_id = "1ue68TSJQQedKa7sVBB4syOc0OXJNaLS7p9vSnV52mKA"
        sheet_name = "SS26 Product_Name"
        encoded = requests.utils.quote(sheet_name)

        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded}"
        df = pd.read_csv(url)

        if df.empty:
            st.error("Loaded translations but sheet appears empty")

        return df

    except Exception as e:
        st.error(f"❌ Failed to load translations: {str(e)}")
        return pd.DataFrame()


# ================================================================
#  MATERIAL TRANSLATION LOADER
# ================================================================
@st.cache_data(ttl=600)
def load_material_translations():
    """Load material translations (AL, MK) with fallback."""
    try:
        url = (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRdAQmBHwDEWCgmLdEdJc0HsFYpPSyERPHLwmr2tnTYU1BDWdBD6I0ZYfEDzataX0wTNhfLfnm-Te6w/"
            "pub?gid=1096440227&single=true&output=csv"
        )
        df = pd.read_csv(url)

        # Empty → go fallback
        if df.empty:
            st.warning("Material translations sheet empty — using fallback.")
            raise ValueError("Empty sheet")

        material_translations = []

        for _, row in df.iterrows():
            # Material name
            name = None
            if 'Name' in row and pd.notna(row['Name']):
                name = row['Name']
            else:
                try:
                    name = row.iloc[0]
                except Exception:
                    name = None

            if not name or pd.isna(name):
                continue

            # Add AL & MK groups
            for lang in ['AL', 'MK']:
                tr = row.get(lang, "")
                tr = "" if pd.isna(tr) else tr

                material_translations.append({
                    'material': name,
                    'language': lang,
                    'translation': tr
                })

        if not material_translations:
            raise ValueError("No material rows produced")

        return pd.DataFrame(material_translations)

    except Exception as e:
        # Fallback
        st.warning(f"Could not load material translations ({e}). Using fallback.")
        fallback = [
            {'material': 'Cotton', 'language': 'AL', 'translation': 'Cotton'},
            {'material': 'Cotton', 'language': 'MK', 'translation': 'Cotton'}
        ]
        return pd.DataFrame(fallback)


# ================================================================
#  HELPER FUNCTIONS
# ================================================================

# ---------- Auto detect PLN price from PDF text ----------
def detect_pl_sales_price(full_text):
    try:
        m = re.search(r"PL\s+[^\n]*?(\d+[\.,]\d+)", full_text)
        if m:
            return m.group(1).replace(',', '.')
    except Exception:
        pass
    return None


# ---------- Format numbers (PLN, EUR, RON, etc) ----------
def format_number(value, currency):
    """Format numeric pricing based on currency."""
    try:
        if isinstance(value, str):
            value = float(value.replace(',', '.'))

        if currency in ['EUR', 'BGN', 'BAM', 'RON', 'PLN']:
            formatted = f"{float(value):,.2f}".replace(".", ",")

            if ',' in formatted:
                parts = formatted.split(',')
                parts[0] = parts[0].replace('.', '')  # remove thousand separator
                formatted = ','.join(parts)

            return formatted

        return str(int(float(value)))

    except (ValueError, TypeError):
        return str(value)


# ---------- Match PLN to price ladder ----------
def find_closest_price(pln_value):
    """Returns matching row of other currencies for the PLN price."""
    try:
        price_data = load_price_data()

        if not price_data or 'PLN' not in price_data:
            st.error("❌ Price data not available")
            return None

        pln_value = float(pln_value)
        ladder = price_data['PLN']

        if pln_value not in ladder:
            st.error(f"❌ PLN {pln_value} not found in price sheet.")
            return None

        idx = ladder.index(pln_value)

        return {
            currency: format_number(values[idx], currency)
            for currency, values in price_data.items()
            if currency != 'PLN'
        }

    except Exception as e:
        st.error(f"Invalid price value: {str(e)}")
        return None


# ---------- Classification → mapping ----------
def get_classification_type(item_class):
    """Determine class type key used in COLLECTION_MAPPING."""
    if not item_class:
        return None

    ic = item_class.lower()

    if 'younger girls outerwear' in ic:
        return 'yg'
    if 'older girls outerwear' in ic:
        return 'og'
    if 'younger boys outerwear' in ic:
        return 'yb'
    if 'older boys outerwear' in ic:
        return 'ob'
    if 'baby girls outerwear' in ic:
        return 'a'
    if 'baby boys outerwear' in ic:
        return 'b'
    if 'baby girls essentials' in ic:
        return 'd_girls'
    if 'baby boys essentials' in ic:
        return 'd'
    if 'ladies outerwear' in ic:
        return 'l'
    if 'mens outerwear' in ic:
        return 'm'

    return None


# ---------- Map Item_classification → Dept label ----------
def map_item_class_to_dept_label(item_class):
    """Map item_class text to UI Department names."""
    if not item_class:
        return None

    ic = item_class.lower()

    if 'baby boys outerwear' in ic or 'baby boys essentials' in ic:
        return "Baby Boy"
    if 'baby girls outerwear' in ic or 'baby girls essentials' in ic:
        return "Baby Girl"
    if 'younger boys outerwear' in ic or 'older boys outerwear' in ic:
        return "Boys"
    if 'younger girls outerwear' in ic or 'older girls outerwear' in ic:
        return "Girls"
    if 'ladies outerwear' in ic:
        return "Women"
    if 'mens outerwear' in ic:
        return "Mens"

    return None


# ---------- Map Item_classification → DEPT column ----------
def get_dept_value(item_class):
    """Maps classification → BABY / KIDS / TEENS / WOMEN / MEN."""
    if not item_class:
        return ""

    ic = item_class.lower()

    if any(x in ic for x in ['baby boys', 'baby girls']):
        return "BABY"
    if any(x in ic for x in ['younger boys', 'younger girls']):
        return "KIDS"
    if any(x in ic for x in ['older girls', 'older boys']):
        return "TEENS"
    if 'ladies outerwear' in ic:
        return "WOMEN"
    if 'mens outerwear' in ic:
        return "MEN"

    return ""


# ---------- Modify collection name (add B/G) ----------
def modify_collection(collection, item_class):
    """Append B/G based on gender groups."""
    if not item_class:
        return collection

    ic = item_class.lower()

    if any(x in ic for x in ['younger boys', 'older boys']):
        return f"{collection} B"

    if any(x in ic for x in ['younger girls', 'older girls']):
        return f"{collection} G"

    return collection

# ---------- Item_name_EN ----------


def clean_item_name_english(name: str) -> str:
    """
    Item_name_EN থেকে নিচের prefix গুলো বাদ দিয়ে
    বাকি অংশ CAPITAL LETTERS এ রিটার্ন করবে।
    """
    if not isinstance(name, str):
        return ""

    text = name.strip()
    lower = text.lower()

    # লম্বা phrase আগে, তারপর ছোট – যেন "baby girl basic" থাকলে
    # শুধু "baby girl" কেটে না যায়।
    prefixes = [
        "xxxxx",
        "xxxxx",
        "xxxxx",
        "xxxxx",
        "xxxxx",
        "xxxxx",
        "xxxxx",
        "xxxxx",
    ]

    for p in prefixes:
        if lower.startswith(p):
            # prefix এর দৈর্ঘ্য অনুযায়ী কাটবো
            cut_len = len(p)
            text = text[cut_len:].strip(" -_,./").strip()
            break

    # সবশেষে CAPITAL
    return text.upper()


# ================================================================
# PART 3 — PDF EXTRACTION + MATERIAL SYSTEM + TRANSLATION FORMATTER
# ================================================================
import re


# ================================================================
#  COLOUR EXTRACTION (multiple PDF layout compatible)
# ================================================================
def extract_colour_from_page2(text, page_number=1):
    """Old function: Extract colour from page2."""
    try:
        m = re.search(
            r"Colour[^\n]*?\n\s*([A-Za-z]+)\s+([0-9]{2}-[0-9]{4}[A-Za-z]*)",
            text,
            re.IGNORECASE
        )
        if m:
            colour_name = m.group(1).strip().upper()
            pantone = m.group(2).strip().upper()
            return f"{colour_name} {pantone}"
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def extract_colour_from_pdf_pages(pages_text):
    """
    Ultra-robust PEPCO Colour Detection
    Supports:
        ✔ Old 6-page PDF format
        ✔ New 5-page PDF format
        ✔ Broken layout (Colour row + size row merged)
        ✔ Missing pantone
    """
    # -------- 1️⃣ Standard Colour Table --------
    for txt in pages_text:
        m = re.search(
            r"Colour.*?\n.*?\n\s*([A-Za-z ]+)\s+[0-9]{2}-[0-9]{4}",
            txt,
            re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip().upper()

    # -------- 2️⃣ Purchase Price block --------
    for txt in pages_text:
        m2 = re.search(
            r"Purchase price.*?\n\s*([A-Za-z ]+)\s+[0-9]{2}-[0-9]{4}",
            txt,
            re.IGNORECASE | re.DOTALL
        )
        if m2:
            return m2.group(1).strip().upper()

    # -------- 3️⃣ Generic fallback using "colour" keyword --------
    for txt in pages_text:
        if "colour" in txt.lower():
            for line in txt.splitlines():
                if re.search(r"[A-Za-z ]+\s+[0-9]{2}-[0-9]{4}", line):
                    name = line.split()[0:-1]
                    if name:
                        return " ".join(name).upper()

    # -------- 4️⃣ Manual input fallback --------
    st.warning("⚠️ Colour not found in PDF. Enter colour manually:")
    manual = st.text_input("Colour (e.g. WHITE):", key="manual_colour_fix")
    return manual.strip().upper() if manual else "UNKNOWN"


# ================================================================
#  EXTRACT ORDER ID FROM PDF (for multiple uploads)
# ================================================================
def extract_order_id_only(file):
    """Extract only Order ID from a PDF file."""
    pos = None
    try:
        pos = file.tell()
    except Exception:
        pass

    try:
        file.seek(0)
    except Exception:
        pass

    try:
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            page1_text = doc[0].get_text() if len(doc) > 0 else ""
    except Exception:
        try:
            file.seek(0 if pos is None else pos)
        except Exception:
            pass
        return None

    try:
        file.seek(0 if pos is None else pos)
    except Exception:
        pass

    m = re.search(
        r"Order\s*-\s*ID\s*\.{2,}\s*([A-Z0-9_+-]+)",
        page1_text,
        re.IGNORECASE
    )
    return m.group(1).strip() if m else None


# ================================================================
#  MAIN PDF EXTRACTION ENGINE
# ================================================================
def extract_data_from_pdf(file):
    """Robust PEPCO extractor (5-page + 6-page)."""
    try:
        raw = file.read()
        if not raw:
            st.error("Empty PDF uploaded.")
            return None

        doc = fitz.open(stream=raw, filetype="pdf")

        if len(doc) < 1:
            st.error("PDF must have at least 1 page.")
            return None

        pages_text = [doc[i].get_text() for i in range(len(doc))]
        full_text = "\n".join(pages_text)
        page1 = pages_text[0]

        # ---------------- Item Name EN ----------------
        item_name_en = None

        m_item = re.search(
            r"Item\s*name\s*English\s*[:\.]{1,}\s*(.+)",
            full_text,
            re.IGNORECASE
        )
        if not m_item:
            m_item = re.search(
                r"Item\s*name\s*[:\.]{1,}\s*(.+?)\n",
                full_text,
                re.IGNORECASE
            )
        if m_item:
            item_name_en = m_item.group(1).strip()

        # ---------------- Identifiers ----------------
        merch_code = re.search(r"Merch\s*code\s*\.{2,}\s*([\w/]+)", page1)
        season = re.search(r"Season\s*\.{2,}\s*(\w+)?\s*(\d{2})", page1)
        style_code = re.search(r"\b\d{6}\b", page1)

        style_suffix = ""
        if merch_code and season:
            style_suffix = f"{merch_code.group(1).strip()}{season.group(2)}"
        elif merch_code:
            style_suffix = merch_code.group(1).strip()

        collection = re.search(r"Collection\s*\.{2,}\s*(.+)", page1)

        date_match = re.search(
            r"Handover\s*date\s*\.{2,}\s*(\d{2}/\d{2}/\d{4})",
            page1
        )

        batch = "UNKNOWN"
        if date_match:
            try:
                batch_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
                batch = (batch_date - timedelta(days=20)).strftime("%m%Y")
            except Exception:
                pass

        order_id = re.search(r"Order\s*-\s*ID\s*\.{2,}\s*(.+)", page1)
        item_class = re.search(r"Item classification\s*\.{2,}\s*(.+)", page1)
        supplier_code = re.search(r"Supplier product code\s*\.{2,}\s*(.+)", page1)
        supplier_name = re.search(r"Supplier name\s*\.{2,}\s*(.+)", page1)

        item_class_value = item_class.group(1).strip() if item_class else "UNKNOWN"

        class_type = get_classification_type(item_class_value)

        collection_value = (
            collection.group(1).split("-")[0].strip()
            if collection else "UNKNOWN"
        )

        # Collection mapping
        if class_type and class_type in COLLECTION_MAPPING:
            for orig, new in COLLECTION_MAPPING[class_type].items():
                if orig.upper() in collection_value.upper():
                    collection_value = new
                    break

        # ---------------- AUTO COLOUR EXTRACTION ----------------
        colour = extract_colour_from_pdf_pages(pages_text)

        # ---------------- SKU + BARCODE ----------------
        skus = []
        barcodes = []
        excluded = set()

        for txt in pages_text:
            skus.extend(re.findall(r"\b\d{8}\b", txt))
            barcodes.extend(re.findall(r"\b\d{13}\b", txt))
            excluded.update(re.findall(r"barcode:\s*(\d{13})", txt))

        # Dedupe
        def _dedupe(seq):
            seen = set()
            out = []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        skus = _dedupe(skus)
        barcodes = _dedupe(barcodes)

        valid_barcodes = [b for b in barcodes if b not in excluded]

        if not skus or not valid_barcodes:
            st.error("SKU or Barcode missing.")
            return None

        # Align count mismatch
        if len(skus) != len(valid_barcodes):
            min_len = min(len(skus), len(valid_barcodes))
            st.warning(
                f"SKU ({len(skus)}) and Barcode ({len(valid_barcodes)}) differ. Using first {min_len}."
            )
            skus = skus[:min_len]
            valid_barcodes = valid_barcodes[:min_len]

        season_value = (
            f"{season.group(1)}{season.group(2)}"
            if season else "UNKNOWN"
        )

        # ---------------- BUILD RESULT ----------------
        results = []
        for sku, barcode in zip(skus, valid_barcodes):
            results.append({
                "Order_ID": order_id.group(1).strip() if order_id else "UNKNOWN",
                "Style": style_code.group() if style_code else "UNKNOWN",
                "Colour": colour,
                "Supplier_product_code": supplier_code.group(1).strip() if supplier_code else "UNKNOWN",
                "Item_classification": item_class_value,
                "Supplier_name": supplier_name.group(1).strip() if supplier_name else "UNKNOWN",
                "today_date": datetime.today().strftime('%d-%m-%Y'),
                "Collection": collection_value,
                "Colour_SKU": f"{colour} • SKU {sku}",
                "Style_Merch_Season": (
                    f"STYLE {style_code.group()} • {style_suffix} • Batch No./"
                    if style_code else "STYLE UNKNOWN"
                ),
                "Batch": f"виготовлення: {batch}",
                "barcode": barcode,
                "Item_name_EN": item_name_en or "",
                "Season": season_value
            })

        return results

    except Exception as e:
        st.error(f"PDF error: {str(e)}")
        return None


# ================================================================
#  TRANSLATION FORMATTER (AL, ES, MK, etc)
# ================================================================
def format_product_translations(
    product_name,
    translation_row,
    selected_materials=None,
    material_translations=None,
    material_compositions=None
):
    """Builds multilingual product description with material info."""
    formatted = []

    # Country suffix rules
    country_suffixes = {
        'BiH': " Sastav materijala na ušivenoj etiketi.",
        'RS': " Sastav materijala nalazi se na ušivenoj etiketi.",
    }

    # EN fallback
    en_text = translation_row.get('EN', product_name)
    formatted.append(f"|EN| {en_text}")

    # ES / ES_CA combined
    combined_lang = {
        'ES': (
            f"{translation_row['ES']} / {translation_row['ES_CA']}"
            if pd.notna(translation_row.get('ES_CA'))
            else translation_row.get('ES')
        )
    }

    # Language order defined
    language_order = [
        'AL', 'BG', 'BiH', 'CZ', 'DE', 'EE',
        'ES', 'GR', 'HR', 'HU', 'IT', 'LT',
        'LV', 'MK', 'PL', 'PT', 'RO', 'RS',
        'SI', 'SK', 'UA'
    ]

    # Build translations
    for lang in language_order:
        if lang in combined_lang and combined_lang[lang] is not None:
            text = combined_lang[lang]
        else:
            text = translation_row.get(lang, product_name)

        # Material names or composition for AL + MK only
        if selected_materials and material_translations and lang in ['AL', 'MK']:
            comp = (material_compositions or {}).get(lang, "")
            names = material_translations.get(lang, "")

            if comp:
                text = f"{text}: {comp}"
            elif names:
                text = f"{text}: {names}"

        # Country suffix
        if lang in country_suffixes:
            if not text.endswith('.'):
                text += "."
            text += country_suffixes[lang]

        formatted.append(f"|{lang}| {text}")

    return " ".join(formatted)


# ================================================================
# PART 4 — MAIN PROCESSOR + UI SECTION + APP ENTRY
# ================================================================

# ================================================================
#  MAIN WORKFLOW: PDF → DataFrame → UI → CSV
# ================================================================
def process_pepco_pdf(uploaded_pdf, extra_order_ids: str | None = None):
    """Main pipeline: parse PDF, build DF, apply UI choices, export CSV."""
    # ----- Load reference data -----
    translations_df = load_product_translations()
    material_translations_df = load_material_translations()

    if not (uploaded_pdf and not translations_df.empty):
        return

    # ----- Parse PDF to structured data -----
    result_data = extract_data_from_pdf(uploaded_pdf)
    if not result_data:
        return

    df = pd.DataFrame(result_data)

    # ----- Base values from first row -----
    first_row = result_data[0] if len(result_data) > 0 else {}
    pdf_item_class = first_row.get("Item_classification", "")
    pdf_item_name_en = (first_row.get("Item_name_EN") or "").strip()

    # ----- Merge extra Order IDs from other PDFs -----
    if extra_order_ids:
        try:
            df['Order_ID'] = df['Order_ID'].astype(str) + "+" + extra_order_ids
        except Exception:
            pass

    # ============================================================
    #  UI Controls (Department, Product, Washing, PLN)
    # ============================================================
    c1, c2, c3, c4 = st.columns(4)

    # -- Department select (default from item_class) --
    depts = translations_df['DEPARTMENT'].dropna().unique().tolist()
    default_dept_label = map_item_class_to_dept_label(pdf_item_class)
    default_dept_index = 0

    if default_dept_label:
        for i, d in enumerate(depts):
            if str(d).strip().lower() == str(default_dept_label).strip().lower():
                default_dept_index = i
                break

    with c1:
        selected_dept = st.selectbox(
            "Select Department",
            options=depts,
            index=default_dept_index,
            key="ui_dept"
        )

    # -- Product list filtered by Department --
    filtered = translations_df[translations_df['DEPARTMENT'] == selected_dept]
    products = filtered['PRODUCT_NAME'].dropna().unique().tolist()

    default_product_index = 0
    if pdf_item_name_en:
        for i, p in enumerate(products):
            if str(p).strip().lower() == pdf_item_name_en.strip().lower():
                default_product_index = i
                break

    with c2:
        product_type = st.selectbox(
            "Select Product Type",
            options=products,
            index=default_product_index,
            key="ui_product"
        )

    # -- Washing code --
    washing_options = list(WASHING_CODES.keys())
    washing_default_index = washing_options.index('9') if '9' in washing_options else 0

    with c3:
        washing_code_key = st.selectbox(
            "Select Washing Code",
            options=washing_options,
            index=washing_default_index,
            key="ui_wash"
        )

    # -- PLN price manual input --
    with c4:
        pln_price_raw = st.text_input(
            "Enter PLN Price",
            key="ui_pln_price"
        )

    # ============================================================
    #  Parse PLN price
    # ============================================================
    pln_price = None
    if pln_price_raw.strip():
        try:
            pln_price = float(pln_price_raw.replace(",", "."))
            if pln_price < 0:
                st.error("❌ Price can't be negative.")
                pln_price = None
        except ValueError:
            st.error("❌ Please enter a valid number like 12.50 or 12,50")
            pln_price = None

    # ============================================================
    #  MATERIAL COMPOSITION UI
    # ============================================================
    st.markdown("### Material Composition (%)")

    # Session init
    if "mat_rows" not in st.session_state:
        st.session_state.mat_rows = 1
    if "mat_data" not in st.session_state:
        st.session_state.mat_data = [{"mat": "Cotton", "pct": 100}]

    materials_list = (
        material_translations_df['material'].dropna().unique().tolist()
        if not material_translations_df.empty else []
    )
    if "Cotton" not in materials_list:
        materials_list = ["Cotton"] + materials_list

    def _ensure_row(i):
        while i >= len(st.session_state.mat_data):
            st.session_state.mat_data.append({"mat": None, "pct": 0})

    # ------ Per-row UI ------
    for i in range(st.session_state.mat_rows):
        _ensure_row(i)

        prev_total = sum(r["pct"] for r in st.session_state.mat_data[:i] if r["pct"])
        remain = max(0, 100 - prev_total)

        cA, cB = st.columns([3, 1.3])

        # Material select
        with cA:
            cur_mat = st.session_state.mat_data[i]["mat"]
            options = ["—"] + materials_list
            idx = options.index(cur_mat) if (cur_mat in options) else 0

            st.session_state.mat_data[i]["mat"] = st.selectbox(
                "Select Material(s)" if i == 0 else f"Select Material(s) #{i+1}",
                options,
                index=idx,
                key=f"mat_sel_{i}"
            )

        # Percentage input
        with cB:
            cur_pct = st.session_state.mat_data[i]["pct"]
            default_pct = (
                100 if (i == 0 and not cur_pct and st.session_state.mat_data[i]["mat"] == "Cotton")
                else min(cur_pct, remain)
            )

            if i == 0 and st.session_state.mat_data[i]["mat"] == "Cotton" and cur_pct in (None, 0):
                default_pct = 100
                st.session_state.mat_data[i]["pct"] = 100

            st.session_state.mat_data[i]["pct"] = st.number_input(
                "Composition (%)" if i == 0 else f"Composition (%) #{i+1}",
                min_value=0,
                max_value=remain,
                step=1,
                value=default_pct,
                key=f"mat_pct_{i}"
            )

    # Valid rows
    valid_rows = [
        r for r in st.session_state.mat_data[:st.session_state.mat_rows]
        if r["mat"] not in (None, "—") and r["pct"] > 0
    ]
    running_total = sum(r["pct"] for r in valid_rows)

    # Auto-add next material row - FIXED (removed st.rerun)
    if running_total < 100 and st.session_state.mat_rows < 5:
        last = st.session_state.mat_data[st.session_state.mat_rows - 1]
        if last["mat"] not in (None, "—") and last["pct"] > 0:
            st.session_state.mat_rows += 1
            _ensure_row(st.session_state.mat_rows - 1)

    # If total >= 100 → trim extra rows visually
    if running_total >= 100 and st.session_state.mat_rows > len(valid_rows):
        st.session_state.mat_rows = len(valid_rows)

    selected_materials = [r["mat"] for r in valid_rows]

    # Cotton flag
    cotton_value = ""
    if len(valid_rows) == 1:
        mat0 = (valid_rows[0]["mat"] or "").strip().lower()
        try:
            pct0_int = int(valid_rows[0]["pct"])
        except Exception:
            pct0_int = 0

        if mat0 == "cotton" and pct0_int == 100:
            cotton_value = "Y"

    # Info about totals
    if st.session_state.mat_rows == 1 and valid_rows and valid_rows[0]["pct"] == 100 and (
        valid_rows[0]["mat"] or ""
    ).lower() == "cotton":
        st.info("✅ 100% selected")
    elif running_total > 100:
        st.error("⚠️ Total exceeds 100%")

    st.write(f"**Total: {running_total}%**")

    # ============================================================
    #  Material Translation for AL / MK
    # ============================================================
    material_trans_dict = {}
    material_compositions = {}

    if selected_materials and not material_translations_df.empty:
        for lang in ['AL', 'MK']:
            names = []
            comp = []

            for r in valid_rows:
                t = material_translations_df[
                    (material_translations_df['material'] == r['mat']) &
                    (material_translations_df['language'] == lang)
                ]
                if not t.empty:
                    tr = t['translation'].iloc[0]
                    names.append(tr)
                    comp.append(f"{r['pct']}% {tr}")

            if names:
                material_trans_dict[lang] = ", ".join(names)
            if comp:
                material_compositions[lang] = ", ".join(comp)

    # ============================================================
    #  CARE LABEL UI (With Dynamic Language Selection)
    # ============================================================
    st.markdown("### 🏷️ Care Label")
    
    care_data = load_care_label_data_full()
    
    # Initialize
    final_composition_text = ""
    care_inst_text = ""
    
    if not (care_data["comp_instructions"].empty and care_data["composition"].empty and care_data["care_instructions"].empty):
        
        # Detect available languages from first sheet's columns
        df_sample = care_data["comp_instructions"]
        if not df_sample.empty:
            # Skip first column (EN) - rest are language columns
            available_langs = df_sample.columns[1:].tolist()
        else:
            available_langs = ['EN']  # Fallback
        
        col_lang, col1, col2, col3 = st.columns([1, 2, 2, 2])
        
        with col_lang:
            # Default to first language if available
            default_idx = 0 if available_langs else 0
            care_lang = st.selectbox("Language", options=available_langs, index=default_idx, key="care_lang")
        
        with col1:
            comp_inst_options = []
            if not care_data["comp_instructions"].empty:
                en_col = care_data["comp_instructions"].columns[0]
                comp_inst_options = care_data["comp_instructions"][en_col].dropna().astype(str).tolist()
            selected_comp_inst = st.selectbox("Composition Instructions", options=[""] + comp_inst_options, key="comp_inst")
            
        with col2:
            comp_options = []
            if not care_data["composition"].empty:
                en_col = care_data["composition"].columns[0]
                comp_options = care_data["composition"][en_col].dropna().astype(str).tolist()
            selected_composition = st.selectbox("Composition", options=[""] + comp_options, key="composition")
            
        with col3:
            care_inst_options = []
            if not care_data["care_instructions"].empty:
                en_col = care_data["care_instructions"].columns[0]
                care_inst_options = care_data["care_instructions"][en_col].dropna().astype(str).tolist()
            selected_care_inst = st.selectbox("Care Instructions", options=[""] + care_inst_options, key="care_inst")
        
        def get_translation(df, en_text, lang):
            if df.empty or not en_text:
                return ""
            en_col = df.columns[0]
            row = df[df[en_col].astype(str).str.strip() == en_text]
            if not row.empty:
                if lang in df.columns:
                    return row.iloc[0][lang]
                return row.iloc[0][en_col]
            return ""
        
        comp_inst_text = get_translation(care_data["comp_instructions"], selected_comp_inst, care_lang)
        composition_text = get_translation(care_data["composition"], selected_composition, care_lang)
        care_inst_text = get_translation(care_data["care_instructions"], selected_care_inst, care_lang)
        
        # Combine
        if comp_inst_text:
            final_composition_text = comp_inst_text
        if composition_text:
            if final_composition_text:
                final_composition_text += " "
            final_composition_text += composition_text
        
        # Preview
        if final_composition_text or care_inst_text:
            with st.expander("📋 Preview"):
                if final_composition_text:
                    st.write(f"**Composition:** {final_composition_text}")
                if care_inst_text:
                    st.write(f"**Care Instructions:** {care_inst_text}")
    else:
        st.warning("⚠️ Care Label data not available from Google Sheet")
    # ============================================================
    #  PRICE LADDER + CSV EXPORT
    # ============================================================
    if pln_price is not None:
        currency_values = find_closest_price(pln_price)

        if currency_values:
            # Fill currency columns
            for cur in ['EUR', 'BGN', 'BAM', 'RON', 'CZK', 'UAH', 'MKD', 'RSD', 'HUF']:
                df[cur] = currency_values.get(cur, "")

            df['PLN'] = format_number(pln_price, 'PLN')

            # NEW COLUMN → Item name English (cleaned & CAPITAL)
            df["Item_name_English"] = df["Item_name_EN"].apply(clean_item_name_english)
            
            # NEW: Add Care Label columns to dataframe
            df['Composition'] = final_composition_text
            df['Care Instructions'] = care_inst_text

            final_cols = [
                "Order_ID", "Style", "Colour", "Supplier_product_code",
                "Item_classification", "Supplier_name", "today_date",
                "Collection", "Colour_SKU", "Style_Merch_Season",
                "Batch", "barcode", "washing_code", "EUR", "BGN",
                "BAM", "PLN", "RON", "CZK", "UAH", "MKD", "RSD", "HUF",
                "product_name", "Dept", "Item_name_English", "Season",
                "Composition", "Care Instructions"
            ]

            # Optionally include Cotton column
            if 'Cotton' in df.columns and 'Cotton' not in final_cols:
                final_cols.append("Cotton")

            # Ensure all columns exist
            for col in final_cols:
                if col not in df.columns:
                    df[col] = ""

            st.success("✅ Done!")
            st.subheader("Edit Before Download")

            edited_df = st.data_editor(df[final_cols])

            # Build CSV with ; separator & quoted fields
            csv_buffer = StringIO()
            writer = pycsv.writer(
                csv_buffer,
                delimiter=';',
                quoting=pycsv.QUOTE_ALL
            )
            writer.writerow(final_cols)

            for row in edited_df.itertuples(index=False):
                writer.writerow(row)

            # ---------- Custom CSV filename ----------
            first_row_df = df.iloc[0]
            season_val = first_row_df.get("Season", "UNKNOWN").upper()

            all_skus = df['Colour_SKU'].apply(
                lambda x: re.sub(r".*SKU\s*", "", x)
            ).tolist()
            sku_val = "_".join(all_skus) if all_skus else "UNKNOWN"

            supplier_code = first_row_df.get("Supplier_product_code", "UNKNOWN")
            style_val = first_row_df.get("Style", "UNKNOWN")

            custom_filename = (
                f"PEPCO_{season_val}_{sku_val}_Swingtag "
                f"{supplier_code}_00_{style_val}.csv"
            )

            st.download_button(
                "📥 Download CSV",
                csv_buffer.getvalue().encode('utf-8-sig'),
                file_name=custom_filename,
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Processing stopped - valid PLN price not found")


# ================================================================
#  PEPCO SECTION (Uploader + Reset)
# ================================================================
def pepco_section():
    """Main PEPCO UI section (upload + reset + extra order IDs merge)."""
    st.subheader("PEPCO Data Processing")

    # One-time init for uploader key
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    cols = st.columns([1, 6])

    # Reset / new upload button
    with cols[0]:
        def _reset_all():
            # Clear only app-related session keys
            for k in list(st.session_state.keys()):
                if k.startswith((
                    "ui_", "mat_", "pepco_",
                    "colour_", "colour_manual_", "colour_missing_", "comp_inst", "composition", "care_inst", "care_lang"
                )):
                    st.session_state.pop(k, None)

            # Force uploader refresh
            st.session_state.uploader_key += 1

        st.button("🆕 Upload New File", on_click=_reset_all)

    # File uploader (multi PDF)
    uploaded_pdfs = st.file_uploader(
        "Upload PEPCO Data file",
        type=["pdf"],
        key=f"pepco_uploader_{st.session_state.uploader_key}",
        accept_multiple_files=True
    )

    if uploaded_pdfs:
        if not isinstance(uploaded_pdfs, list):
            uploaded_pdfs = [uploaded_pdfs]

        primary_pdf = uploaded_pdfs[0]
        others = uploaded_pdfs[1:]

        # Collect Order_ID from additional PDFs
        other_ids = []
        for f in others:
            try:
                f.seek(0)
            except Exception:
                pass

            oid = extract_order_id_only(f)
            if oid:
                other_ids.append(oid)

            try:
                f.seek(0)
            except Exception:
                pass

        concatenated_ids = "+".join(other_ids) if other_ids else ""
        process_pepco_pdf(primary_pdf, extra_order_ids=concatenated_ids)


# ================================================================
#  HEADER RENDER
# ================================================================
def render_header():
    """Render logo or fallback icon."""
    left, _ = st.columns([3, 10], vertical_alignment="center")
    with left:
        if os.path.exists(LOGO_SVG):
            st.image(LOGO_SVG, width=300)
        elif os.path.exists(LOGO_PNG):
            st.image(LOGO_PNG, width=300)
        else:
            st.markdown(
                "<div style='font-size:40px'>🏷️</div>",
                unsafe_allow_html=True
            )


# ================================================================
#  MAIN APP
# ================================================================
def main():
    # Apply theme
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Header + Title
    render_header()
    st.title("PEPCO Automation App")

    # Password gate
    if not check_password():
        st.stop()

    # Main content
    pepco_section()

    st.markdown("---")
    st.caption("This app developed by Ovi")


# ================================================================
#  ENTRY POINT
# ================================================================
if __name__ == "__main__":
    main()
