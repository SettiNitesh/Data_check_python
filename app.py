import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Title and file upload
st.title("Data Analyzer Web App")
st.sidebar.title("Upload and Analyze Data")

# File upload with support for .csv and Excel files
uploaded_file = st.sidebar.file_uploader("Upload an Excel or CSV File", type=["xls", "xlsx", "csv"])
if uploaded_file:
    try:
        # Detect file type and load data
        if uploaded_file.name.endswith(".csv"):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        # Display the uploaded data
        st.subheader("Uploaded Data")
        st.dataframe(data)

        # Select a column for grouping
        group_column = st.sidebar.selectbox("Select a Column to Group By", data.columns)

        # Select a numeric column for aggregation
        numeric_columns = data.select_dtypes(include=["number"]).columns
        agg_column = st.sidebar.selectbox("Select a Numeric Column to Analyze", numeric_columns)

        if group_column and agg_column:
            # Group by the selected column and calculate metrics
            grouped_data = data.groupby(group_column)[agg_column].agg(
                Sum="sum",
                Count="count",
                Average="mean",
                Median="median",
                Min="min",
                Max="max"
            ).reset_index()

            # Display grouped data
            st.subheader(f"Metrics by '{group_column}'")
            st.dataframe(grouped_data)

            # Plot the metrics
            st.subheader("Bar Chart")
            fig, ax = plt.subplots(figsize=(12, 6))
            grouped_data.plot(
                x=group_column,
                y=["Sum", "Average", "Median"],
                kind="bar",
                ax=ax,
                colormap="viridis"
            )
            ax.set_title(f"Metrics of {agg_column} by {group_column}")
            ax.set_xlabel(group_column)
            ax.set_ylabel("Values")
            ax.tick_params(axis="x", rotation=45)

            st.pyplot(fig)

    except Exception as e:
        st.error(f"Error processing the file: {e}")
else:
    st.info("Please upload an Excel or CSV file to start.")
