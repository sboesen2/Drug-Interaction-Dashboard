import streamlit as st
import pandas as pd
import os
from api.data_queries import (
    search_drugs,
    get_drug_details,
    get_drug_properties,
    get_drug_interactions,
    engine,
    create_drug_interaction_network
)
import logging
from sqlalchemy import text
import streamlit.components.v1 as components
import gc
import time
from functools import lru_cache
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import base64

# Load secrets with error handling
try:
    db_user = st.secrets["database"]["DB_USER"]
    db_password = st.secrets["database"]["DB_PASSWORD"]
    db_host = st.secrets["database"]["DB_HOST"]
    db_port = st.secrets["database"]["DB_PORT"]
    db_name = st.secrets["database"]["DB_NAME"]
except KeyError as e:
    logger.error(f"Missing secret: {e}")
    st.error("Configuration error: Missing database credentials.")
    st.stop()  # Stop the app if secrets are missing

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize session states
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'previous_drug' not in st.session_state:
    st.session_state.previous_drug = None
if 'cache_timeout' not in st.session_state:
    st.session_state.cache_timeout = 3600  # 1 hour cache

# Utility functions
@lru_cache(maxsize=32)
def get_cached_drug_details(drug_name):
    """Cache drug details to improve performance"""
    return get_drug_details(drug_name)

def retry_operation(func, max_retries=3):
    """Retry an operation with exponential backoff"""
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i == max_retries - 1:
                raise e
            time.sleep(2 ** i)

def clear_memory():
    """Clear memory when switching between drugs"""
    gc.collect()
    if 'structure_img' in st.session_state:
        del st.session_state.structure_img
    if 'html_content' in st.session_state:
        del st.session_state.html_content

@st.cache_data(ttl=3600)
def get_initial_suggestions():
    """Cache initial drug suggestions"""
    try:
        return search_drugs("").head(10)
    except Exception as e:
        logger.exception("Error loading initial drugs")
        return pd.DataFrame()

def display_network_visualization(selected_drug, html_content):
    """Display network visualization with styling"""
    st.markdown("""
        <style>
            .network-container {
                border: 2px solid #e6e6e6;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                background-color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                position: relative;
                min-width: 800px;
                width: 100%;
                max-width: 1400px;
            }
            .network-container iframe {
                width: 100% !important;
                height: 1000px !important;
                border: none;
                margin: 0;
                padding: 0;
                transform: scale(1);
            }
            .vis-tooltip {
                position: absolute;
                padding: 10px;
                background-color: white;
                border-radius: 5px;
                border: 1px solid #ddd;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-width: 300px;
                z-index: 1000;
                font-size: 12px;
                line-height: 1.4;
            }
            .vis-navigation {
                position: absolute;
                right: 20px;
                top: 20px;
                z-index: 1000;
            }
        </style>
        <div class="network-container">
    """, unsafe_allow_html=True)
    
    st.components.v1.html(
        html_content,
        height=1000,
        scrolling=False
    )
    
    st.markdown("</div>", unsafe_allow_html=True)

