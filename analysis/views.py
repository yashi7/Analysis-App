import os
import pandas as pd
import plotly.express as px
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

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
        required_columns = ["Service Type Offered", "Billed Weight", "Zone", "Client's Cost",
                            "Base Rate Charged", "Total Accessorial Charges", "Peak Calc", "Entered Weight"]
        
        for col in required_columns:
            if col not in df.columns:
                return JsonResponse({"error": f"Missing required column: {col}"})

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

        # Custom color scheme (softer shades)
        custom_colors = ["#410F0A", "#C57B25", "#F0D410", "#9B9F0E", "#457503"] 

        # Visualization 1: Total Spend by Weight Class
        weight_spend = df.groupby("Weight Class")["Client's Cost"].sum().reset_index()
        chart1 = px.bar(weight_spend, x="Weight Class", y="Client's Cost",
                        title="Total Spend by Weight Class", 
                        color_discrete_sequence=custom_colors)
        chart1.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 2: Total Spend by Service Type and Weight Break
        df_summary = df.groupby(["Service Type Offered", "Weight_Break"])["Client's Cost"].sum().reset_index()
        chart2 = px.bar(df_summary, x="Service Type Offered", y="Client's Cost", 
                        color="Weight_Break", title="Total Spend by Service Type and Weight Break", 
                        barmode='group', color_discrete_sequence=custom_colors)
        chart2.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 3: Total Accessorials by Service Type
        df_pie = df.groupby("Service Type Offered")["Total Accessorial Charges"].sum().reset_index()
        chart3 = px.pie(df_pie, names="Service Type Offered", values="Total Accessorial Charges", 
                        title="Total Accessorials by Service Type", 
                        color_discrete_sequence=custom_colors)
        chart3.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 4: Average Discount by Service Type and Weight Break
        df_avg_discount = df.groupby(["Service Type Offered", "Weight_Break"])["Peak Calc"].mean().reset_index()
        df_avg_discount["Average Discount"] = df_avg_discount["Peak Calc"] * 100
        chart4 = px.bar(df_avg_discount, x="Service Type Offered", y="Average Discount",
                        color="Weight_Break", title="Average Discount by Service Type and Weight Break", 
                        barmode='group', color_discrete_sequence=custom_colors)
        chart4.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 5: Distribution of Accessorial Charges
        base_rate_index = df.columns.get_loc("Base Rate Charged")
        fuel_charge_index = df.columns.get_loc("Fuel %")
        accessorial_cols = df.columns[base_rate_index + 1 : fuel_charge_index]

        df_accessorials = df[accessorial_cols].sum().reset_index()
        df_accessorials.columns = ["Accessorial", "Amount"]
        chart5 = px.bar(df_accessorials, x="Accessorial", y="Amount",
                        title="Distribution of Accessorial Charges", 
                        color='Amount', color_continuous_scale=custom_colors)
        chart5.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 6: Total Spend by Service Type and Zones
        df_summary_zone = df.groupby(["Service Type Offered", "Zone"])["Client's Cost"].sum().reset_index()
        chart6 = px.bar(df_summary_zone, x="Service Type Offered", y="Client's Cost",
                        color="Zone", title="Total Spend by Service Type and Zones", 
                        barmode='group', color_continuous_scale=custom_colors)
        chart6.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 7: Average Discount by Service Type and Zone
        df_avg_discount_zone = df.groupby(["Service Type Offered", "Zone"])["Peak Calc"].mean().reset_index()
        df_avg_discount_zone["Average Discount"] = df_avg_discount_zone["Peak Calc"] * 100
        chart7 = px.bar(df_avg_discount_zone, x="Service Type Offered", y="Average Discount",
                        color="Zone", title="Average Discount by Service Type and Zone", 
                        barmode='group', color_continuous_scale=custom_colors)
        chart7.update_traces(
            textfont=dict(size=12, family="Arial", color='black', weight='bold'),
            textposition='outside'
        )

        # Visualization 8: Total Accessorials by Service Type and Zone
        df_pie_zone = df.groupby(["Service Type Offered", "Zone"])["Total Accessorial Charges"].sum().reset_index()

        chart8 = []
        for service_type in df_pie_zone["Service Type Offered"].unique():
            df_filtered = df_pie_zone[df_pie_zone["Service Type Offered"] == service_type]
            fig = px.pie(df_filtered, 
                        names="Zone", 
                        values="Total Accessorial Charges",
                        title=f"{service_type} - Total Accessorials by Zone",
                        color_discrete_sequence=custom_colors)
            
            fig.update_traces(
                textfont=dict(size=12, family="Arial", color='black', weight='bold'),
                textposition='inside'
            )

            fig.update_layout(
                title={'font': {'size': 18, 'weight': 'bold'}},
                legend=dict(
                    font=dict(size=12, weight='bold')
            ))

            chart8.append(fig.to_html(full_html=False))

        # Analysis Logic
        clients_min_amount = df.groupby("Service Type Offered")["Base Rate Charged"].min().to_dict()

        summary = df.groupby(["Service Type Offered", "Weight Class", "Zone"]).agg(
            Count=("Service Type Offered", "size"),
            Total_Spend=("Client's Cost", "sum"),
            Base_Rate=("Base Rate Charged", "sum"),
            Total_Accessorial=("Total Accessorial Charges", "sum"),
            Disc=("Peak Calc", lambda x: round(x.max() * 100, 2)),
        ).reset_index()

        summary["Client's Min"] = summary["Service Type Offered"].map(clients_min_amount)

        # Save processed file
        output_file = os.path.join(settings.MEDIA_ROOT, "summary_output.xlsx")
        summary.to_excel(output_file, index=False, sheet_name="Summary")

        return render(request, "upload.html", {
            "summary_table": summary.to_html(classes="table table-striped", index=False),
            "file_url": f"/media/summary_output.xlsx",
            "chart1": chart1.to_html(full_html=False),
            "chart2": chart2.to_html(full_html=False),
            "chart3": chart3.to_html(full_html=False),
            "chart4": chart4.to_html(full_html=False),
            "chart5": chart5.to_html(full_html=False),
            "chart6": chart6.to_html(full_html=False),
            "chart7": chart7.to_html(full_html=False),
            "chart8": chart8
        })

    return render(request, "upload.html")