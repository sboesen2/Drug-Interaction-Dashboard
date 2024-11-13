# app.py

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
from api import data_queries as dq  # Corrected import statement
import dash.exceptions
import logging
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize the app
app = dash.Dash(__name__)
server = app.server  # For deployment purposes

# Fetch top 50 drugs for initial dropdown options
try:
    top_drugs_df = dq.get_top_50_drugs()
    initial_options = [{'label': name, 'value': name} for name in top_drugs_df['drug_name']]
    logger.info("Successfully fetched top 50 drugs.")
except Exception as e:
    logger.error(f"Error fetching top 50 drugs: {e}")
    initial_options = []

# Layout of the app
app.layout = html.Div([
    html.H1("Drug Interaction Dashboard", style={'textAlign': 'center'}),
    html.Br(),

    # Drug Search Dropdown
    html.Div([
        html.Label("Select a Drug", style={'fontSize': 20}),
        dcc.Dropdown(
            id='drug-dropdown',
            options=initial_options,
            placeholder="Type or select a drug name...",
            style={'width': '50%'},
            clearable=True  # Allow users to clear the selection
        ),
    ], style={'textAlign': 'center'}),

    html.Hr(),

    # Section to display drug details
    html.Div(id='drug-details', style={'textAlign': 'center'}),

    html.Hr(),

    # Section to display drug properties graph
    html.Div(id='drug-properties-graph', style={'textAlign': 'center'}),

    html.Hr(),

    # Section to display drug interactions as a table
    html.Div(id='drug-interaction-table', style={'textAlign': 'center'}),

    html.Hr(),

    # Optional: Drug Interactions Network Graph
    html.Div(id='drug-interaction-network', style={'textAlign': 'center'})
])

# Callback to update the dropdown with available drug names based on search
@app.callback(
    Output('drug-dropdown', 'options'),
    [Input('drug-dropdown', 'search_value')]
)
def update_dropdown_options(search_value):
    """
    Updates the dropdown options based on user search input.
    If no search is performed, retains the initial top 50 options.
    """
    logger.debug(f"Search value entered: {search_value}")

    # If no search value, return initial options
    if not search_value:
        logger.debug("No search value provided. Returning initial options.")
        return initial_options

    try:
        # Fetch list of drug names from the database using search value
        drugs_df = dq.search_drugs(search_value)
        logger.debug(f"Number of drugs found: {len(drugs_df)}")

        # Reference 'drug_name' (from COALESCE of pref_name and synonyms)
        if drugs_df.empty:
            logger.info(f"No drugs found matching search value: {search_value}")
            return [{'label': f'No results found for "{search_value}"', 'value': None}]
        
        options = [{'label': name, 'value': name} for name in drugs_df['drug_name']]
        logger.debug(f"Dropdown options updated with {len(options)} entries.")
        return options

    except Exception as e:
        logger.error(f"Error updating dropdown options: {e}")
        return initial_options  # Fallback to initial options on error

# Callback to display details for the selected drug
@app.callback(
    Output('drug-details', 'children'),
    [Input('drug-dropdown', 'value')]
)
def display_drug_details(selected_drug):
    """
    Displays detailed information about the selected drug.
    """
    logger.debug(f"Selected drug for details: {selected_drug}")

    if selected_drug is None:
        return "Select a drug to see details."

    try:
        # Query for drug details
        drug_details_df = dq.get_drug_details(selected_drug)
        logger.debug(f"Drug details fetched: {drug_details_df}")

        if drug_details_df.empty:
            logger.info(f"No details found for: {selected_drug}")
            return f"No details found for: {selected_drug}. Please ensure the drug name is correct."

        # Format and return the drug details
        details = html.Div([
            html.H3(f"Drug: {drug_details_df['drug_name'].values[0]}"),
            html.P(f"Max Phase: {drug_details_df['max_phase'].values[0]}"),
            html.P(f"Therapeutic Flag: {drug_details_df['therapeutic_flag'].values[0]}")
        ])

        return details

    except Exception as e:
        logger.error(f"Error fetching details for {selected_drug}: {e}")
        return f"An error occurred while fetching details for: {selected_drug}"

