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
    return df

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
        data_table = "<p>No data available.</p>"
    else:
        production_chart = create_production_chart(df)
        quality_chart = create_quality_chart(df)
        deviation_chart = create_deviation_chart(df)
        production_pie = create_production_pie(df)
        quality_pie = create_quality_pie(df)
        recommendations = generate_recommendations(df)
        data_table = df.head(10).to_html(classes="table table-bordered table-striped table-sm", index=False)

    html_template = """
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <title>Production & Quality Dashboard</title>
        <link rel=\"stylesheet\" href=\"https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css\">
        <style>
            :root {
                --bg-color: #f4f6f9;
                --text-color: #343a40;
                --card-bg: #ffffff;
            }
            [data-theme='dark'] {
                --bg-color: #1e1e2f;
                --text-color: #f1f1f1;
                --card-bg: #2c2f3e;
            }
            body {
                background-color: var(--bg-color);
                color: var(--text-color);
            }
            .wrapper { display: flex; min-height: 100vh; }
            .sidebar { background-color: #343a40; width: 220px; padding: 20px 0; color: #fff; }
            .sidebar h2 { text-align: center; font-size: 1.5rem; font-weight: 600; margin-bottom: 30px; }
            .sidebar a { display: block; color: #adb5bd; text-decoration: none; padding: 12px 20px; transition: background 0.3s; }
            .sidebar a:hover { background-color: #495057; color: #fff; }
            .content { flex: 1; padding: 30px; overflow-y: auto; }
            h1 { font-size: 2rem; font-weight: 600; margin-bottom: 20px; }
            .card { border: none; background: var(--card-bg); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); margin-bottom: 30px; border-radius: 12px; }
            .card-header { background-color: transparent; font-weight: 600; font-size: 1.2rem; color: var(--text-color); }
            .plotly-graph-div { width: 100% !important; }
            form.filter-form { margin-bottom: 30px; }
            .table-container { max-height: 300px; overflow-y: auto; overflow-x: auto; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; background: #fff; }
            .dark-toggle { position: absolute; top: 15px; right: 20px; cursor: pointer; font-size: 1rem; background: #007bff; color: #fff; border: none; padding: 6px 14px; border-radius: 5px; }
            @media (max-width: 768px) {
                .wrapper { flex-direction: column; }
                .sidebar { width: 100%; height: auto; }
            }
        </style>
    </head>
    <body>
    <button class=\"dark-toggle\" onclick=\"toggleTheme()\">Toggle Theme</button>
    <div class=\"wrapper\">
        <div class=\"sidebar\">
            <h2>Dashboard</h2>
            <a href=\"#\">Overview</a>
            <a href=\"#\">Production</a>
            <a href=\"#\">Quality</a>
            <a href=\"#\">Recommendations</a>
        </div>
        <div class=\"content\">
            <h1>Production & Quality Insights Dashboard</h1>
            <form method=\"POST\" class=\"filter-form form-inline\">
                <label for=\"start_date\">Start:</label>
                <input type=\"date\" name=\"start_date\" value=\"{{ start_date }}\" class=\"form-control mx-2\">
                <label for=\"end_date\">End:</label>
                <input type=\"date\" name=\"end_date\" value=\"{{ end_date }}\" class=\"form-control mx-2\">
                <button type=\"submit\" class=\"btn btn-primary\">Filter</button>
            </form>

            <div class=\"card\"><div class=\"card-header\">Data Preview</div><div class=\"card-body table-container\">{{ data_table|safe }}</div></div>
            <div class=\"card\"><div class=\"card-header\">Planned vs Actual Production</div><div class=\"card-body\">{{ production_chart|safe }}</div></div>
            <div class=\"card\"><div class=\"card-header\">Planned vs Actual Quality</div><div class=\"card-body\">{{ quality_chart|safe }}</div></div>
            <div class=\"card\"><div class=\"card-header\">Deviation Analysis</div><div class=\"card-body\">{{ deviation_chart|safe }}</div></div>
            <div class=\"row\">
                <div class=\"col-md-6\"><div class=\"card\"><div class=\"card-header\">Production Contribution</div><div class=\"card-body\">{{ production_pie|safe }}</div></div></div>
                <div class=\"col-md-6\"><div class=\"card\"><div class=\"card-header\">Quality Contribution</div><div class=\"card-body\">{{ quality_pie|safe }}</div></div></div>
            </div>
            <div class=\"card\"><div class=\"card-header\">Recommendations</div><div class=\"card-body\"><ul>{% for rec in recommendations %}<li>{{ rec }}</li>{% endfor %}</ul></div></div>
        </div>
    </div>
    <script>
        function toggleTheme() {
            const current = document.body.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }
        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.body.setAttribute('data-theme', savedTheme);
        });
    </script>
    </body>
    </html>
    """
    return render_template_string(html_template,
                                  start_date=start_date,
                                  end_date=end_date,
                                  data_table=data_table,
                                  production_chart=production_chart,
                                  quality_chart=quality_chart,
                                  deviation_chart=deviation_chart,
                                  production_pie=production_pie,
                                  quality_pie=quality_pie,
                                  recommendations=recommendations)

if __name__ == "__main__":
    app.run(debug=True)
