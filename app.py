from flask import Flask, render_template_string, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

app = Flask(__name__)
pio.templates.default = "plotly_white"

def load_data():
    file_path = "datasets.xlsx"
    df = pd.read_excel(file_path)

    rename_map = {
        "ClearanceDate": "Date",
        "PlanThickness": "Planned_Production",
        "FinalThk": "Actual_Production",
        "Order Yield Strength": "Planned_Quality",
        "Yield Strength": "Actual_Quality"
    }
    df.rename(columns=rename_map, inplace=True)

    df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.tz_localize(None)
    for col in ["Planned_Production", "Actual_Production", "Planned_Quality", "Actual_Quality"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Date", "Planned_Production", "Actual_Production", "Planned_Quality", "Actual_Quality"])
    return df

def process_data(df):
    df["Production_Deviation"] = df["Actual_Production"] - df["Planned_Production"]
    df["Quality_Deviation"] = df["Actual_Quality"] - df["Planned_Quality"]

    df = df.sort_values('Date', ascending=False)
    return df

def prepare_table_slides(df):
    """Create multiple slides for the table swiper based on data categories."""
    slides = []

    overview_columns = ["Date", "Planned_Production", "Actual_Production", "Planned_Quality", "Actual_Quality"]
    overview_df = df[overview_columns].head(15).copy()
    overview_df["Date"] = overview_df["Date"].dt.strftime("%Y-%m-%d")
    
    slides.append({
        "title": "Overview",
        "content": overview_df.to_html(classes="table table-bordered table-striped table-sm", index=False)
    })
    
    prod_columns = ["Date", "Planned_Production", "Actual_Production", "Production_Deviation"]
    prod_df = df[prod_columns].head(15).copy()
    prod_df["Date"] = prod_df["Date"].dt.strftime("%Y-%m-%d")
    prod_df["Production_Deviation"] = prod_df["Production_Deviation"].round(2)
    
    slides.append({
        "title": "Production Analysis",
        "content": prod_df.to_html(classes="table table-bordered table-striped table-sm", index=False)
    })
    
    qual_columns = ["Date", "Planned_Quality", "Actual_Quality", "Quality_Deviation"]
    qual_df = df[qual_columns].head(15).copy()
    qual_df["Date"] = qual_df["Date"].dt.strftime("%Y-%m-%d")
    qual_df["Quality_Deviation"] = qual_df["Quality_Deviation"].round(2)
    
    slides.append({
        "title": "Quality Analysis",
        "content": qual_df.to_html(classes="table table-bordered table-striped table-sm", index=False)
    })
    
    summary_data = {
        "Metric": ["Total Planned Production", "Total Actual Production", "Avg Production Deviation",
                   "Total Planned Quality", "Total Actual Quality", "Avg Quality Deviation"],
        "Value": [
            f"{df['Planned_Production'].sum():.2f}",
            f"{df['Actual_Production'].sum():.2f}",
            f"{df['Production_Deviation'].mean():.2f}",
            f"{df['Planned_Quality'].sum():.2f}",
            f"{df['Actual_Quality'].sum():.2f}",
            f"{df['Quality_Deviation'].mean():.2f}"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    slides.append({
        "title": "Summary Statistics",
        "content": summary_df.to_html(classes="table table-bordered table-striped table-sm", index=False)
    })
    
    return slides

def create_production_chart(df):
    fig = px.line(df, x="Date", y=["Planned_Production", "Actual_Production"],
                  title="Planned vs Actual Production", markers=True)
    fig.update_layout(legend_title_text='Production', margin=dict(t=40, b=20))
    return fig.to_html(full_html=False)

def create_quality_chart(df):
    fig = px.line(df, x="Date", y=["Planned_Quality", "Actual_Quality"],
                  title="Planned vs Actual Quality", markers=True)
    fig.update_layout(legend_title_text='Quality', margin=dict(t=40, b=20))
    return fig.to_html(full_html=False)

def create_deviation_chart(df):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Production Deviation", "Quality Deviation"))
    fig.add_trace(go.Box(y=df["Production_Deviation"], name="Production Deviation"), row=1, col=1)
    fig.add_trace(go.Box(y=df["Quality_Deviation"], name="Quality Deviation"), row=1, col=2)
    fig.update_layout(title_text="Deviation Analysis", showlegend=False, margin=dict(t=40, b=20))
    return fig.to_html(full_html=False)

def create_production_pie(df):
    labels = ['Planned', 'Actual']
    values = [df["Planned_Production"].sum(), df["Actual_Production"].sum()]
    fig = px.pie(values=values, names=labels, title="Production Contribution")
    fig.update_traces(textposition='outside', textinfo='percent+label', pull=[0.05, 0],
                      marker=dict(line=dict(color='white', width=2)))
    fig.update_layout(margin=dict(t=60, b=40, l=20, r=20), showlegend=True)
    return fig.to_html(full_html=False)

def create_quality_pie(df):
    labels = ['Planned', 'Actual']
    values = [df["Planned_Quality"].sum(), df["Actual_Quality"].sum()]
    fig = px.pie(values=values, names=labels, title="Quality Contribution", hole=0.3)
    fig.update_traces(textposition='outside', textinfo='percent+label', pull=[0.05, 0],
                      marker=dict(line=dict(color='white', width=2)))
    fig.update_layout(margin=dict(t=60, b=40, l=20, r=20), showlegend=True)
    return fig.to_html(full_html=False)

def generate_recommendations(df):
    recommendations = []
    avg_prod_dev = df["Production_Deviation"].mean()
    avg_qual_dev = df["Quality_Deviation"].mean()

    if avg_prod_dev > 0:
        recommendations.append("Production exceeding plan on average. Consider revising targets.")
    elif avg_prod_dev < 0:
        recommendations.append("Production below plan. Investigate bottlenecks or inefficiencies.")
    else:
        recommendations.append("Production closely aligns with planning.")

    if avg_qual_dev > 0:
        recommendations.append("Quality is higher than planned - good, but double-check consistency.")
    elif avg_qual_dev < 0:
        recommendations.append("Quality below expectation. Investigate root causes.")
    else:
        recommendations.append("Quality is on target.")

    return recommendations

@app.route("/", methods=["GET", "POST"])
def index():
    df = load_data()
    df = process_data(df)

    min_date_raw = df["Date"].min()
    max_date_raw = df["Date"].max()
    min_date = min_date_raw.strftime("%Y-%m-%d") if pd.notna(min_date_raw) else ""
    max_date = max_date_raw.strftime("%Y-%m-%d") if pd.notna(max_date_raw) else ""

    start_date = request.form.get("start_date", min_date)
    end_date = request.form.get("end_date", max_date)

    try:
        start_date_obj = pd.to_datetime(start_date).tz_localize(None)
        end_date_obj = pd.to_datetime(end_date).tz_localize(None)
        df = df[(df["Date"] >= start_date_obj) & (df["Date"] <= end_date_obj)]
    except Exception:
        pass

    if df.empty:
        production_chart = quality_chart = deviation_chart = production_pie = quality_pie = "<p>No data to display.</p>"
        recommendations = ["No data in the selected range."]
        table_slides = [{"title": "No Data", "content": "<p>No data available in the selected range.</p>"}]
    else:
        production_chart = create_production_chart(df)
        quality_chart = create_quality_chart(df)
        deviation_chart = create_deviation_chart(df)
        production_pie = create_production_pie(df)
        quality_pie = create_quality_pie(df)
        recommendations = generate_recommendations(df)
        table_slides = prepare_table_slides(df)

    return render_template_string(
        open("templates/dashboard.html").read(),
        start_date=start_date,
        end_date=end_date,
        min_date=min_date,
        max_date=max_date,
        table_slides=table_slides,
        production_chart=production_chart,
        quality_chart=quality_chart,
        deviation_chart=deviation_chart,
        production_pie=production_pie,
        quality_pie=quality_pie,
        recommendations=recommendations
    )

if __name__ == "__main__":
    app.run(debug=True)