# Callback to display a graph of drug properties
@app.callback(
    Output('drug-properties-graph', 'children'),
    [Input('drug-dropdown', 'value')]
)
def display_drug_properties(selected_drug):
    """
    Visualizes the chemical properties of the selected drug using a bar chart.
    """
    logger.debug(f"Selected drug for properties: {selected_drug}")

    if selected_drug is None:
        return "Select a drug to see its properties."

    try:
        # Query for drug properties
        properties_df = dq.get_drug_properties(selected_drug)
        logger.debug(f"Drug properties fetched: {properties_df}")

        if properties_df.empty:
            logger.info(f"No chemical properties found for: {selected_drug}")
            return f"No chemical properties found for: {selected_drug}. It may not have documented chemical properties."

        # Melt the data frame to convert wide format to long format for easier plotting
        properties_long_df = properties_df.melt(var_name='Property', value_name='Value')
        logger.debug(f"Melted properties DataFrame: {properties_long_df}")

        # Handle NULL values by converting them to NaN
        properties_long_df['Value'] = properties_long_df['Value'].astype(float)
        logger.debug(f"Converted 'Value' to float: {properties_long_df}")

        # Drop rows where 'Value' is NaN
        properties_long_df = properties_long_df.dropna(subset=['Value'])
        logger.debug(f"Properties DataFrame after dropping NaNs: {properties_long_df}")

        if properties_long_df.empty:
            logger.info(f"All chemical properties are missing or invalid for: {selected_drug}")
            return f"All chemical properties are missing or invalid for: {selected_drug}."

        # Create a bar chart for properties
        fig = px.bar(properties_long_df, x='Property', y='Value',
                     title=f"Chemical Properties of {selected_drug}",
                     labels={'Property': 'Property', 'Value': 'Value'},
                     color='Property',
                     template='plotly_white')

        return dcc.Graph(figure=fig)

    except Exception as e:
        logger.error(f"Error fetching properties for {selected_drug}: {e}", exc_info=True)
        return f"An error occurred while fetching properties for: {selected_drug}"

# Callback to display a table of drug interactions
@app.callback(
    Output('drug-interaction-table', 'children'),
    [Input('drug-dropdown', 'value')]
)
def display_drug_interactions_table(selected_drug):
    """
    Displays a table of drugs that interact with the selected drug based on shared mechanisms of action.
    """
    logger.debug(f"Selected drug for interactions table: {selected_drug}")

    if selected_drug is None:
        return "Select a drug to see its interactions."

    try:
        # Query for drug interactions
        interaction_df = dq.get_drug_interactions(selected_drug)
        logger.debug(f"Drug interactions fetched: {interaction_df}")

        if interaction_df.empty:
            logger.info(f"No interactions found for: {selected_drug}")
            return f"No interactions found for: {selected_drug}. It may not have any documented interactions."

        # Create a DataTable for interactions
        interactions_table = dash_table.DataTable(
            data=interaction_df.to_dict('records'),
            columns=[
                {'name': 'Interacting Drug', 'id': 'interacting_drug'},
                {'name': 'Mechanism of Action', 'id': 'mechanism_of_action'},
                {'name': 'Action Type', 'id': 'action_type'},
                {'name': 'Target Name', 'id': 'target_name'}
            ],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '5px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'lightgrey',
                'fontWeight': 'bold'
            },
            filter_action='native',
            sort_action='native'
        )

        return html.Div([
            html.H3(f"Interactions of {selected_drug}"),
            interactions_table
        ])

    except Exception as e:
        logger.error(f"Error fetching interactions for {selected_drug}: {e}")
        return f"An error occurred while fetching interactions for: {selected_drug}"

# Optional Callback to display a network graph of drug interactions
@app.callback(
    Output('drug-interaction-network', 'children'),
    [Input('drug-dropdown', 'value')]
)
def display_drug_interactions_network(selected_drug):
    """
    Visualizes the interaction network of the selected drug using a network graph.
    """
    logger.debug(f"Selected drug for network graph: {selected_drug}")

    if selected_drug is None:
        return "Select a drug to see its interaction network."

    try:
        # Query for drug interactions
        interaction_df = dq.get_drug_interactions(selected_drug)
        logger.debug(f"Drug interactions for network graph fetched: {interaction_df}")

        if interaction_df.empty:
            logger.info(f"No interactions found for: {selected_drug}")
            return f"No network interactions to display for: {selected_drug}. It may not have interaction data available."

        # Build the interaction network using networkx
        import networkx as nx
        import plotly.graph_objects as go

        G = nx.Graph()

        # Add the central drug
        G.add_node(selected_drug, color='red')

        # Add interacting drugs and edges
        for _, row in interaction_df.iterrows():
            interacting_drug = row['interacting_drug']
            G.add_node(interacting_drug, color='blue')
            G.add_edge(selected_drug, interacting_drug, 
                       mechanism=row['mechanism_of_action'], 
                       action_type=row['action_type'])

        if len(G.nodes()) <= 1:
            logger.info(f"No network interactions to display for: {selected_drug}")
            return f"No network interactions to display for: {selected_drug}. It may not have interaction data available."

        # Generate positions for the nodes
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        logger.debug(f"Node positions: {pos}")

        # Extract edge positions
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        # Extract node positions and colors
        node_x = []
        node_y = []
        node_colors = []
        node_text = []
        for node, data in G.nodes(data=True):
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_colors.append(data['color'])
            node_text.append(node)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="top center",
            hoverinfo='text',
            marker=dict(
                showscale=False,
                color=node_colors,
                size=20,
                line_width=2
            )
        )

        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title=f"Interaction Network for {selected_drug}",
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20, l=5, r=5, t=40),
                            annotations=[dict(
                                text="",
                                showarrow=False,
                                xref="paper", yref="paper"
                            )],
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                        )
                       )

        return dcc.Graph(figure=fig)

    except Exception as e:
        logger.error(f"Error creating network graph for {selected_drug}: {e}")
        return f"An error occurred while creating the network graph for: {selected_drug}"

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
