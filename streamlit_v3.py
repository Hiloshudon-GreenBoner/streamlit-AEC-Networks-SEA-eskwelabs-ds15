import streamlit as st
import networkx as nx
import os
import plotly.graph_objects as go
import numpy as np

# --- 0. CONFIGURATION & PATHS ---
st.set_page_config(page_title="Interactive Skills Network", layout="wide")

# Update this path to your specific local folder
GRAPHML_FOLDER = "data"

# --- 1. DATA LOADING (Cached) ---
@st.cache_resource
def load_all_networks(folder_path):
    """
    Loads all GraphML files from a folder. Cached to prevent reloading on every interaction.
    """
    networks_dict = {}
    
    if not os.path.exists(folder_path):
        return None

    # Iterate over files
    for filename in os.listdir(folder_path):
        if filename.endswith(".graphml"):
            try:
                file_path = os.path.join(folder_path, filename)
                G = nx.read_graphml(file_path)
                
                # Clean up attributes if necessary
                for node, data in G.nodes(data=True):
                    # Ensure numeric conversion if numbers are stored as strings
                    if 'size' in data and isinstance(data['size'], str):
                        try: data['size'] = float(data['size'])
                        except: pass
                        
                network_name = filename.replace(".graphml", "")
                networks_dict[network_name] = G
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                
    return networks_dict

# --- 2. PLOTLY GRAPH GENERATION ---
def create_plotly_graph(nx_graph, network_name):
    """
    Generates a Plotly figure with nodes sized by degree and colored by community_id.
    """
    
    # A. Layout Calculation
    # We use a seed so the node positions stay consistent (don't jump around)
    pos = nx.spring_layout(nx_graph, k=0.3, iterations=50, seed=42)
    
    # B. Prepare Node Data
    node_x = []
    node_y = []
    node_text = []
    node_sizes = []
    node_colors = []
    
    # 1. Extract raw degrees for sizing
    # Note: We use G.degree (connection count) rather than the 'degree' attribute (centrality score)
    # to ensure the visual size matches the number of visible lines.
    raw_degrees = [val for (node, val) in nx_graph.degree()]
    
    # Avoid division by zero if graph is empty or has 1 node
    if len(raw_degrees) > 0:
        min_deg = min(raw_degrees)
        max_deg = max(raw_degrees)
        degree_range = max_deg - min_deg
        
        # If all nodes have same degree, set range to 1 to avoid div/0
        if degree_range == 0: degree_range = 1
    else:
        min_deg, degree_range = 0, 1

    # 2. Iterate nodes to build lists
    for node in nx_graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Get Attributes
        node_data = nx_graph.nodes[node]
        degree_count = nx_graph.degree[node]
        # Use .get() with default 0 to prevent crashing if attribute is missing
        community_id = node_data.get('community_id', 0) 
        
        # Calculate Size (Min-Max Normalization)
        # Scale between 10px and 50px
        normalized_size = (degree_count - min_deg) / degree_range
        final_size = 10 + (normalized_size * 40) 
        node_sizes.append(final_size)
        
        # Collect Color Data
        node_colors.append(community_id)
        
        # Custom Hover Text
        hover_info = (
            f"<b>{node}</b><br>"
            f"Degree: {degree_count}<br>"
            f"Community ID: {community_id}"
        )
        node_text.append(hover_info)

    # C. Prepare Edge Traces
    edge_x = []
    edge_y = []
    
    for edge in nx_graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # D. Build Node Trace (FIXED)
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        hovertext=node_text,
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            reversescale=True,
            size=node_sizes,
            # Ensure cmin/cmax are calculated correctly, handling empty lists
            cmin=min(node_colors) if node_colors else 0,
            cmax=max(node_colors) if node_colors else 1,
            color=node_colors, # Actual colors based on community_id
            colorbar=dict(
                thickness=15,
                title='Community ID',
                xanchor='left',
                # titleside='right' <--- REMOVED TO FIX ERROR
            ),
            line_width=2
        )
    )

# E. Assembly (Workaround: Removing Title)
    fig = go.Figure(data=[edge_trace, node_trace],
        layout=go.Layout(
            # --- Title and title font arguments are removed entirely ---
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=700
        )
    )
    
    return fig

# --- 3. STREAMLIT APP INTERFACE ---
st.title("🌐 Interactive Skills Network")
st.markdown("Nodes are **colored by Community ID** and **sized by Degree**.")

# Load Data
skills_networks = load_all_networks(GRAPHML_FOLDER)

if skills_networks is None:
    st.error(f"❌ The folder path could not be found: `{GRAPHML_FOLDER}`")
elif not skills_networks:
    st.warning(f"⚠️ No .graphml files found in `{GRAPHML_FOLDER}`")
else:
    # Sidebar Selection
    with st.sidebar:
        st.header("Graph Controls")
        network_names = list(skills_networks.keys())
        selected_network_name = st.selectbox("Select Network", network_names)
        
        G_selected = skills_networks[selected_network_name]
        st.write("---")
        st.metric("Nodes", G_selected.number_of_nodes())
        st.metric("Edges", G_selected.number_of_edges())

    # Main Area
    st.subheader(f"Analyzing: {selected_network_name}")
    
    with st.spinner("Calculating layout and rendering..."):
        # Pass the graph object to the plotter
        plotly_fig = create_plotly_graph(G_selected, selected_network_name)
        st.plotly_chart(plotly_fig, use_container_width=True)

    st.caption("Tip: You can zoom, pan, and hover over nodes to see details.")