# ESG Document Processor – Deployment Guide

This document describes how to deploy the ESG Document Processor Azure Function to Azure.

---

## Prerequisites

- **Azure Subscription**
- **Azure CLI**: [Install instructions](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Azure Functions Core Tools**: [Install instructions](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- **Python 3.8–3.11** and `pip`
- **Git** and a [GitHub account](https://github.com/)

---

## 1. Prepare Your Code

- Ensure your code is committed and pushed to GitHub.
- Make sure `local.settings.json` is **not** committed (it should be in `.gitignore`).

---

## 2. Create Azure Resources

Open a terminal and run:

```bash
# Login to Azure
az login

# Set variables (change names as needed)
RESOURCE_GROUP=esg-processor-rg
LOCATION=eastus
STORAGE_ACCOUNT=esgprocessorstorage$RANDOM
FUNCTION_APP=esg-processor-func-$RANDOM

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account
az storage account create --name $STORAGE_ACCOUNT --location $LOCATION --resource-group $RESOURCE_GROUP --sku Standard_LRS

# Create the Function App (Linux, Python)
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux
```

---

## 3. Configure Application Settings

Set your Document Intelligence credentials:

```bash
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP \
  --settings DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-doc-intelligence-resource>.cognitiveservices.azure.com/"
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP \
  --settings DOCUMENT_INTELLIGENCE_KEY="<your-document-intelligence-key>"
```

---

## 4. Deploy the Function

### Option A: Deploy from Local Machine

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2. Publish to Azure:
    ```bash
    func azure functionapp publish $FUNCTION_APP
    ```

### Option B: Deploy with GitHub Actions (Recommended for CI/CD)

1. In the Azure Portal, go to your Function App → **Deployment Center**.
2. Connect your GitHub repository and branch.
3. Azure will set up a workflow for automatic deployment.

---

## 5. Test Your Deployment

- Go to the Azure Portal → Function App → Functions.
- Trigger the function by uploading a file to the configured blob container.
- Check the output container for results.
- Monitor logs:
    ```bash
    az functionapp log stream --name $FUNCTION_APP --resource-group $RESOURCE_GROUP
    ```

---

## 6. Security & Best Practices

- **Never commit secrets** (like keys in `local.settings.json`) to GitHub.
- Use Azure Key Vault for production secrets.
- Restrict storage account and function app access as needed.

---

## 7. Clean Up Resources

To avoid charges, remove resources when done:

```bash
az group delete --name $RESOURCE_GROUP
```

---

## References

- [Azure Functions Python Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure Blob Storage Triggers](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-storage-blob-trigger)
- [Azure Document Intelligence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)

---