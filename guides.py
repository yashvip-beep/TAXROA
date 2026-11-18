"""Step-by-step guides and video slots.
To add a video, paste a YouTube or other link into the "url" field in this file.
Leave it as "" until you have a real link that you have checked."""

VIDEO_NOTE = "Video coming soon. The link will appear here once it is added in guides.py."

GUIDES = {
    "Getting started": {
        "title": "How to use GST TAXORA",
        "summary": "A quick tour for first-time users. You do not need an account or personal details.",
        "steps": [
            "Click **Get started** on the first screen.",
            "On the menu, choose the feature you need. Each option is a button with a short description.",
            "The selected feature opens on its own page. Use **Back to menu** at the top to return.",
            "Read the disclaimer in the sidebar (open it with the » arrow at the top left). GST advice depends on the facts of your case.",
            "Always check the official notification before you invoice or file a return.",
        ],
        "videos": [{"title": "Overview of GST TAXORA", "url": ""}],
    },
    "Search a GST rate": {
        "title": "Search for a goods or service rate",
        "summary": "Find the GST rate, HSN or SAC code and notification for an item.",
        "steps": [
            "Open **Search** from the menu.",
            "Pick what you are looking for: goods by name, goods by HSN code, or services by name or SAC code.",
            "Choose **Intra-State** if buyer and seller are in the same state, or **Inter-State** if they are not.",
            "Type the item name, for example *rice* or *cement*. Small spelling mistakes are fine.",
            "Read the result card: status, total GST, the CGST/SGST or IGST split, the notification and the condition.",
            "Suggestions appear in a separate box and are not confirmed matches. Check the item name before relying on them.",
            "Use **Download these results (CSV)** to save the result.",
        ],
        "videos": [{"title": "How to search a rate", "url": ""}],
    },
    "Browse by category": {
        "title": "Browse items by category and GST slab",
        "summary": "See all items in a category or at a particular rate.",
        "steps": [
            "Open **Browse by category** from the menu.",
            "Choose a category, or leave it as *All categories*.",
            "Choose Goods, Services or Both.",
            "Choose a GST slab to see only items at that rate.",
            "Use Search to see the full condition and notes for any item in the table.",
        ],
        "videos": [{"title": "How to browse by category", "url": ""}],
    },
    "GST calculator": {
        "title": "Calculate GST on an amount",
        "summary": "Add GST to a price, or take GST out of a price that already includes it.",
        "steps": [
            "Open **GST calculator** from the menu.",
            "Enter the base amount in rupees.",
            "Choose a rate: pick an item from the dataset, or choose *Manual rate* and type the rate yourself.",
            "Choose Intra-State or Inter-State.",
            "Choose **Add GST to base amount** if your price excludes GST, or **Extract GST** if it includes GST.",
            "Read the taxable value, CGST, SGST/UTGST, IGST and final amount.",
        ],
        "videos": [{"title": "How to use the calculator", "url": ""}],
    },
    "Barcode & QR scanner": {
        "title": "Scan a product barcode or QR code",
        "summary": "Scan a product to see its category and GST rate, if that product is linked in the app.",
        "steps": [
            "Open **Barcode & QR scanner** from the menu.",
            "Choose Intra-State or Inter-State.",
            "Use the **Camera** tab and allow camera access when your browser asks. Hold the barcode steady and well lit.",
            "Or use **Upload photo** to choose a clear photo of the barcode.",
            "Or use **Type code** and enter the number printed under the barcode.",
            "If the product is linked to a verified item, its category and GST rate appear. If not, search by name instead.",
        ],
        "videos": [{"title": "How to scan a barcode", "url": ""}],
    },
    "GST invoice generator": {
        "title": "Create a printable invoice",
        "summary": "Enter seller and buyer details, add items, and download a PDF draft.",
        "steps": [
            "Open **GST invoice generator** from the menu.",
            "Enter the seller and buyer names and addresses. GSTIN is optional for unregistered parties.",
            "Enter an invoice number and date.",
            "Choose Intra-State or Inter-State.",
            "In the item table, add a row for each item: description, HSN/SAC, quantity, unit price and GST %.",
            "Use **Look up GST %** above the table to copy the correct rate from the dataset.",
            "Check the summary: taxable value, CGST, SGST/UTGST or IGST, and grand total.",
            "Click **Download invoice PDF**. The PDF is marked DRAFT. Check invoice content rules under GST law before issuing it.",
        ],
        "videos": [{"title": "How to make an invoice", "url": ""}],
    },
    "Bulk check": {
        "title": "Check many items at once",
        "summary": "Upload a list of items in a CSV file and get the GST rate for each one.",
        "steps": [
            "Open **Bulk check** from the menu.",
            "Download the sample CSV, or make your own file with one column named **item**.",
            "Upload the CSV file.",
            "Read the table. Each row shows the first matched goods item, its HSN code, total GST and status.",
            "Rows marked *Not found* need a better name. Try Search for those items.",
            "Download the results as CSV.",
        ],
        "videos": [{"title": "How to use bulk check", "url": ""}],
    },
    "Privacy & data": {
        "title": "Your privacy and data",
        "summary": "What the app keeps, what it does not keep, and how to delete your data.",
        "steps": [
            "Open **Privacy & data** from the menu to read the full notice.",
            "Searches and calculations need no personal data.",
            "Recent searches are off by default. If you turn them on, they stay only in your session.",
            "Invoice details stay in your session. Click **Delete all session data now** to clear them.",
        ],
        "videos": [],
    },
}
