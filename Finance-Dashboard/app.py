import io
import base64
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State, dash_table

# --- Demo-Daten (falls nichts hochgeladen wird) ---
def demo_df():
    years = list(range(2016, 2026))
    revenue = [1000,1050,1102,1158,1216,1276,1340,1407,1477,1551]
    costs   = [800,824,849,874,900,927,955,984,1013,1044]
    df = pd.DataFrame({"Year": years, "Revenue": revenue, "Costs": costs})
    df["Profit"] = df["Revenue"] - df["Costs"]
    df["Profit_Margin_%"] = (df["Profit"] / df["Revenue"] * 100).round(2)
    return df

app = Dash(__name__, title="Financial KPI Dashboard")
app.layout = html.Div(
    style={"maxWidth": "1100px", "margin": "0 auto", "fontFamily": "system-ui, sans-serif"},
    children=[
        html.H1("Financial KPI Dashboard"),
        html.P("Lade eine CSV (Spalten: Year, Revenue, Costs) hoch – oder nutze die Demo-Daten."),

        dcc.Upload(
            id="upload",
            children=html.Div(["📤 Datei hierher ziehen oder klicken, um auszuwählen"]),
            style={
                "width": "100%", "height": "70px", "lineHeight": "70px",
                "borderWidth": "2px", "borderStyle": "dashed", "borderRadius": "8px",
                "textAlign": "center", "marginBottom": "16px"
            },
            multiple=False,
        ),

        html.Div([
            html.Label("Jahre filtern"),
            dcc.RangeSlider(
                id="year-range",
                min=2016, max=2025, value=[2018, 2025], step=1,
                marks={y: str(y) for y in range(2016, 2026)}
            ),
        ], style={"marginBottom": "12px"}),

        html.Div(id="kpi-cards", style={"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "12px"}),

        dcc.Tabs(id="tabs", value="tab-trend", children=[
            dcc.Tab(label="Zeitreihe (Linie)", value="tab-trend"),
            dcc.Tab(label="Vergleich (Balken)", value="tab-bars"),
            dcc.Tab(label="Tabelle", value="tab-table"),
        ], style={"marginTop": "8px"}),

        html.Div(id="tab-content", style={"marginTop": "8px"}),

        # versteckt: Daten-Cache
        dcc.Store(id="data-store")
    ]
)

# --- Helper ---
def parse_contents(contents: str) -> pd.DataFrame:
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    # Minimal-Validierung
    needed = {"Year", "Revenue", "Costs"}
    if not needed.issubset(df.columns):
        raise ValueError(f"CSV benötigt Spalten: {needed}")
    df = df.copy()
    df["Profit"] = df["Revenue"] - df["Costs"]
    df["Profit_Margin_%"] = (df["Profit"] / df["Revenue"] * 100).round(2)
    return df

# --- Callbacks ---
@app.callback(
    Output("data-store", "data"),
    Input("upload", "contents"),
    prevent_initial_call=False
)
def load_data(uploaded_contents):
    try:
        if uploaded_contents:
            df = parse_contents(uploaded_contents)
        else:
            df = demo_df()
        return df.to_dict("records")
    except Exception as e:
        # Fallback auf Demo bei Fehler
        return demo_df().to_dict("records")

@app.callback(
    Output("kpi-cards", "children"),
    Output("tab-content", "children"),
    Input("data-store", "data"),
    Input("year-range", "value"),
    Input("tabs", "value")
)
def update_view(records, year_range, active_tab):
    df = pd.DataFrame(records) if records else demo_df()
    df = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])]

    total_rev = df["Revenue"].sum()
    total_profit = df["Profit"].sum()
    avg_margin = (df["Profit"].sum() / df["Revenue"].sum() * 100).round(2) if total_rev else 0.0

    card = lambda title, value: html.Div(
        [html.Div(title, style={"fontSize": "14px", "opacity": 0.7}),
         html.Div(value, style={"fontSize": "22px", "fontWeight": 700})],
        style={"border":"1px solid #ddd","borderRadius":"10px","padding":"14px","background":"#fafafa"}
    )

    kpis = [
        card("Gesamtumsatz", f"{total_rev:,.0f}"),
        card("Gesamtgewinn", f"{total_profit:,.0f}"),
        card("Ø Marge", f"{avg_margin:.2f}%"),
    ]

    if active_tab == "tab-trend":
        fig = px.line(df, x="Year", y=["Revenue","Costs","Profit"], markers=True, title="Zeitreihe")
        return kpis, dcc.Graph(figure=fig, responsive=True, style={"height":"420px"})
    elif active_tab == "tab-bars":
        long = df.melt(id_vars="Year", value_vars=["Revenue","Costs","Profit"], var_name="Metric", value_name="Value")
        fig = px.bar(long, x="Year", y="Value", color="Metric", barmode="group", title="Vergleich")
        return kpis, dcc.Graph(figure=fig, responsive=True, style={"height":"420px"})
    else:
        table = dash_table.DataTable(
            data=df.round(2).to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
            page_size=10,
            style_table={"overflowX":"auto"},
        )
        return kpis, table

if __name__ == "__main__":
    app.run_server(debug=True)
