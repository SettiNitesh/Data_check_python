import pandas as pd
import requests
import streamlit as st
from utils import call_visualizer_api, log_test_result, initialize_session_state, generate_test_case_name

# Streamlit Page Configuration
st.set_page_config(page_title="Data Validator", layout="wide")

# Main Streamlit App
def main():
    # Initialize session state variables
    initialize_session_state()

    # Title and Sidebar Setup
    st.title("📊 Data Validator")
    st.sidebar.title("🔍 Upload and Analyze Data")

    # File Upload and Processing
    uploaded_file = st.sidebar.file_uploader(
        "Upload an Excel or CSV File", type=["xls", "xlsx", "csv"]
    )

    # Test Case Description Field (moved before Chart Type)
    st.sidebar.subheader("📝 Test Case Description")
    test_case_description = st.sidebar.text_area(
        "Enter a detailed description for this test case",
        value=""
    )
    st.session_state.test_case_description = test_case_description

    if uploaded_file is not None:
        try:
            # Detect file type and load data
            if uploaded_file.name.endswith(".csv"):
                data = pd.read_csv(uploaded_file)
            else:
                data = pd.read_excel(uploaded_file)

            # Ensure datetime columns are properly converted
            for col in data.columns:
                if pd.api.types.is_datetime64_any_dtype(data[col]):
                    data[col] = pd.to_datetime(data[col])

            # Display the uploaded data
            st.subheader("📂 Uploaded Data")
            st.dataframe(
                data.style.set_properties(**{"text-align": "center"}).set_table_styles(
                    [{"selector": "th", "props": [("text-align", "center")]}]
                ),
                use_container_width=True,
            )

            chart_type_options = ["bar", "pie", "bubble", "scatter", "line"]
            selected_chart_type = st.sidebar.selectbox(
                "📊 Select Chart Type",
                options=chart_type_options,
                index=0  # Default to bar chart
            )

            # Initialize filtered data
            filtered_data = data.copy()

            # Select columns for grouping and aggregation (with None as default values)
            group_column = st.sidebar.selectbox(
                "📊 Select a Column to Group By",
                options=[None] + list(filtered_data.columns),
            )
            numeric_columns = filtered_data.select_dtypes(include=["number"]).columns
            agg_column = st.sidebar.selectbox(
                "🔢 Select a Numeric Column to Analyze",
                options=[None] + list(numeric_columns),
            )

            # Dynamic Filters
            st.sidebar.subheader("🔍 Apply Filters")

            # Multi-select dropdown to select columns for filtering
            selected_columns = st.sidebar.multiselect(
                "Select Columns to Filter",
                options=list(data.columns),
                key="filter_columns_multiselect",
            )

            # Render filter UI for selected columns
            for filter_column in selected_columns:
                st.sidebar.subheader(f"Filter: {filter_column}")

                # Determine column type and render appropriate filter
                if pd.api.types.is_datetime64_any_dtype(filtered_data[filter_column]):
                    # Date range filter for datetime columns
                    min_date = filtered_data[filter_column].min().date()
                    max_date = filtered_data[filter_column].max().date()
                    date_range = st.sidebar.date_input(
                        f"Select Date Range for {filter_column}",
                        [min_date, max_date],
                        key=f"date_filter_input_{filter_column}"
                    )
                    filtered_data = filtered_data[
                        (filtered_data[filter_column].dt.date >= date_range[0])
                        & (filtered_data[filter_column].dt.date <= date_range[1])
                    ]

                elif pd.api.types.is_numeric_dtype(filtered_data[filter_column]):
                    # Slider for numeric columns
                    min_val = filtered_data[filter_column].min()
                    max_val = filtered_data[filter_column].max()
                    numeric_range = st.sidebar.slider(
                        f"Select Range for {filter_column}",
                        min_value=float(min_val),  # Use float to handle decimal values
                        max_value=float(max_val),
                        value=(float(min_val), float(max_val)),
                        key=f"numeric_filter_slider_{filter_column}"
                    )
                    filtered_data = filtered_data[
                        (filtered_data[filter_column] >= numeric_range[0])
                        & (filtered_data[filter_column] <= numeric_range[1])
                    ]

                elif pd.api.types.is_string_dtype(filtered_data[filter_column]):
                    # Multi-select for categorical columns
                    unique_values = filtered_data[filter_column].unique()
                    selected_values = st.sidebar.multiselect(
                        f"Select Values for {filter_column}",
                        options=unique_values,
                        default=unique_values,
                        key=f"categorical_filter_multiselect_{filter_column}"
                    )
                    filtered_data = filtered_data[
                        filtered_data[filter_column].isin(selected_values)
                    ]

            # Display filtered data only if it's different from the original data
            if not filtered_data.equals(data):
                st.subheader("📂 Filtered Data")
                st.dataframe(
                    filtered_data.style.set_properties(
                        **{"text-align": "center"}
                    ).set_table_styles(
                        [{"selector": "th", "props": [("text-align", "center")]}]
                    ),
                    use_container_width=True,
                )

                # Optional: Display the number of rows in original vs filtered data
                st.write(f"Original Data Rows: {len(data)} | Filtered Data Rows: {len(filtered_data)}")

            # Group data only if both group_column and agg_column are selected
            if group_column and agg_column:
                # Convert group_column to string to ensure compatibility
                grouped_data = (
                    filtered_data.groupby(group_column)[agg_column].sum().reset_index()
                )
                grouped_data[group_column] = grouped_data[group_column].astype(str)
                st.session_state.grouped_data = grouped_data  # Store in session state
                st.subheader("📊 Grouped Data")
                st.dataframe(
                    grouped_data.style.set_properties(
                        **{"text-align": "center"}
                    ).set_table_styles(
                        [{"selector": "th", "props": [("text-align", "center")]}]
                    ),
                    use_container_width=True,
                )
            else:
                st.warning(
                    "⚠️ Please select both a column to Group By and a Numeric Column to Analyze."
                )

            # Enter analysis prompt
            st.subheader("💬 Enter Analysis Prompt")
            user_prompt = st.text_area(
                "Provide a description for the analysis", value=""
            )

            # Check if all required fields are filled
            is_compare_ready = (
                group_column is not None
                and agg_column is not None
                and user_prompt.strip() != ""
            )

            # Create a button with a key to track state
            compare_button = st.button(
                "🔗 Compare Results",
                disabled=not is_compare_ready,
                key="permanent_compare_button",
            )

            # Show warning if any required field is missing
            if not is_compare_ready:
                if user_prompt.strip() == "":
                    st.warning("⚠️ Please Enter an Analysis Prompt")

            # Trigger comparison when button is clicked
            if is_compare_ready and compare_button:
                st.session_state.show_results = True
                # Reset session state variables
                st.session_state.api_response = None
                st.session_state.comparison_table = None
                st.session_state.comparison_results = None

            # Render results if show_results is True and we have all necessary data
            if st.session_state.show_results and group_column and agg_column:
                try:
                    st.subheader("🔍 API Results")

                    # Call API only if results haven't been generated
                    if st.session_state.api_response is None:
                        # Use stored grouped data for simulated API call
                        api_response = call_visualizer_api(data, user_prompt, chart_type=selected_chart_type)
                        st.session_state.api_response = api_response  # Store API response

                    # Use stored API response
                    api_response = st.session_state.api_response

                    # Convert API response labels to string to ensure compatibility
                    api_data = pd.DataFrame(
                        api_response["chartConfig"]["data"]["datasets"][0]["data"],
                        columns=["AggregatedValue"],
                    )
                    api_data[group_column] = [str(label) for label in api_response["chartConfig"]["data"]["labels"]]
                    st.dataframe(api_data.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                            [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

                    st.subheader("📋 Comparison Table")
                    # Regenerate comparison table only if not already generated
                    if st.session_state.comparison_table is None:
                        # Reset the index to ensure matching merge keys
                        grouped_data_reset = st.session_state.grouped_data.reset_index(drop=True)
                        api_data_reset = api_data.reset_index(drop=True)

                        # Merge with how='outer' to include all rows
                        comparison_table = pd.concat([grouped_data_reset, api_data_reset], axis=1)

                        # Rename columns to handle potential conflicts
                        comparison_table.columns = [
                            f"{col}_processed" if i < len(grouped_data_reset.columns)
                            else col
                            for i, col in enumerate(comparison_table.columns)
                        ]

                        st.session_state.comparison_table = comparison_table  # Store comparison table

                    # Use stored comparison table
                    comparison_table = st.session_state.comparison_table

                    # Generate comparison results if not already done
                    if 'comparison_results' not in st.session_state or st.session_state.comparison_results is None:
                        # Compare processed data with simulated API data
                        comparison_results = {"comparisons": []}
                        processed_group_col = f"{group_column}_processed"
                        processed_agg_col = f"{agg_column}_processed"

                        for idx, row in comparison_table.iterrows():
                            comp = {
                                "processed_label": row[processed_group_col] if pd.notna(row[processed_group_col]) else "N/A",
                                "processed_value": row[processed_agg_col] if pd.notna(row[processed_agg_col]) else 0,
                                "api_label": row[group_column] if pd.notna(row[group_column]) else "N/A",
                                "api_value": row["AggregatedValue"] if pd.notna(row["AggregatedValue"]) else 0,
                                "label_match": str(row[processed_group_col]) == str(row[group_column]) if pd.notna(row[processed_group_col]) and pd.notna(row[group_column]) else False,
                                "value_match": abs(row[processed_agg_col] - row["AggregatedValue"]) < 1e-10 if pd.notna(row[processed_agg_col]) and pd.notna(row["AggregatedValue"]) else False
                            }
                            comparison_results["comparisons"].append(comp)

                        # Store comparison results in session state for logging
                        st.session_state.comparison_results = comparison_results

                    # Add a column to indicate pass/fail with icons
                    comparison_table["Test_Result"] = comparison_table.apply(
                        lambda row: "✅" if abs(row[f"{agg_column}_processed"] - row["AggregatedValue"]) < 1e-10 else "❌",
                        axis=1
                    )
                    st.dataframe(comparison_table.style.set_properties(**{'text-align': 'center'}).set_table_styles(
                        [{'selector': 'th', 'props': [('text-align', 'center')]}]), use_container_width=True)

                    # Determine overall test status
                    test_status = "Passed" if all(comp['value_match'] for comp in st.session_state.comparison_results['comparisons']) else "Failed"

                    # Determine next test case ID
                    try:
                        existing_logs = pd.read_csv("VisualizerTests.csv")
                        next_test_no = existing_logs['Test Case ID'].max() + 1 if not existing_logs.empty else 1
                    except FileNotFoundError:
                        next_test_no = 1

                    # Submit button for logging
                    log_test_case_button = st.button("🔖 Log Test Case")

                    # Check if Test Case Description is empty
                    if log_test_case_button:
                        if st.session_state.test_case_description.strip() == "":
                            st.warning("⚠️ Please enter a Test Case Description before logging")
                        else:
                            try:
                                # Log the test result
                                result = log_test_result(
                                    next_test_no,
                                    st.session_state.test_case_description,
                                    generate_test_case_name(api_response['dataProcessing']),
                                    st.session_state.grouped_data,
                                    st.session_state.api_response,
                                    test_status
                                )
                                if result:
                                    st.success(result)
                            except Exception as e:
                                st.error(f"Error logging test case: {e}")

                except Exception as e:
                    st.error(f"Error processing results: {e}")

        except Exception as e:
            st.error(f"Error processing file: {e}")
    else:
        st.info("📤 Please upload an Excel or CSV file to start.")


if __name__ == "__main__":
    main()