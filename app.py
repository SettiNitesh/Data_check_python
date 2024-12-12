import pandas as pd
import streamlit as st
import requests
from requests.exceptions import RequestException

# Streamlit Page Configuration
st.set_page_config(page_title="Data Validator", layout="wide")

# Helper function for fetching API token
def get_access_token():
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlE0QzM4eE1iSHdpLVFOdmNRRzJuNiJ9.eyJpc3MiOiJodHRwczovL2J5dGVyaWRnZS1hdXRoMC11YXQudXMuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA0MzY1NDEwMjk1ODkzNzkyMzIwIiwiYXVkIjpbImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vYXBpL3YyLyIsImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzMzOTA5OTI2LCJleHAiOjE3MzM5OTYzMjYsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhenAiOiI5cDNhRXpWc0F2QzJqNWNGcGtObWlJMm5zTzNmTXVldiJ9.sHk8pKG53PDtA9DMF9a3zib9Z9F5jhPATXHtUAM4sBcmbMTWfTr9S2vJ9RlbwRKZVbnHjcEtzzuethKRYhim327LV43X4m8mOaaf3QP40kh5AR4KsfV_1--ZLEOta2lQ_HpF3JDWRlTGgFa9vDOmgZIGvs7Wfsxux0fMB3gFuapfnG5e6ZApgXdhLTfW15Da9HVnSftC9TlrvAGWXOLsWMmHUVx8Yt-TKoBD7vVWMRLKFgUpR7GwCKTJxvrcWz9P5NtwNKkCsAnjL8FpOCFKkTUTVPjD4WGzhkQGeOuiF5sBiSY8f-9CWlmSDog-EXcpg76-gLGlmuC_IAF9xVtfrQ"  # Add your access token here

# Function to call the visualizer API
def call_visualizer_api(data, user_prompt, chart_type="bubble"):
    url = "https://gen-ai-visualizer-api-uat.byteridge.com/api/visualize/generate-chart"
    token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Convert timestamp columns to string for JSON serialization
    data = data.copy()
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

# Initialize session state variables
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'data' not in st.session_state:
    st.session_state.data = None
if 'api_response' not in st.session_state:
    st.session_state.api_response = None
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ""
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'grouped_data' not in st.session_state:
    st.session_state.grouped_data = None
if 'comparison_table' not in st.session_state:
    st.session_state.comparison_table = None

# Title and Sidebar Setup
st.title("📊 Data Validator")
st.sidebar.title("🔍 Upload and Analyze Data")

# File Upload and Processing
uploaded_file = st.sidebar.file_uploader("Upload an Excel or CSV File", type=["xls", "xlsx", "csv"])

# Check if a new file is uploaded
if uploaded_file and uploaded_file != st.session_state.uploaded_file:
    st.session_state.uploaded_file = uploaded_file
    try:
        # Detect file type and load data
        if uploaded_file.name.endswith(".csv"):
            st.session_state.data = pd.read_csv(uploaded_file)
        else:
            st.session_state.data = pd.read_excel(uploaded_file)

        # Reset other session state variables
        st.session_state.api_response = None
        st.session_state.user_prompt = ""
        st.session_state.filtered_data = None
        st.session_state.grouped_data = None
        st.session_state.comparison_table = None
    except Exception as e:
        st.error(f"Error occurred while processing the uploaded file: {str(e)}")

