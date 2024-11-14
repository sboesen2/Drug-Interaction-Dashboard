# api/data_queries.py

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
import pandas as pd
import os
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus
from pyvis.network import Network
import tempfile
import networkx as nx
import streamlit as st

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration - remove hardcoded values
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

# Add better error handling for missing environment variables
required_env_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
    raise ValueError(error_msg)

# Create global engine instance
try:
    # Properly encode the password
    password = quote_plus(DB_CONFIG['password'])
    DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{password}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    # Test connection - Modified this part
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1;"))
        result.scalar()
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

def get_top_50_drugs():
    """
    Retrieves initial set of drugs for dropdown.
    """
    query = """
    SELECT DISTINCT 
        md.pref_name AS drug_name,
        md.max_phase
    FROM molecule_dictionary md
    WHERE md.pref_name IS NOT NULL
      AND md.max_phase IN (3, 4)
      AND md.therapeutic_flag = 1
    ORDER BY 
        md.max_phase DESC,
        md.pref_name
    LIMIT 50;
    """
    try:
        df = pd.read_sql(query, engine)
        logger.debug(f"Retrieved {len(df)} initial drugs")
        return df
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching initial drugs: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def search_drugs(search_value):
    """
    Enhanced search function optimized for autocomplete with better logging and error handling.
    Returns up to 10 matching drugs for quick suggestions.
    """
    if not isinstance(search_value, str):
        logger.warning("Invalid search value type")
        return pd.DataFrame()

    # Clean the search value
    search_value = search_value.strip()
    
    # If empty string, return initial popular drugs
    if not search_value:
        return get_top_50_drugs().head(10)
    
    query = """
    SELECT DISTINCT 
        md.pref_name AS drug_name,
        md.max_phase
    FROM molecule_dictionary md
    WHERE md.pref_name IS NOT NULL
      AND md.therapeutic_flag = 1
      AND md.pref_name ILIKE %s
    ORDER BY 
        md.max_phase DESC,
        md.pref_name
    LIMIT 10;
    """
    try:
        # Add wildcards for partial matching
        search_pattern = f"%{search_value}%"
        logger.debug(f"Searching with pattern: {search_pattern}")
        
        df = pd.read_sql(query, engine, params=(search_pattern,))
        logger.debug(f"Search results for '{search_value}': {len(df)} matches")
        return df
    except SQLAlchemyError as e:
        logger.error(f"Database error in drug search: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_drug_details(drug_name):
    """
    Retrieves detailed information about a specific drug.
    """
    if not drug_name:
        logger.warning("No drug name provided")
        return pd.DataFrame()

    query = """
    SELECT 
        md.pref_name AS drug_name,
        md.max_phase,
        md.therapeutic_flag,
        md.molecule_type,
        md.first_approval,
        md.oral,
        md.parenteral,
        md.topical,
        md.black_box_warning,
        md.natural_product,
        md.first_in_class,
        md.chirality
    FROM molecule_dictionary md
    WHERE LOWER(md.pref_name) = LOWER(%s);
    """
    try:
        df = pd.read_sql(query, engine, params=(drug_name,))
        logger.debug(f"Retrieved details for drug: {drug_name}")
        return df
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching drug details: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_drug_properties(drug_name):
    """
    Retrieves chemical properties of a specific drug.
    """
    try:
        # First, get the molregno
        molregno_query = """
        SELECT molregno 
        FROM molecule_dictionary 
        WHERE LOWER(pref_name) = LOWER(%s);
        """
        molregno_df = pd.read_sql(molregno_query, engine, params=(drug_name,))
        
        if molregno_df.empty:
            logger.warning(f"No molecule found for drug name: {drug_name}")
            return pd.DataFrame()
            
        # Convert numpy.int64 to Python int
        molregno = int(molregno_df['molregno'].iloc[0])
        logger.debug(f"Found molregno {molregno} for drug {drug_name}")
        
        # Get basic properties - NO molecular_formula here
        properties_query = """
        SELECT 
            cp.alogp,
            cp.hba,
            cp.hbd,
            cp.psa,
            cp.aromatic_rings,
            cp.qed_weighted,
            cp.mw_freebase,
            cp.full_mwt
        FROM compound_properties cp
        WHERE cp.molregno = %s;
        """
        
        df = pd.read_sql(properties_query, engine, params=(molregno,))
        
        if df.empty:
            logger.warning(f"No properties found for molregno {molregno}")
            return pd.DataFrame()
            
        # Add drug name to the dataframe
        df['drug_name'] = drug_name
        
        logger.debug(f"Properties retrieved for {drug_name}: {df.to_dict('records')}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching drug properties: {str(e)}")
        logger.exception(e)  # This will log the full stack trace
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_drug_interactions(drug_name):
    """
    Retrieves drug interactions with improved performance and error handling.
    """
    if not drug_name:
        logger.warning("No drug name provided for interactions query")
        return pd.DataFrame()

    query = """
    WITH selected_drug_mechanisms AS (
        SELECT DISTINCT dm.mechanism_of_action
        FROM drug_mechanism dm
        JOIN molecule_dictionary md ON dm.molregno = md.molregno
        WHERE LOWER(md.pref_name) = LOWER(%s)
    )
    SELECT DISTINCT 
        md.pref_name AS interacting_drug,
        dm.mechanism_of_action,
        dm.action_type,
        td.pref_name AS target_name,
        td.organism AS target_organism
    FROM drug_mechanism dm
    JOIN molecule_dictionary md ON dm.molregno = md.molregno
    JOIN target_dictionary td ON dm.tid = td.tid
    WHERE EXISTS (
        SELECT 1 FROM selected_drug_mechanisms sdm 
        WHERE dm.mechanism_of_action = sdm.mechanism_of_action
    )
    AND LOWER(md.pref_name) != LOWER(%s)
    ORDER BY interacting_drug
    LIMIT 50;
    """
    try:
        df = pd.read_sql(query, engine, params=(drug_name, drug_name))
        df['drug_name'] = drug_name  # Add the drug_name column
        logger.debug(f"Retrieved {len(df)} interactions for drug: {drug_name}")
        return df
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching drug interactions: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def create_drug_interaction_network(selected_drug, interactions_df):
    """
    Creates an interactive network visualization with meaningful drug relationships.
    """
    if interactions_df.empty:
        return None
        
    try:
        net = Network(
            height="800px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#000000",
            directed=True,
            select_menu=False,
            filter_menu=False
        )

        # Group drugs by mechanism of action
        mechanism_groups = {}
        for _, row in interactions_df.iterrows():
            mechanism = row['mechanism_of_action']
            if mechanism not in mechanism_groups:
                mechanism_groups[mechanism] = []
            mechanism_groups[mechanism].append(row['interacting_drug'])

        # Add main drug node in center
        net.add_node(
            selected_drug,
            label=selected_drug,
            color="#E41A1C",  # Red
            size=40,
            title=f"Main Drug: {selected_drug}",
            shape="dot"
        )

        # Color palette for different mechanisms
        colors = ["#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33", 
                 "#A65628", "#F781BF", "#999999"]
        
        # Add interacting drugs, grouped by mechanism
        for idx, (mechanism, drugs) in enumerate(mechanism_groups.items()):
            color = colors[idx % len(colors)]  # Cycle through colors
            
            # Add mechanism label node
            mechanism_id = f"mech_{idx}"
            net.add_node(
                mechanism_id,
                label=mechanism[:20] + "..." if len(mechanism) > 20 else mechanism,
                color="#FFFFFF",
                size=30,
                title=f"Mechanism: {mechanism}",
                shape="box",
                borderWidth=2,
                borderColor=color
            )
            
            # Connect main drug to mechanism
            net.add_edge(selected_drug, mechanism_id, color=color)
            
            # Add drugs for this mechanism
            for drug in drugs:
                net.add_node(
                    drug,
                    label=drug,
                    color=color,
                    size=25,
                    title=f"""
                    Drug: {drug}
                    Mechanism: {mechanism}
                    Target: {interactions_df[interactions_df['interacting_drug'] == drug]['target_name'].iloc[0]}
                    """,
                    shape="dot"
                )
                # Connect drug to its mechanism
                net.add_edge(mechanism_id, drug, color=color)

        # Updated options with better zoom and interaction controls
        net.set_options("""
        {
          "physics": {
            "hierarchicalRepulsion": {
              "centralGravity": 0.0,
              "springLength": 200,
              "springConstant": 0.01,
              "nodeDistance": 150,
              "damping": 0.09
            },
            "solver": "hierarchicalRepulsion",
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            }
          },
          "layout": {
            "hierarchical": {
              "enabled": true,
              "levelSeparation": 150,
              "nodeSpacing": 150,
              "direction": "UD",
              "sortMethod": "directed"
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "zoomView": true,
            "dragView": true,
            "dragNodes": true,
            "zoomSpeed": 0.3,
            "navigationButtons": true,
            "keyboard": {
              "enabled": true,
              "speed": {
                "x": 10,
                "y": 10,
                "zoom": 0.1
              },
              "bindToWindow": true
            }
          },
          "configure": {
            "enabled": false
          }
        }
        """)
        
        return net.generate_html()
            
    except Exception as e:
        logger.error(f"Error in network visualization: {str(e)}")
        logger.exception(e)
        return None