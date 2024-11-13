# app.py

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import logging
from api import data_queries as dq
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
from functools import wraps
from api.data_queries import (
    engine,
    search_drugs,
    get_drug_details,
    get_drug_properties,
    get_drug_interactions
)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add function entry/exit logging decorator
def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Entering {func.__name__} with args: {args}, kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

# Initialize the app with custom styling
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)
app.title = 'Drug Interaction Dashboard'

# Custom CSS styles
CUSTOM_STYLE = {
    'container': {
        'margin': '0 auto',
        'padding': '20px',
        'maxWidth': '1200px'
    },
    'header': {
        'textAlign': 'center',
        'color': '#2c3e50',
        'marginBottom': '30px'
    },
    'dropdown_container': {
        'textAlign': 'center',
        'marginBottom': '30px'
    },
    'section': {
        'marginBottom': '40px',
        'padding': '20px',
        'backgroundColor': '#ffffff',
        'borderRadius': '5px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }
}

# Enhanced app layout with better styling and organization
app.layout = html.Div([
    html.H1('Drug Interaction Dashboard', 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
    
    html.Div([
        dcc.Dropdown(
            id='drug-dropdown',
            options=[],
            value=None,
            placeholder='Type to search for drugs...',
            style={'width': '100%'}
        )
    ], style={'width': '80%', 'margin': '0 auto', 'marginBottom': '30px'}),
    
    dcc.Loading(
        id="loading-1",
        type="default",
        children=[
            html.Div([
                html.Div(id='drug-details'),
                html.Div(id='drug-properties'),
                html.Div(id='drug-interaction-table'),
                html.Div(id='drug-interaction-network')
            ], style={'width': '90%', 'margin': '0 auto'})
        ]
    )
], style={
    'padding': '20px',
    'minHeight': '100vh',
    'backgroundColor': '#f0f2f5'  # Light gray background
})

# Add custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .section {
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            body {
                background-color: #f5f5f5;
                font-family: Arial, sans-serif;
            }
            .dash-table-container {
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Callbacks for interactive features
@app.callback(
    [Output('drug-details', 'children'),
     Output('drug-properties', 'children'),
     Output('drug-interaction-table', 'children'),
     Output('drug-interaction-network', 'children')],
    Input('drug-dropdown', 'value'),
    prevent_initial_call=True
)
def update_drug_info(selected_drug):
    if not selected_drug:
        placeholder = html.Div("Select a drug to view details", 
                             style={'textAlign': 'center', 'padding': '20px'})
        return [placeholder] * 4

    try:
        # 1. Drug Details Section
        details_df = get_drug_details(selected_drug)
        details = html.Div([
            html.H3("Drug Details", style={'color': '#2c3e50', 'marginBottom': '15px'}),
            dash_table.DataTable(
                data=details_df.to_dict('records') if not details_df.empty else [],
                columns=[{"name": i, "id": i} for i in details_df.columns] if not details_df.empty else [],
                style_table={'overflowX': 'auto', 'border': '1px solid #ddd'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            ) if not details_df.empty else html.P("No details available")
        ], style={
            'padding': '20px',
            'margin': '10px',
            'backgroundColor': 'white',
            'border': '1px solid #ddd',
            'borderRadius': '5px'
        })

        # 2. Properties Section
        properties_df = get_drug_properties(selected_drug)
        properties = html.Div([
            html.H3("Drug Properties", style={'color': '#2c3e50', 'marginBottom': '15px'}),
            dash_table.DataTable(
                data=properties_df.to_dict('records') if not properties_df.empty else [],
                columns=[{"name": i, "id": i} for i in properties_df.columns] if not properties_df.empty else [],
                style_table={'overflowX': 'auto', 'border': '1px solid #ddd'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            ) if not properties_df.empty else html.P("No properties available")
        ], style={
            'padding': '20px',
            'margin': '10px',
            'backgroundColor': 'white',
            'border': '1px solid #ddd',
            'borderRadius': '5px'
        })

        # 3. Interactions Section
        interactions_df = get_drug_interactions(selected_drug)
        interactions = html.Div([
            html.H3("Drug Interactions", style={'color': '#2c3e50', 'marginBottom': '15px'}),
            dash_table.DataTable(
                data=interactions_df.to_dict('records') if not interactions_df.empty else [],
                columns=[{"name": i, "id": i} for i in interactions_df.columns] if not interactions_df.empty else [],
                style_table={'overflowX': 'auto', 'border': '1px solid #ddd'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            ) if not interactions_df.empty else html.P("No interactions found")
        ], style={
            'padding': '20px',
            'margin': '10px',
            'backgroundColor': 'white',
            'border': '1px solid #ddd',
            'borderRadius': '5px'
        })

        # 4. Network Section (placeholder)
        network = html.Div([
            html.H3("Network View", style={'color': '#2c3e50', 'marginBottom': '15px'}),
            html.P("Network visualization coming soon")
        ], style={
            'padding': '20px',
            'margin': '10px',
            'backgroundColor': 'white',
            'border': '1px solid #ddd',
            'borderRadius': '5px'
        })

        # Add debug prints
        print(f"Details DataFrame shape: {details_df.shape if not details_df.empty else 'Empty'}")
        print(f"Properties DataFrame shape: {properties_df.shape if not properties_df.empty else 'Empty'}")
        print(f"Interactions DataFrame shape: {interactions_df.shape if not interactions_df.empty else 'Empty'}")

        return [details, properties, interactions, network]

    except Exception as e:
        logger.error(f"Error updating drug info: {str(e)}", exc_info=True)
        error_div = html.Div([
            html.H4("Error", style={'color': 'red'}),
            html.P(str(e))
        ], style={
            'padding': '20px',
            'margin': '10px',
            'backgroundColor': 'white',
            'border': '1px solid red',
            'borderRadius': '5px'
        })
        return [error_div] * 4

@app.callback(
    Output('drug-dropdown', 'options'),
    Input('drug-dropdown', 'search_value'),
    prevent_initial_call=True
)
def update_dropdown_options(search_value):
    if not search_value:
        return []
    
    try:
        matching_drugs = search_drugs(search_value)
        options = [{'label': row['drug_name'], 'value': row['drug_name']} 
                  for _, row in matching_drugs.iterrows()]
        return options
    except Exception as e:
        logger.error(f"Error in dropdown search: {e}", exc_info=True)
        return []

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
