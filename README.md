# PC Bargain Hunter

Automatically searches eBay, OzBargain, and Reddit for second-hand PC parts below your target prices. Results are logged to a Google Sheet and hot deals trigger a WhatsApp alert. Runs twice daily via GitHub Actions (7am and 7pm AEST).

---

## Setup

### 1. eBay API credentials

1. Create a developer account at https://developer.ebay.com
2. Go to **My Keys** and create a new Production keyset
3. Copy your **App ID (Client ID)** and **Cert ID (Client Secret)**
4. Add them as GitHub secrets: `EBAY_APP_ID` and `EBAY_CERT_ID`

### 2. Google Sheets service account

1. Go to https://console.cloud.google.com and create a new project
2. Enable the **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** (IAM & Admin → Service Accounts)
4. Generate a JSON key for the service account (Actions → Manage keys → Add key → JSON)
5. Download the JSON file
6. Share your Google Sheet named **"PC Bargain Hunter"** with the service account's email address (give it **Editor** access)
7. Base64-encode the JSON key:
   ```bash
   base64 -i your-service-account-key.json | tr -d '\n'
   ```
8. Add the encoded string as GitHub secret: `GOOGLE_SHEETS_CREDENTIALS`

> The script will automatically create the three tabs (Listings, Summary, Price Trends) on first run.

### 3. WhatsApp alerts via CallMeBot

1. Save the number **+34 644 71 89 22** in your phone contacts as "CallMeBot"
2. Send this WhatsApp message to that number: `I allow callmebot to send me messages`
3. You'll receive an API key in reply
4. Add your phone (international format, no `+`, e.g. `61412345678`) as GitHub secret: `WHATSAPP_PHONE`
5. Add the API key as GitHub secret: `CALLMEBOT_API_KEY`

### 4. GitHub Actions secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret.

Add all five secrets:

| Secret | Description |
|--------|-------------|
| `EBAY_APP_ID` | eBay App ID (Client ID) |
| `EBAY_CERT_ID` | eBay Cert ID (Client Secret) |
| `GOOGLE_SHEETS_CREDENTIALS` | Base64-encoded service account JSON |
| `WHATSAPP_PHONE` | Your phone in international format (e.g. 61412345678) |
| `CALLMEBOT_API_KEY` | API key from CallMeBot |

---

## Modifying the parts wishlist

Edit `config.py` and update `PARTS_WISHLIST`. Each entry is a dict with:

```python
{
    "category": "GPU",                              # Display name
    "search_terms": ["RTX 3060", "RX 6700 XT"],    # All terms to search
    "max_price_aud": 300,                           # Skip listings above this
    "target_price_aud": 200,                        # "Good deal" threshold
    "hot_deal_price_aud": 150,                      # Triggers WhatsApp alert
}
```

---

## Running locally

```bash
# 1. Clone the repo and install dependencies
pip install -r requirements.txt

# 2. Copy the env template and fill in your credentials
cp .env.example .env
# Edit .env with your actual values

# 3. Run
python main.py
```

Results will be written to Google Sheets if credentials are set, otherwise to `results.json`.

---

## Triggering a manual run via GitHub Actions

1. Go to your repo on GitHub
2. Click the **Actions** tab
3. Select **PC Bargain Hunt** from the workflow list
4. Click **Run workflow** → **Run workflow**

---

## Google Sheet structure

| Tab | Description |
|-----|-------------|
| **Listings** | Every new deal found. Set the Status column manually as you act on leads. |
| **Summary** | Overwritten each run: deals per category, hot deal count, best price today. |
| **Price Trends** | Appended each run: lowest/average price per category over time (chartable). |
