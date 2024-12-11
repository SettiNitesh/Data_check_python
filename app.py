import pandas as pd
import streamlit as st
import requests
from requests.exceptions import RequestException

# Streamlit Page Configuration
st.set_page_config(page_title="Data Analyzer Verifier", layout="wide")

# Helper function for fetching API token
def get_access_token():
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlE0QzM4eE1iSHdpLVFOdmNRRzJuNiJ9.eyJpc3MiOiJodHRwczovL2J5dGVyaWRnZS1hdXRoMC11YXQudXMuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA0MzY1NDEwMjk1ODkzNzkyMzIwIiwiYXVkIjpbImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vYXBpL3YyLyIsImh0dHBzOi8vYnl0ZXJpZGdlLWF1dGgwLXVhdC51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzMzODEyMTM1LCJleHAiOjE3MzM4OTg1MzUsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhenAiOiI5cDNhRXpWc0F2QzJqNWNGcGtObWlJMm5zTzNmTXVldiJ9.fsd4-Pambg24KIKL08Y9SbD2eBG5PymEqpPtTYY_E2u9IN0TQCT9NTOx_YiQZ4X4VQLYIanZhOj7fShqdU7W8OGKlkWppkSJkXwJmeqrMjr2bCDZ8Im9j9ssCbAyYzauuowetmNeGGZgAeY6BktU3scwzy9rXfmd_P7-ltLnqya0p6S1VoL6ZQI3vDCpFhZb9hhuAIW7pdc8EaSiqEJAqU9k3sNaURbBL0BXEJFgMkA6t6kITobAZcMee3hCvnlsvzU30zpnvoeGsfZLPiIe72r6XCMBSWIqnfR_QGtIOwY7GaqDC-xNdjpoPRIs26EwRLGW1h-Gtal07jDnQYVK8A"

# Function to call the visualizer API
def call_visualizer_api(data, user_prompt, chart_type="bar"):
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

# Title and Sidebar Setup
st.title("📊 Data Analyzer Verifier")
st.sidebar.title("🔍 Upload and Analyze Data")

# File Upload and Processing
uploaded_file = st.sidebar.file_uploader("Upload an Excel or CSV File", type=["xls", "xlsx", "csv"])

if uploaded_file:
    try:
        # Detect file type and load data
        if uploaded_file.name.endswith(".csv"):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        # Display the uploaded data
        st.subheader("📂 Uploaded Data")
        st.dataframe(data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
            [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

        # Select columns for grouping and aggregation
        group_column = st.sidebar.selectbox("📊 Select a Column to Group By", data.columns)
        numeric_columns = data.select_dtypes(include=["number"]).columns
        agg_column = st.sidebar.selectbox("🔢 Select a Numeric Column to Analyze", numeric_columns)

        st.subheader("🧪 Upload Test Case Data")
        test_case_file = st.file_uploader("Upload an Excel or CSV File for Test Case Data", type=["xls", "xlsx", "csv"])

        if test_case_file:
            if test_case_file.name.endswith(".csv"):
                test_case_data = pd.read_csv(test_case_file)
            else:
                test_case_data = pd.read_excel(test_case_file)

            st.subheader("📂 Test Case Data")
            st.dataframe(test_case_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

            grouped_data = test_case_data

        st.subheader("💬 Enter Analysis Prompt")
        user_prompt = st.text_area(
            "Provide a description for the analysis",
            value="A bar chart is effective for comparing the total sales amounts across different categories or products, allowing for easy identification of top-performing items."
        )

        if st.button("🔗 Compare Results"):
            if user_prompt:
                try:
                    st.subheader("🔍 API Results")
                    api_response = call_visualizer_api(data, user_prompt)
                    st.write("API Response Metadata:", api_response.get("chartSummary"))

                    api_data = pd.DataFrame(api_response["chartConfig"]["data"]["datasets"][0]["data"],
                                            columns=["AggregatedValue"])
                    api_data[group_column] = api_response["chartConfig"]["data"]["labels"]
                    st.dataframe(api_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                        [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

                    st.subheader("📋 Comparison Table")
                    comparison_table = pd.merge(
                        grouped_data,
                        api_data,
                        left_on=group_column,
                        right_on=group_column,
                        how="outer"
                    )
                    comparison_table.rename(columns={
                        "Sum": "Test_Case_Sum",
                        "AggregatedValue": "API_Value"
                    }, inplace=True)

                    # Add a column to indicate pass/fail with icons
                    comparison_table["Test_Result"] = comparison_table.apply(
                        lambda row: "✅" if row["Test_Case_Sum"] == row["API_Value"] else "❌",
                        axis=1
                    )
                    st.dataframe(comparison_table.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                        [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

                    # Calculate passed and failed counts
                    passed_count = comparison_table["Test_Result"].value_counts().get("✅", 0)
                    failed_count = comparison_table["Test_Result"].value_counts().get("❌", 0)

                    # Display results
                    st.markdown(
                        f"""
                        <div style='color: green; font-size: 20px; text-align: center;'>
                            ✅ Total Test Cases Passed: {passed_count}
                        </div>
                        <div style='color: red; font-size: 20px; text-align: center;'>
                            ❌ Total Test Cases Failed: {failed_count}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.error(f"Error fetching or processing API response: {e}")
            else:
                st.error("⚠️ Please enter a prompt for the analysis.")
    except Exception as e:
        st.error(f"⚠️ Error processing the file: {e}")
else:
    st.info("📤 Please upload an Excel or CSV file to start.")