if st.session_state.data is not None:
    # Display the uploaded data
    st.subheader("📂 Uploaded Data")
    st.dataframe(st.session_state.data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
        [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

    # Enter analysis prompt
    st.subheader("💬 Enter Analysis Prompt")
    user_prompt = st.text_area(
        "Provide a description for the analysis",
        value=st.session_state.user_prompt
    )
    st.session_state.user_prompt = user_prompt

    # Disable the fetch API button if the user prompt is empty
    fetch_api_disabled = not bool(user_prompt)

    if st.button("🔗 Fetch API", disabled=fetch_api_disabled):
        if user_prompt:
            try:
                # Directly update the API Results instead of creating a separate section
                st.session_state.api_response = call_visualizer_api(st.session_state.data, user_prompt)
                st.write("API Response Metadata:", st.session_state.api_response.get("chartSummary"))

                # Extract the API data and display it
                api_data = pd.DataFrame(st.session_state.api_response["chartConfig"]["data"]["datasets"][0]["data"],
                                        columns=["AggregatedValue"])
                group_column = st.session_state.api_response["dataProcessing"]["groupBy"]
                api_data[group_column] = st.session_state.api_response["chartConfig"]["data"]["labels"]

                # Reset comparison table when new API call is made
                st.session_state.comparison_table = None
            except Exception as e:
                st.error(f"Error occurred while processing the uploaded file: {str(e)}")

    # Dynamic Filters
    st.sidebar.subheader("🔍 Apply Filters")
    filtered_data = st.session_state.data.copy()  # Create a copy of the original data

    # Apply filters if data exists
    if st.session_state.data is not None:
        for col in st.session_state.data.columns:
            if pd.api.types.is_datetime64_any_dtype(st.session_state.data[col]):
                # Date range filter for datetime columns
                min_date = st.session_state.data[col].min().date()
                max_date = st.session_state.data[col].max().date()
                date_range = st.sidebar.date_input(
                    f"Select Date Range for {col}",
                    [min_date, max_date]
                )
                filtered_data = filtered_data[
                    (pd.to_datetime(filtered_data[col]).dt.date >= date_range[0]) &
                    (pd.to_datetime(filtered_data[col]).dt.date <= date_range[1])
                ]

            elif pd.api.types.is_numeric_dtype(st.session_state.data[col]):
                # Slider for numeric columns
                min_val = st.session_state.data[col].min()
                max_val = st.session_state.data[col].max()
                numeric_range = st.sidebar.slider(
                    f"Select Range for {col}",
                    min_value=float(min_val),  # Use float to handle decimal values
                    max_value=float(max_val),
                    value=(float(min_val), float(max_val))
                )
                filtered_data = filtered_data[
                    (filtered_data[col] >= numeric_range[0]) &
                    (filtered_data[col] <= numeric_range[1])
                ]

            elif pd.api.types.is_string_dtype(st.session_state.data[col]):
                # Multi-select for categorical columns
                unique_values = st.session_state.data[col].unique()
                selected_values = st.sidebar.multiselect(
                    f"Select Values for {col}",
                    options=unique_values,
                    default=unique_values
                )
                filtered_data = filtered_data[filtered_data[col].isin(selected_values)]

    st.session_state.filtered_data = filtered_data

    # Display filtered data
    st.subheader("📂 Filtered Data")
    st.dataframe(st.session_state.filtered_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
        [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

    # Display API results if they exist
    if st.session_state.api_response:
        st.subheader("🔍 API Results")
        api_data = pd.DataFrame(st.session_state.api_response["chartConfig"]["data"]["datasets"][0]["data"],
                                columns=["AggregatedValue"])
        group_column = st.session_state.api_response["dataProcessing"]["groupBy"]
        api_data[group_column] = st.session_state.api_response["chartConfig"]["data"]["labels"]
        st.dataframe(api_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
            [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

    # Ensure API response exists before proceeding
    if st.session_state.api_response:
        # Select columns for grouping and aggregation (prefill dropdowns)
        group_column = st.sidebar.selectbox(
            "📊 Select a Column to Group By",
            options=[None] + list(st.session_state.filtered_data.columns),
            index=st.session_state.filtered_data.columns.get_loc(st.session_state.api_response["dataProcessing"]["groupBy"]) + 1
        )

        numeric_columns = st.session_state.filtered_data.select_dtypes(include=["number"]).columns
        agg_column = st.sidebar.selectbox(
            "🔢 Select a Numeric Column to Analyze",
            options=[None] + list(numeric_columns),
            index=numeric_columns.get_loc(st.session_state.api_response["dataProcessing"]["valueField"]) + 1
        )

        # Check if a group has been applied and if both group_column and agg_column are selected
        if group_column and agg_column:
            st.session_state.grouped_data = st.session_state.filtered_data.groupby(group_column)[agg_column].sum().reset_index()

            st.subheader("📊 Grouped Data")
            st.dataframe(st.session_state.grouped_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

        # Show the "Compare Results" button
        if st.button("🔗 Compare Results"):
            # Comparison Table logic
            st.subheader("📋 Comparison Table")

            # Create comparison table using session state data
            api_data = pd.DataFrame(st.session_state.api_response["chartConfig"]["data"]["datasets"][0]["data"],
                                    columns=["AggregatedValue"])
            group_column = st.session_state.api_response["dataProcessing"]["groupBy"]
            api_data[group_column] = st.session_state.api_response["chartConfig"]["data"]["labels"]

            comparison_table = st.session_state.grouped_data.merge(api_data, left_on=group_column, right_on=group_column, how="outer")

            # Rename columns
            comparison_table.rename(columns={st.session_state.api_response["dataProcessing"]["valueField"]: "Preprocessed Result", "AggregatedValue": "API Value"}, inplace=True)

            # Add a column to indicate pass/fail with icons
            comparison_table["Test_Result"] = comparison_table.apply(
                lambda row: "✅" if row["Preprocessed Result"] == row["API Value"] else "❌",
                axis=1
            )

            st.session_state.comparison_table = comparison_table

            st.dataframe(st.session_state.comparison_table.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

            # Calculate passed and failed counts
            passed_count = st.session_state.comparison_table["Test_Result"].value_counts().get("✅", 0)
            failed_count = st.session_state.comparison_table["Test_Result"].value_counts().get("❌", 0)

            # Display results
            st.markdown(f"**Total Passed:** {passed_count}  |  **Total Failed:** {failed_count}")
else:
    st.info("📤 Please upload an Excel or CSV file to start.")