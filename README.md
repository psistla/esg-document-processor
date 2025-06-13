# ESG Document Processor

Azure Function app for processing ESG (Environmental, Social, and Governance) documents using Azure Document Intelligence.

## Features

- Automated processing of Excel files for ESG metrics
- Table extraction and analysis
- Key-value pair detection
- ESG keyword identification and context extraction
- JSON output generation

## Setup

1. Clone repository:
```bash
git clone https://github.com/[your-username]/esg-document-processor.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Azure settings in [local.settings.json](http://_vscodecontentref_/0):
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DOCUMENT_INTELLIGENCE_ENDPOINT": "your-endpoint",
    "DOCUMENT_INTELLIGENCE_KEY": "your-key"
  }
}
```

## Local Development

1. Install Azure Functions Core Tools
2. Run [func start](http://_vscodecontentref_/1) to start locally
3. Upload files to `input-files` container
4. Check processed results in `output-files` container

## Deployment

See deployment instructions in `DEPLOYMENT.md`