def create_drug_likeness_dashboard(properties_df):
    """
    Creates an interactive dashboard showing drug-likeness properties
    and Lipinski's Rule of 5 compliance
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "<b>Molecular Weight Distribution</b>",
            "<b>LogP vs Polar Surface Area</b>",
            "<b>H-Bond Donors vs Acceptors</b>",
            "<b>Lipinski's Rules Compliance</b>"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    # Molecular Weight Distribution
    fig.add_trace(
        go.Histogram(
            x=properties_df['full_mwt'],
            name="Molecular Weight",
            nbinsx=20,
            marker_color='#2E91E5',
            showlegend=False
        ),
        row=1, col=1
    )

    # LogP vs PSA Scatter
    fig.add_trace(
        go.Scatter(
            x=properties_df['alogp'],
            y=properties_df['psa'],
            mode='markers',
            name='LogP vs PSA',
            marker=dict(
                size=12,
                color=properties_df['full_mwt'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Molecular Weight")
            ),
            hovertemplate="<br>".join([
                "LogP: %{x:.2f}",
                "PSA: %{y:.2f}",
                "MW: %{marker.color:.2f}"
            ])
        ),
        row=1, col=2
    )

    # H-Bond Donors vs Acceptors
    fig.add_trace(
        go.Scatter(
            x=properties_df['hba'],
            y=properties_df['hbd'],
            mode='markers',
            name='H-Bonds',
            marker=dict(
                size=12,
                color='#2ca02c'
            ),
            hovertemplate="<br>".join([
                "Acceptors: %{x}",
                "Donors: %{y}"
            ])
        ),
        row=2, col=1
    )

    # Lipinski Rules Compliance
    lipinski_rules = {
        'Molcular Weight ≤ 500': (properties_df['full_mwt'] <= 500).mean() * 100,
        'LogP ≤ 5': (properties_df['alogp'] <= 5).mean() * 100,
        'Hydrogen Bond Acceptors ≤ 10': (properties_df['hba'] <= 10).mean() * 100,
        'Hydrogen Bond Donors ≤ 5': (properties_df['hbd'] <= 5).mean() * 100
    }

    fig.add_trace(
        go.Bar(
            x=list(lipinski_rules.keys()),
            y=list(lipinski_rules.values()),
            name="Lipinski Compliance",
            marker_color='#FF7F0E',
            text=[f"{v:.1f}%" for v in lipinski_rules.values()],
            textposition='auto',
        ),
        row=2, col=2
    )

    # Update layout and styling
    fig.update_layout(
        height=800,
        width=1000,
        showlegend=False,
        title=dict(
            text="<b>Drug-likeness Properties Analysis</b>",
            x=0.5,
            y=0.95,
            font=dict(size=24)
        ),
        paper_bgcolor='white',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12)
    )

    # Update axes labels and styling
    fig.update_xaxes(
        title_text="<b>Molecular Weight (Da)</b>",
        row=1, col=1,
        gridcolor='lightgrey'
    )
    fig.update_xaxes(
        title_text="<b>LogP</b>",
        row=1, col=2,
        gridcolor='lightgrey'
    )
    fig.update_xaxes(
        title_text="<b>H-Bond Acceptors</b>",
        row=2, col=1,
        gridcolor='lightgrey'
    )
    fig.update_xaxes(
        title_text="<b>Lipinski Rules</b>",
        row=2, col=2,
        gridcolor='lightgrey'
    )
    
    fig.update_yaxes(
        title_text="<b>Count</b>",
        row=1, col=1,
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        title_text="<b>Polar Surface Area</b>",
        row=1, col=2,
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        title_text="<b>H-Bond Donors</b>",
        row=2, col=1,
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        title_text="<b>Compliance (%)</b>",
        row=2, col=2,
        gridcolor='lightgrey',
        range=[0, 100]
    )

    # Add grid to all subplots
    fig.update_layout(
        template="simple_white"
    )

    return fig

def get_image_download_link(img, filename, text):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}">{text}</a>'
    return href

def get_plotly_fig_download_link(fig, filename):
    buffer = BytesIO()
    fig.write_image(buffer, format='png')
    buffer.seek(0)
    return buffer

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_drug_structure(drug_name):
    try:
        # Add a timeout to the request
        with st.spinner('Loading structure (timeout: 10s)...'):
            structure_available = check_drug_structure_availability(drug_name)
            if not structure_available:
                return None
            return get_drug_structure(drug_name)
    except Exception as e:
        st.warning("Structure loading timed out or failed")
        return None

def main():
    st.set_page_config(
        page_title="Drug Interaction Dashboard",
        layout="wide",
        initial_sidebar_state="auto"
    )
    
    # Move search functionality to sidebar
    with st.sidebar:
        st.title("Search")
        search_term = st.text_input(
            "Search for a drug",
            key="drug_search_sidebar",
            placeholder="Type to search..."
        )
        
        # Move initial suggestions to sidebar
        if not search_term:
            initial_drugs = get_initial_suggestions()
            if not initial_drugs.empty:
                with st.expander("Popular Drugs"):
                    st.dataframe(
                        initial_drugs[['drug_name', 'max_phase']], 
                        hide_index=True
                    )
    
    # Main content area
    st.title("Drug Interaction Dashboard")
    st.write("Search for a drug in the sidebar to see its details and interactions.")

    try:
        if search_term:
            matching_drugs = retry_operation(lambda: search_drugs(search_term))
            
            if not matching_drugs.empty:
                st.success(f"Found {len(matching_drugs)} matching drugs")
                selected_drug = st.selectbox(
                    "Select a drug from matches",
                    options=matching_drugs['drug_name'].tolist(),
                    key="drug_selector"
                )
                
                if selected_drug:
                    # Clear memory if drug changed
                    if selected_drug != st.session_state.previous_drug:
                        clear_memory()
                        st.session_state.previous_drug = selected_drug

                    col1, col2 = st.columns([0.6, 0.4])
                    
                    with st.spinner('Loading drug data...'):
                        progress_bar = st.progress(0)
                        
                        try:
                            # Load data with caching and retries
                            progress_bar.progress(20)
                            details_df = retry_operation(lambda: get_cached_drug_details(selected_drug))
                            
                            progress_bar.progress(40)
                            properties_df = retry_operation(lambda: get_drug_properties(selected_drug))
                            
                            progress_bar.progress(60)
                            interactions_df = retry_operation(lambda: get_drug_interactions(selected_drug))
                            
                            progress_bar.progress(100)
                            progress_bar.empty()
                            
                            # Display drug details
                            with col1:
                                st.subheader("Drug Details")
                                if not details_df.empty:
                                    st.dataframe(details_df, use_container_width=True)
                                else:
                                    st.info("No details available")
                                
                                st.subheader("Drug Properties")
                                if not properties_df.empty:
                                    # Existing dataframe display
                                    st.dataframe(properties_df, use_container_width=True)
                                    
                                    # Make sure properties_df has all required columns
                                    required_columns = ['full_mwt', 'alogp', 'hba', 'hbd', 'psa']
                                    
                                    # Check if all required columns exist and have data
                                    if all(col in properties_df.columns for col in required_columns):
                                        # Rename full_mwt to molecular_weight if needed
                                        if 'full_mwt' in properties_df.columns:
                                            properties_df['molecular_weight'] = properties_df['full_mwt']
                                        
                                        st.subheader("Drug-likeness Analysis")
                                        with st.expander("ℹ️ About Drug-likeness", expanded=True):
                                            st.markdown("""
                                            ### Understanding Drug-likeness Properties
                                            
                                            **Lipinski's Rule of 5** predicts drug-likeness based on these criteria:
                                            - Molecular Weight ≤ 500 daltons
                                            - Lipophicity of calculated LogP ≤ 5 
                                            - Hydrogen Bond Donors ≤ 5
                                            - Hydrogen Bond Acceptors ≤ 10
                                            """)
                                        
                                        drug_likeness_fig = create_drug_likeness_dashboard(properties_df)
                                        st.plotly_chart(drug_likeness_fig, use_container_width=True, config={
                                            'displayModeBar': True,
                                            'toImageButtonOptions': {
                                                'format': 'png',
                                                'filename': f'{selected_drug}_drug_likeness',
                                                'height': 800,
                                                'width': 1000,
                                                'scale': 2
                                            }
                                        })
                                        
                                        # Add download button for the dashboard
                                        buffer = get_plotly_fig_download_link(drug_likeness_fig, f"{selected_drug}_drug_likeness.png")
                                        st.download_button(
                                            label="💾 Download Drug-likeness Dashboard",
                                            data=buffer,
                                            file_name=f"{selected_drug}_drug_likeness.png",
                                            mime="image/png"
                                        )
                                    else:
                                        st.info("Insufficient property data available for visualization")
                                else:
                                    st.info("No properties available")
                                
                                if st.checkbox("Show Chemical Structure", value=False):
                                    structure_img = cached_get_drug_structure(selected_drug)
                                    if structure_img:
                                        st.image(structure_img, caption=f"{selected_drug} Structure")
                                        st.download_button(
                                            label="💾 Download Structure Image",
                                            data=structure_img,
                                            file_name=f"{selected_drug}_structure.png",
                                            mime="image/png"
                                        )
                                    else:
                                        st.info("No structure available or loading failed")
                            
                            with col2:
                                st.subheader("Drug Interactions")
                                if not interactions_df.empty:
                                    st.dataframe(
                                        interactions_df,
                                        use_container_width=True,
                                        height=300
                                    )
                                    
                                    if st.checkbox("Show Network Visualization", value=False):
                                        st.subheader("Network Visualization")
                                        try:
                                            with st.spinner("Generating interaction network..."):
                                                html_content = create_drug_interaction_network(selected_drug, interactions_df)
                                                if html_content:
                                                    display_network_visualization(selected_drug, html_content)
                                                    
                                                    st.download_button(
                                                        label="💾 Download Network Visualization",
                                                        data=html_content,
                                                        file_name=f"{selected_drug}_network.html",
                                                        mime="text/html",
                                                        help="Download the network visualization as an HTML file"
                                                    )
                                                    
                                                    with st.expander("📌 Network Interaction Guide"):
                                                        st.markdown("""
                                                        ### How to interact with the network:
                                                        
                                                        #### Network Elements:
                                                        - 🔴 **Red Node**: Selected main drug
                                                        - 📦 **Box Nodes**: Mechanism of action groups
                                                        - ⭕ **Colored Nodes**: Interacting drugs (color indicates mechanism group)
                                                        
                                                        #### Interactions:
                                                        - **Zoom**: Use mouse wheel or pinch gesture
                                                        - **Pan**: Click and drag the background
                                                        - **Move Nodes**: Click and drag individual nodes
                                                        - **View Details**: Hover over nodes or edges
                                                        - **Reset View**: Double-click the background
                                                        
                                                        #### Understanding the Layout:
                                                        - Drugs are grouped by their mechanism of action
                                                        - Same-colored nodes share the same mechanism
                                                        - Hover over mechanism boxes to see full descriptions
                                                        - Hover over drug nodes to see detailed information
                                                        """)
                                        except Exception as e:
                                            st.error("Failed to create network visualization")
                                            logger.exception("Network visualization error")
                                else:
                                    st.info("No interactions found for network visualization")
                        except Exception as e:
                            st.error(f"Error fetching drug data: {str(e)}")
                            logger.exception("Error in drug data retrieval")
            else:
                st.warning("No drugs found matching your search")
        else:
            st.info("Type a drug name to begin searching")
            initial_drugs = get_initial_suggestions()
            if not initial_drugs.empty:
                with st.expander("View Popular Drugs"):
                    st.dataframe(
                        initial_drugs[['drug_name', 'max_phase']], 
                        hide_index=True
                    )

    except Exception as e:
        st.error(f"Application error: {str(e)}")
        logger.exception("General application error")

    # Footer
    st.markdown("---")
    st.markdown("Drug Interaction Dashboard - Data from ChEMBL Database")

    # Debug information
    if os.getenv('STREAMLIT_ENV') == 'development':
        if st.checkbox("Show Debug Info"):
            st.write("Debug Information:")
            st.write({
                "Database URL": "****",  # Don't expose connection string
                "Search Term": search_term if 'search_term' in locals() else None,
                "Selected Drug": selected_drug if 'selected_drug' in locals() else None,
                "Cache Status": "Active" if st.session_state.get('cache_timeout') else "Inactive"
            })

if __name__ == "__main__":
    main()


# Use this function if you want to make the dashboard fit the screen width
# def main():
#     # Add this as the first line in main() function, before any other st. commands
#     st.set_page_config(
#         page_title="Drug Interaction Dashboard",
#         layout="wide",  # Use full width of the browser
#         initial_sidebar_state="auto"
#     )