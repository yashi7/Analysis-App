import os
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.utils.safestring import mark_safe
import openai
from openai import OpenAI
import json  # Import json for serialization
import numpy as np
def generate_insights(summary):
    """
    Generate insights from the summary table using OpenAI GPT.
    """
    # Convert the summary DataFrame to a string
    summary_text = summary.to_string()

    # Create a prompt for OpenAI GPT
    prompt = f"""
    The following is a summary table of shipping data:
    {summary_text}

    Analyze the data and provide key insights in bullet points. Focus on trends, anomalies, and actionable recommendations.
    """

    # Check for API key before initializing OpenAI client
    if not settings.OPENAI_API_KEY:
        return "Please add an OpenAI API key to generate insights."

    # Initialize the OpenAI client
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use the GPT-3.5 model
        messages=[
            {"role": "system", "content": "You are a data analyst. Provide concise and actionable insights based on the data provided."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,  # Adjust based on the desired length of insights
        temperature=0.7,  # Controls creativity (0.7 is a good balance)
    )

    # Extract the generated insights
    insights = response.choices[0].message.content.strip()
    return insights

def generate_merged_table_html(df):
    # Map service types to Express, Ground, and Smartpost/Surepost
    def map_service_type(service):
        if "Ground" in service:
            return "Ground"
        elif "Smartpost" in service or "Surepost" in service:
            return "Smartpost/Surepost"
        else:
            return "Express"

    # Apply the mapping
    df["Mapped Service Type"] = df["Service Type Offered"].apply(map_service_type)

    # Sort the DataFrame by the mapped service type
    df = df.sort_values(by=["Mapped Service Type", "Service Type Offered", "Weight Class", "Zone"])

    html = '<table class="table table-striped">'

    # Add Table Header
    html += "<thead><tr>"
    for col in df.columns:
        if col != "Mapped Service Type":  # Exclude the mapped service type from the table header
            html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    prev_service = None
    prev_weight_class = None
    prev_mapped_service = None
    service_rowspan = {}
    weight_rowspan = {}

    # Calculate row spans
    df_grouped = df.groupby(["Mapped Service Type", "Service Type Offered", "Weight Class"]).size().reset_index(name='count')

    # Adjust row spans to account for Weight Class Total rows
    for _, row in df_grouped.iterrows():
        service_rowspan[row["Service Type Offered"]] = service_rowspan.get(row["Service Type Offered"], 0) + row["count"] + 1  # +1 for the Weight Class Total row
        weight_rowspan[(row["Service Type Offered"], row["Weight Class"])] = row["count"]

    # Group by Mapped Service Type and Service Type Offered
    grouped = df.groupby(["Mapped Service Type", "Service Type Offered"])

    # Initialize a list to track processed mapped service types
    processed_mapped_services = []

    for (mapped_service, service), group in grouped:
        # Add rows for the current service type inside a collapsible section
        html += f'<tbody class="collapse show" id="collapse-{service}">'

        # Group by Weight Class within the current service type
        weight_class_grouped = group.groupby("Weight Class")

        for weight_class, weight_class_group in weight_class_grouped:
            for _, row in weight_class_group.iterrows():
                html += "<tr>"

                # Merge "Service Type Offered" if it's the first row of the service
                if row["Service Type Offered"] != prev_service:
                    html += f'<td rowspan="{service_rowspan[row["Service Type Offered"]]}">{row["Service Type Offered"]}</td>'
                    prev_service = row["Service Type Offered"]

                # Merge "Weight Class" if it's the first row of the weight class
                if row["Weight Class"] != prev_weight_class or prev_service != row["Service Type Offered"]:
                    html += f'<td rowspan="{weight_rowspan[(row["Service Type Offered"], row["Weight Class"])]}">{row["Weight Class"]}</td>'
                    prev_weight_class = row["Weight Class"]

                # Add other columns (skip first two columns as they are already added)
                for col in df.columns[2:]:
                    if col == "Mapped Service Type":
                        continue  # Skip the mapped service type column
                    value = row[col]
                    if col in ["Total_Spend", "Base_Rate", "Total_Accessorial", "Client's Min", "Savings", "Offered_Cost"]:
                        value = f"${round(value, 2):,.2f}"
                    elif col in ["Spend %", "Base Rate %", "Accessorial %", "Max Disc"]:
                        value = f"{round(value, 2):,.2f}%"
                    elif col == "Count":
                        value = int(value)
                    html += f"<td>{value}</td>"

                html += "</tr>"

            # Add Weight Class Total Row
            weight_class_total = weight_class_group.sum(numeric_only=True)
            weight_class_total["Service Type Offered"] = f"Total for {weight_class}"
            weight_class_total["Weight Class"] = ""
            weight_class_total["Zone"] = ""
            weight_class_total["Count"] = weight_class_group["Count"].sum()
            weight_class_total["Spend %"] = weight_class_group["Spend %"].sum()
            weight_class_total["Base Rate %"] = weight_class_group["Base Rate %"].sum()
            weight_class_total["Accessorial %"] = weight_class_group["Accessorial %"].sum()
            weight_class_total["Max Disc"] = weight_class_group["Max Disc"].max()
            weight_class_total["Client's Min"] = weight_class_group["Client's Min"].min()
            weight_class_total["Savings"] = weight_class_group["Savings"].sum()
            weight_class_total["Offered_Cost"] = weight_class_group["Offered_Cost"].sum()

            html += "<tr style='background-color: #ffe0b2;'>"
            html += f"<td><strong>Total for {weight_class}</strong></td>"
            for col in df.columns[2:]:
                if col == "Mapped Service Type":
                    continue  # Skip the mapped service type column
                value = weight_class_total[col]
                if col in ["Total_Spend", "Base_Rate", "Total_Accessorial", "Client's Min", "Savings", "Offered_Cost"]:
                    value = f"${round(value, 2):,.2f}"
                elif col in ["Spend %", "Base Rate %", "Accessorial %", "Max Disc"]:
                    value = f"{round(value, 2):,.2f}%"
                elif col == "Count":
                    value = int(value)
                html += f"<td><strong>{value}</strong></td>"
            html += "</tr>"

        # Add Total Row for the current Service Type
        total_row = group.sum(numeric_only=True)
        total_row["Service Type Offered"] = "Total"
        total_row["Weight Class"] = ""
        total_row["Zone"] = ""
        total_row["Count"] = group["Count"].sum()
        total_row["Spend %"] = group["Spend %"].sum()
        total_row["Base Rate %"] = group["Base Rate %"].sum()
        total_row["Accessorial %"] = group["Accessorial %"].sum()
        total_row["Max Disc"] = group["Max Disc"].max()
        total_row["Client's Min"] = group["Client's Min"].min()
        total_row["Savings"] = group["Savings"].sum()
        total_row["Offered_Cost"] = group["Offered_Cost"].sum()

        html += "<tr style='background-color: #e0f7fa;'>"
        html += f"<td></td>"  # Empty cell for Service Type Offered (already spanned)
        html += f"<td><strong>Total for {service}</strong></td>"
        for col in df.columns[2:]:
            if col == "Mapped Service Type":
                continue  # Skip the mapped service type column
            value = total_row[col]
            if col in ["Total_Spend", "Base_Rate", "Total_Accessorial", "Client's Min", "Savings", "Offered_Cost"]:
                value = f"${round(value, 2):,.2f}"
            elif col in ["Spend %", "Base Rate %", "Accessorial %", "Max Disc"]:
                value = f"{round(value, 2):,.2f}%"
            elif col == "Count":
                value = int(value)
            html += f"<td><strong>{value}</strong></td>"
        html += "</tr>"

        html += '</tbody>'

        # Check if all services under the current mapped service type have been processed
        if mapped_service not in processed_mapped_services:
            # Check if this is the last service under the current mapped service type
            last_service_in_mapped_type = df[df["Mapped Service Type"] == mapped_service]["Service Type Offered"].iloc[-1]
            if service == last_service_in_mapped_type:
                # Calculate totals for the current mapped service type
                mapped_total = df[df["Mapped Service Type"] == mapped_service].sum(numeric_only=True)
                mapped_total["Service Type Offered"] = f"Total for {mapped_service}"
                mapped_total["Weight Class"] = ""
                mapped_total["Zone"] = ""
                mapped_total["Count"] = df[df["Mapped Service Type"] == mapped_service]["Count"].sum()
                mapped_total["Spend %"] = df[df["Mapped Service Type"] == mapped_service]["Spend %"].sum()
                mapped_total["Base Rate %"] = df[df["Mapped Service Type"] == mapped_service]["Base Rate %"].sum()
                mapped_total["Accessorial %"] = df[df["Mapped Service Type"] == mapped_service]["Accessorial %"].sum()
                mapped_total["Max Disc"] = df[df["Mapped Service Type"] == mapped_service]["Max Disc"].max()
                mapped_total["Client's Min"] = df[df["Mapped Service Type"] == mapped_service]["Client's Min"].min()
                mapped_total["Savings"] = df[df["Mapped Service Type"] == mapped_service]["Savings"].sum()
                mapped_total["Offered_Cost"] = df[df["Mapped Service Type"] == mapped_service]["Offered_Cost"].sum()

                html += "<tr style='background-color: #a8e6cf;'>"
                html += f"<td></td>"  # Empty cell for Service Type Offered (already spanned)
                html += f"<td><strong>{mapped_total['Service Type Offered']}</strong></td>"
                for col in df.columns[2:]:
                    if col == "Mapped Service Type":
                        continue  # Skip the mapped service type column
                    value = mapped_total[col]
                    if col in ["Total_Spend", "Base_Rate", "Total_Accessorial", "Client's Min", "Savings", "Offered_Cost"]:
                        value = f"${round(value, 2):,.2f}"
                    elif col in ["Spend %", "Base Rate %", "Accessorial %", "Max Disc"]:
                        value = f"{round(value, 2):,.2f}%"
                    elif col == "Count":
                        value = int(value)
                    html += f"<td><strong>{value}</strong></td>"
                html += "</tr>"

                # Mark this mapped service type as processed
                processed_mapped_services.append(mapped_service)

    # Add Whole Total Row
    whole_total_row = df.sum(numeric_only=True)
    whole_total_row["Service Type Offered"] = "Whole Total"
    whole_total_row["Weight Class"] = ""
    whole_total_row["Zone"] = ""
    whole_total_row["Count"] = df["Count"].sum()
    whole_total_row["Spend %"] = df["Spend %"].sum()
    whole_total_row["Base Rate %"] = df["Base Rate %"].sum()
    whole_total_row["Accessorial %"] = df["Accessorial %"].sum()
    whole_total_row["Max Disc"] = df["Max Disc"].max()
    whole_total_row["Client's Min"] = df["Client's Min"].min()
    whole_total_row["Savings"] = df["Savings"].sum()
    whole_total_row["Offered_Cost"] = df["Offered_Cost"].sum()

    html += "<tfoot>"
    html += "<tr style='background-color: #a8e6cf;'>"
    html += f"<td></td>"  # Empty cell for Service Type Offered (already spanned)
    html += f"<td><strong>Whole Total</strong></td>"
    for col in df.columns[2:]:
        if col == "Mapped Service Type":
            continue  # Skip the mapped service type column
        value = whole_total_row[col]
        if col in ["Total_Spend", "Base_Rate", "Total_Accessorial", "Client's Min", "Savings", "Offered_Cost"]:
            value = f"${round(value, 2):,.2f}"
        elif col in ["Spend %", "Base Rate %", "Accessorial %", "Max Disc"]:
            value = f"{round(value, 2):,.2f}%"
        elif col == "Count":
            value = int(value)
        html += f"<td><strong>{value}</strong></td>"
    html += "</tr>"
    html += "</tfoot>"

    html += "</tbody></table>"
    return mark_safe(html)
def analyze_excel(request):
    if request.method == "POST" and request.FILES.get("file"):
        excel_file = request.FILES["file"]
        file_path = os.path.join(settings.MEDIA_ROOT, excel_file.name)

        with open(file_path, "wb+") as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        # Read the Excel file
        df = pd.read_excel(file_path, skiprows=1)

        # Ensure required columns exist
        required_columns = [
            "Service Type Offered", "Billed Weight", "Zone", "Client's Cost",
            "Base Rate Charged", "Total Accessorial Charges", "Peak Calc", "Entered Weight", "Offered Cost"
        ]

        for col in required_columns:
            if col not in df.columns:
                return JsonResponse({"error": f"Missing required column: {col}"})

        # Handle NaN or inf values in the "Zone" column
        if df["Zone"].isna().any() or np.isinf(df["Zone"]).any():
            df["Zone"] = df["Zone"].fillna(0).replace([np.inf, -np.inf], 0)

        # Convert "Zone" column to integers
        df["Zone"] = df["Zone"].astype(int)

        # Weight Classification
        def classify_weight(weight):
            if weight <= 5:
                return "1-5 lbs"
            elif weight <= 10:
                return "6-10 lbs"
            elif weight <= 20:
                return "11-20 lbs"
            elif weight <= 30:
                return "21-30 lbs"
            else:
                return "31+ lbs"

        # Apply classification
        df["Weight Class"] = df["Billed Weight"].apply(classify_weight)
        df["Weight_Break"] = df["Entered Weight"].apply(classify_weight)

        # Analysis Logic
        clients_min_amount = df.groupby("Service Type Offered")[
            "Base Rate Charged"].min().to_dict()

        # Create the summary DataFrame with additional percentage columns
        summary = df.groupby(["Service Type Offered", "Weight Class", "Zone"]).agg(
            Count=("Service Type Offered", "size"),
            Total_Spend=("Client's Cost", "sum"),
            Base_Rate=("Base Rate Charged", "sum"),
            Total_Accessorial=("Total Accessorial Charges", "sum"),
            Offered_Cost=("Offered Cost", "sum"),  # Add Offered Cost to the summary
            Disc=("Peak Calc", lambda x: round(x.max() * 100, 2)),
        ).reset_index()

        # Add percentage calculations
        summary["Base Rate %"] = (
            summary["Base_Rate"] / summary["Total_Spend"] * 100).fillna(0).round(2)
        summary["Accessorial %"] = (
            summary["Total_Accessorial"] / summary["Total_Spend"] * 100).fillna(0).round(2)
        summary["Max Disc"] = summary["Disc"]
        summary["Max Disc"] = summary["Max Disc"].round(2)

        # Calculate Total Spend Percentage
        grand_total_spend = summary["Total_Spend"].sum()
        summary["Spend %"] = (summary["Total_Spend"] /
                              grand_total_spend * 100).fillna(0).round(2)

        # Add Client's Min Amount
        summary["Client's Min"] = summary["Service Type Offered"].map(
            clients_min_amount)

        # Calculate Savings
        summary["Savings"] = df["Client's Cost"] - df["Offered Cost"]
        summary["Savings"] = summary["Savings"].round(2)

        # Reorder columns for better readability
        summary = summary[[
            "Service Type Offered", "Weight Class", "Zone", "Count", "Total_Spend", "Spend %",
            "Base_Rate", "Base Rate %", "Total_Accessorial", "Accessorial %", "Offered_Cost", "Max Disc", "Client's Min", "Savings"
        ]]
        summary = summary.round(2)

        # Generate the summary table HTML
        merged_table_html = generate_merged_table_html(summary)

        # Generate AI insights
        insights = generate_insights(summary)

        # Convert summary DataFrame to JSON for JavaScript
        summary["Weight Class"] = summary["Weight Class"].astype(str)
        summary_json = summary.to_json(orient='records')

        return render(request, "upload.html", {
            "summary_table": merged_table_html,
            "insights": insights,
            "summary_data": summary_json,  # Pass summary data as JSON
        })

    return render(request, "upload.html")