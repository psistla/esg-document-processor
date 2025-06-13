"""
ESG Document Processing Azure Function
Author: Prasanth Sistla (psistlaw@gmail.com), Generated for ESG metrics extraction from Excel files
Version: 1.0
Description: Azure Function with blob trigger to process ESG documents using Document Intelligence
"""

import logging
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import traceback

import azure.functions as func
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient


# Initialize the Function App with v2 programming model
app = func.FunctionApp()

# Configuration from environment variables
DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
DOCUMENT_INTELLIGENCE_KEY = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
STORAGE_CONNECTION_STRING = os.getenv("AzureWebJobsStorage")

# Initialize clients
doc_intelligence_client = None
blob_service_client = None

def initialize_clients():
    """Initialize Azure service clients"""
    global doc_intelligence_client, blob_service_client
    
    if not doc_intelligence_client and DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY:
        doc_intelligence_client = DocumentIntelligenceClient(
            endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_KEY)
        )
    
    if not blob_service_client and STORAGE_CONNECTION_STRING:
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)


class ESGDocumentProcessor:
    """ESG Document Processing Logic"""
    
    def __init__(self, doc_client: DocumentIntelligenceClient):
        self.doc_client = doc_client
        self.esg_keywords = {
            'environmental': [
                'carbon', 'emissions', 'co2', 'greenhouse gas', 'ghg', 'renewable energy',
                'water consumption', 'water usage', 'waste', 'recycling', 'sustainability',
                'biodiversity', 'deforestation', 'climate change', 'energy efficiency',
                'scope 1', 'scope 2', 'scope 3', 'carbon footprint', 'environmental impact'
            ],
            'social': [
                'diversity', 'inclusion', 'employee', 'workforce', 'human rights',
                'community', 'safety', 'health', 'training', 'labor', 'gender',
                'ethnicity', 'workplace', 'equal opportunity', 'social impact',
                'customer satisfaction', 'data privacy', 'product safety'
            ],
            'governance': [
                'board', 'directors', 'executive', 'compensation', 'ethics',
                'compliance', 'risk management', 'audit', 'transparency',
                'accountability', 'anti-corruption', 'whistleblower',
                'conflicts of interest', 'shareholder', 'stakeholder'
            ]
        }
    
    def analyze_document(self, blob_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Document Intelligence"""
        try:
            # Use layout model for comprehensive extraction including tables
            poller = self.doc_client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=blob_content,
                content_type="application/octet-stream"
            )
            
            result = poller.result()
            return self._process_analysis_result(result, filename)
            
        except Exception as e:
            logging.error(f"Document analysis failed: {str(e)}")
            raise
    
    def _process_analysis_result(self, result, filename: str) -> Dict[str, Any]:
        """Process Document Intelligence analysis result"""
        processed_data = {
            "metadata": {
                "filename": filename,
                "processed_at": datetime.utcnow().isoformat(),
                "model_used": "prebuilt-layout",
                "total_pages": len(result.pages) if result.pages else 0
            },
            "esg_metrics": {
                "environmental": [],
                "social": [],
                "governance": []
            },
            "extracted_tables": [],
            "key_value_pairs": [],
            "text_content": ""
        }
        
        # Extract all text content
        if result.content:
            processed_data["text_content"] = result.content
        
        # Process tables - critical for ESG metrics in Excel files
        if result.tables:
            for table_idx, table in enumerate(result.tables):
                table_data = {
                    "table_id": table_idx,
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                
                for cell in table.cells:
                    cell_data = {
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content,
                        "row_span": getattr(cell, 'row_span', 1),
                        "column_span": getattr(cell, 'column_span', 1)
                    }
                    table_data["cells"].append(cell_data)
                
                processed_data["extracted_tables"].append(table_data)
        
        # Process key-value pairs
        if result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                kv_data = {
                    "key": kv_pair.key.content if kv_pair.key else "",
                    "value": kv_pair.value.content if kv_pair.value else "",
                    "confidence": getattr(kv_pair, 'confidence', 0.0)
                }
                processed_data["key_value_pairs"].append(kv_data)
        
        # Identify ESG-related content
        processed_data["esg_metrics"] = self._extract_esg_metrics(processed_data)
        
        return processed_data
    
    def _extract_esg_metrics(self, processed_data: Dict[str, Any]) -> Dict[str, List]:
        """Extract ESG-specific metrics from processed document data"""
        esg_metrics = {"environmental": [], "social": [], "governance": []}
        
        # Combine all text sources for analysis
        all_text = processed_data.get("text_content", "").lower()
        
        # Add table content to text analysis
        for table in processed_data.get("extracted_tables", []):
            for cell in table.get("cells", []):
                all_text += " " + cell.get("content", "").lower()
        
        # Add key-value pairs to text analysis
        for kv in processed_data.get("key_value_pairs", []):
            all_text += " " + kv.get("key", "").lower() + " " + kv.get("value", "").lower()
        
        # Search for ESG keywords and extract relevant metrics
        for category, keywords in self.esg_keywords.items():
            for keyword in keywords:
                if keyword.lower() in all_text:
                    # Extract context around the keyword
                    context = self._extract_context(all_text, keyword.lower())
                    if context:
                        esg_metrics[category].append({
                            "keyword": keyword,
                            "context": context,
                            "found_at": datetime.utcnow().isoformat()
                        })
        
        # Extract numerical metrics from tables
        numerical_metrics = self._extract_numerical_metrics(processed_data.get("extracted_tables", []))
        for category in esg_metrics:
            esg_metrics[category].extend(numerical_metrics.get(category, []))
        
        return esg_metrics
    
    def _extract_context(self, text: str, keyword: str, context_length: int = 100) -> str:
        """Extract context around a keyword"""
        try:
            index = text.find(keyword)
            if index != -1:
                start = max(0, index - context_length)
                end = min(len(text), index + len(keyword) + context_length)
                return text[start:end].strip()
        except Exception:
            pass
        return ""
    
    def _extract_numerical_metrics(self, tables: List[Dict]) -> Dict[str, List]:
        """Extract numerical metrics from tables that might be ESG-related"""
        numerical_metrics = {"environmental": [], "social": [], "governance": []}
        
        for table in tables:
            # Look for headers and values that indicate ESG metrics
            headers = []
            data_rows = []
            
            # Organize table data by rows
            max_row = max([cell["row_index"] for cell in table["cells"]]) if table["cells"] else 0
            
            for row_idx in range(max_row + 1):
                row_cells = [cell for cell in table["cells"] if cell["row_index"] == row_idx]
                row_cells.sort(key=lambda x: x["column_index"])
                
                if row_idx == 0:  # Assume first row contains headers
                    headers = [cell["content"] for cell in row_cells]
                else:
                    data_rows.append([cell["content"] for cell in row_cells])
            
            # Analyze headers and data for ESG relevance
            for col_idx, header in enumerate(headers):
                header_lower = header.lower()
                
                # Categorize based on header content
                category = None
                for esg_category, keywords in self.esg_keywords.items():
                    if any(keyword in header_lower for keyword in keywords):
                        category = esg_category
                        break
                
                if category:
                    # Extract numerical values from this column
                    for row in data_rows:
                        if col_idx < len(row):
                            value = row[col_idx]
                            # Try to extract numerical values
                            try:
                                # Simple numeric extraction (can be enhanced)
                                import re
                                numbers = re.findall(r'-?\d+\.?\d*', value)
                                if numbers:
                                    numerical_metrics[category].append({
                                        "metric": header,
                                        "value": numbers[0],
                                        "unit": self._extract_unit(value),
                                        "raw_text": value
                                    })
                            except Exception:
                                continue
        
        return numerical_metrics
    
    def _extract_unit(self, value_text: str) -> str:
        """Extract unit from value text"""
        import re
        # Common ESG units
        units = ['%', 'kg', 'tons', 'tco2e', 'kwh', 'mwh', 'gj', 'liters', 'gallons', '$', 'usd', 'eur']
        
        for unit in units:
            if unit.lower() in value_text.lower():
                return unit
        
        # Look for other patterns
        unit_match = re.search(r'([a-zA-Z%$€£]+)', value_text)
        if unit_match:
            return unit_match.group(1)
        
        return ""


@app.blob_trigger(
    arg_name="inputblob",
    path="input-files/{name}",
    connection="AzureWebJobsStorage"
)
@app.blob_output(
    arg_name="outputblob",
    path="output-files/{name}.json",
    connection="AzureWebJobsStorage"
)
def process_esg_document(inputblob: func.InputStream, outputblob: func.Out[str]) -> None:
    """
    Main function triggered when a file is uploaded to input-files container.
    Processes ESG documents using Azure Document Intelligence and outputs JSON.
    """
    
    try:
        # Initialize clients
        initialize_clients()
        
        if not doc_intelligence_client:
            raise ValueError("Document Intelligence client not initialized. Check configuration.")
        
        logging.info(f"Processing blob: {inputblob.name}")
        logging.info(f"Blob size: {inputblob.length} bytes")
        
        # Validate file type (Excel files)
        filename = inputblob.name.split('/')[-1]  # Get filename without path
        if not filename.lower().endswith(('.xlsx', '.xls')):
            logging.warning(f"Skipping non-Excel file: {filename}")
            return
        
        # Read blob content
        blob_content = inputblob.read()
        
        # Process document
        processor = ESGDocumentProcessor(doc_intelligence_client)
        processed_data = processor.analyze_document(blob_content, filename)
        
        # Add processing summary
        processed_data["processing_summary"] = {
            "status": "success",
            "input_filename": filename,
            "input_size_bytes": inputblob.length,
            "esg_categories_found": [
                category for category, metrics in processed_data["esg_metrics"].items() 
                if metrics
            ],
            "total_tables_extracted": len(processed_data["extracted_tables"]),
            "total_key_value_pairs": len(processed_data["key_value_pairs"])
        }
        
        # Convert to JSON and output
        output_json = json.dumps(processed_data, indent=2, ensure_ascii=False)
        outputblob.set(output_json)
        
        logging.info(f"Successfully processed {filename}")
        logging.info(f"Found {sum(len(metrics) for metrics in processed_data['esg_metrics'].values())} ESG metrics")
        
    except Exception as e:
        error_msg = f"Error processing blob {inputblob.name}: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        
        # Create error output
        error_output = {
            "error": {
                "message": str(e),
                "filename": inputblob.name,
                "timestamp": datetime.utcnow().isoformat(),
                "traceback": traceback.format_exc()
            }
        }
        
        outputblob.set(json.dumps(error_output, indent=2))


@app.function_name("health_check")
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring"""
    try:
        initialize_clients()
        
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "document_intelligence": bool(doc_intelligence_client),
                "blob_storage": bool(blob_service_client)
            }
        }
        
        return func.HttpResponse(
            json.dumps(status),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_status = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_status),
            status_code=500,
            mimetype="application/json"
        )