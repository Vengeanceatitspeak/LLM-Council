# To-Do List & Known Issues

- [ ] **Cloudflare API Token:** Need to add `CLOUDFLARE_API_TOKEN` to `.env` for image generation to work. The account ID is already configured (`8cb75e3ccc02647fff32bd6f3f9738c5`).
- [ ] **OCR Debugging:** The image/document uploader works, but the OCR-based reading (`pytesseract`) needs further debugging for better extraction.
- [ ] **Web Scraper Prompting:** Ensure that the LLM strictly utilizes the provided DuckDuckGo search/scraping context, and never responds with "I don't have access to real-time data."
