import pandas as pd
import requests
import os
import numpy as np
from requests.exceptions import RequestException
import streamlit as st


# Helper function for fetching API token
def get_access_token():
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlE0QzM4eE1iSHdpLVFOdmNRRzJuNiJ9.eyJpc3MiOiJodHRwczovL2J5dGVyaWRnZS1hdXRoMC11YXQudXMuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA0MzY1NDEwMjk1ODkzNzkyMzIwIiwiYXVkIjpbImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vYXBpL3YyLyIsImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzM4NTc5NzA0LCJleHAiOjE3Mzg2NjYxMDQsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhenAiOiI5cDNhRXpWc0F2QzJqNWNGcGtObWlJMm5zTzNmTXVldiJ9.ibYtZZt9RBWLKt5cZ33yR9VxQusQN1cVLzQjD5pZqnXxaPlP5iD-zlHKNzgeUq9KzBWOiesfjR7TeSYMuwxXOhKiCbMo5exJFGW7OJdBH4Q4T-A4q3830EQFS6Mcnwk44AwMMghur_594Hk59nsroR1A0nqD54o4sDaJGnah-A1BucLkP7JQO434ByWFTCaX2n5D_KLNw3wSZxaOSCpGXx5UwmRRPJXa7Cf9rhUp87Uv0pHQuDA9dXYZloDlDp9WIwV95JbRmYlaHHk11cDs2JBUq6MUK1uHnktYVd96H-eI5H1j7ejtF48_FkrLSrqgOqSJv8mAAVBFebCgGdXjJQ"
# Function to call the visualizer API
def call_visualizer_api(data, user_prompt, chart_type="bar"):
    url = "https://gen-ai-visualizer-api-uat.byteridge.com/api/visualize/generate-chart"
    token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Create a copy of the data to avoid modifying the original
    data = data.copy()

    # Handle NaN values before JSON serialization
    # Replace NaN with None for numeric columns
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    data[numeric_columns] = data[numeric_columns].replace({pd.NA: None, np.nan: None})

    # Replace NaN with empty string for string columns
    string_columns = data.select_dtypes(include=['object']).columns
    data[string_columns] = data[string_columns].replace({pd.NA: "", np.nan: ""})

    # Convert timestamp columns to string for JSON serialization
    for col in data.select_dtypes(include=["datetime", "datetime64"]):
        data[col] = data[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "chartType": chart_type,
        "data": data.to_dict(orient="records"),
        "userPrompt": user_prompt,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        st.error(f"API call failed: {str(e)}")
        raise



def generate_test_case_name(data_processing):
    """
    Convert data processing details into a readable test case description.

    Args:
        data_processing (dict): Dictionary containing data processing details

    Returns:
        str: A human-readable description of the data processing
    """
    # Base description
    description_parts = []

    # Aggregation method
    if data_processing.get('aggregation'):
        description_parts.append(f"Aggregating by {data_processing['aggregation'].upper()}")

    # Group By
    if data_processing.get('groupBy'):
        description_parts.append(f"grouped by {data_processing['groupBy']}")

    # Value Field
    if data_processing.get('valueField'):
        description_parts.append(f"on {data_processing['valueField']}")

    # Filters
    if data_processing.get('filters'):
        filter_descriptions = []
        for filter_condition in data_processing['filters']:
            field = filter_condition.get('field', 'Unknown')
            operator = filter_condition.get('operator', '==')
            value = filter_condition.get('value', 'Unknown')
            filter_descriptions.append(f"{field} {operator} {value}")

        if filter_descriptions:
            description_parts.append(f"with filters: {' and '.join(filter_descriptions)}")

    # Combine parts
    full_description = " ".join(description_parts)

    return full_description.capitalize()

# Function to log test result
def log_test_result(
    test_case_id,
    test_case_desc,
    filters,
    processed_data,
    api_data,
    status,
    file_path="VisualizerTests.csv",
):
    """
    Log test result to Excel file with enhanced details.
    """
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            existing_df = pd.read_csv(file_path)
        else:
            existing_df = pd.DataFrame(
                columns=[
                    "Test Case ID",
                    "Test Case Description",
                    "Filters",
                    "Expected Result",
                    "Actual Result",
                    "Status",
                    "Remarks",
                ]
            )

        # Prepare comparison details as remarks
        comparison_results = st.session_state.get("comparison_results", {})
        remarks = []
        if comparison_results and "comparisons" in comparison_results:
            for comp in comparison_results["comparisons"]:
                if not comp["value_match"]:
                    remark = (
                        f"Mismatch - Label: {comp['processed_label']}, "
                        f"Expected: {comp['processed_value']}, "
                        f"Actual: {comp['api_value']}"
                    )
                    remarks.append(remark)

        # Convert processed data and API data to concise string representations
        expected_result = processed_data.to_dict(orient='records')
        actual_result = api_data.get("chartConfig", {}).get("data", {})

        # Combine remarks
        combined_remarks = "\n".join(remarks) if remarks else "No issues"

        # Create a new row for the test case
        new_row = pd.DataFrame({
            "Test Case ID": [test_case_id],
            "Test Case Description": [test_case_desc],
            "Filters": [filters],
            "Expected Result": [str(expected_result)],
            "Actual Result": [str(actual_result)],
            "Status": [status],
            "Remarks": [combined_remarks]
        })

        # Concatenate the existing DataFrame with the new row
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)

        # Write the updated DataFrame back to the Excel file
        updated_df.to_csv(file_path, index=False)

        return "Test case logged successfully!"

    except Exception as e:
        st.error(f"Error logging test result: The file is currently open in another application. Please close it and retry.")
        return ""

# Function to initialize session state
def initialize_session_state():
    if "show_results" not in st.session_state:
        st.session_state.show_results = False
    if "grouped_data" not in st.session_state:
        st.session_state.grouped_data = None
    if "api_response" not in st.session_state:
        st.session_state.api_response = None
    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = {}
    if "test_case_description" not in st.session_state:
       st.session_state.test_case_description = ""