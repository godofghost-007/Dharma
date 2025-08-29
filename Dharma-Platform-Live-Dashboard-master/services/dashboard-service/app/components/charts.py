"""
Chart Generation Components
Reusable chart components using Plotly
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional

class ChartGenerator:
    """Component for generating various chart types"""
    
    def __init__(self):
        self.color_palette = {
            'pro_india': '#2E8B57',
            'neutral': '#4682B4', 
            'anti_india': '#DC143C',
            'twitter': '#1DA1F2',
            'youtube': '#FF0000',
            'telegram': '#0088CC',
            'web': '#FF6B35'
        }
    
    def create_time_series_chart(
        self,
        data: Dict[str, List],
        title: str,
        x_column: str = 'date',
        height: int = 400
    ) -> go.Figure:
        """Create a time series line chart"""
        fig = go.Figure()
        
        for column, values in data.items():
            if column != x_column:
                color = self.color_palette.get(column.lower().replace('-', '_'), '#1f77b4')
                fig.add_trace(go.Scatter(
                    x=data[x_column],
                    y=values,
                    mode='lines+markers',
                    name=column,
                    line=dict(color=color, width=3),
                    marker=dict(size=6)
                ))
        
        fig.update_layout(
            title=title,
            height=height,
            xaxis_title=x_column.title(),
            yaxis_title="Value",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        return fig
    
    def create_pie_chart(
        self,
        labels: List[str],
        values: List[float],
        title: str,
        colors: Optional[List[str]] = None,
        height: int = 400
    ) -> go.Figure:
        """Create a pie chart"""
        if not colors:
            colors = [self.color_palette.get(label.lower().replace('-', '_'), '#1f77b4') for label in labels]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            textinfo='label+percent',
            textfont_size=12,
            hole=0.4
        )])
        
        fig.update_layout(
            title=title,
            height=height,
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=True
        )
        
        return fig
    
    def create_bar_chart(
        self,
        data: Dict[str, Any],
        title: str,
        x_column: str,
        y_column: str,
        color_column: Optional[str] = None,
        height: int = 400
    ) -> go.Figure:
        """Create a bar chart"""
        df = pd.DataFrame(data)
        
        if color_column:
            fig = px.bar(df, x=x_column, y=y_column, color=color_column, title=title)
        else:
            fig = px.bar(df, x=x_column, y=y_column, title=title)
        
        fig.update_layout(
            height=height,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        return fig
    
    def create_heatmap(
        self,
        data: List[List[float]],
        x_labels: List[str],
        y_labels: List[str],
        title: str,
        height: int = 400
    ) -> go.Figure:
        """Create a heatmap"""
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            colorscale='Viridis'
        ))
        
        fig.update_layout(
            title=title,
            height=height,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        return fig
    
    def create_scatter_map(
        self,
        data: List[Dict[str, Any]],
        title: str,
        lat_column: str = 'lat',
        lon_column: str = 'lon',
        size_column: str = 'size',
        color_column: Optional[str] = None,
        height: int = 400
    ) -> go.Figure:
        """Create a scatter map"""
        df = pd.DataFrame(data)
        
        fig = px.scatter_geo(
            df,
            lat=lat_column,
            lon=lon_column,
            size=size_column,
            color=color_column if color_column else size_column,
            hover_name='name' if 'name' in df.columns else None,
            size_max=50,
            color_continuous_scale='Viridis',
            title=title
        )
        
        fig.update_layout(
            height=height,
            margin=dict(l=0, r=0, t=50, b=0),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular'
            )
        )
        
        return fig
    
    def create_network_graph(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        title: str,
        height: int = 500
    ) -> go.Figure:
        """Create a network graph visualization"""
        import networkx as nx
        import numpy as np
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for node in nodes:
            G.add_node(node['id'], **node)
        
        # Add edges
        for edge in edges:
            G.add_edge(edge['source'], edge['target'], weight=edge.get('weight', 1))
        
        # Calculate layout
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Extract node positions
        node_x = [pos[node][0] for node in G.nodes()]
        node_y = [pos[node][1] for node in G.nodes()]
        
        # Extract edge positions
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    len=0.5,
                    x=1.02,
                    title="Node Connections"
                ),
                line=dict(width=2)
            )
        )
        
        # Color nodes by number of connections
        node_adjacencies = []
        node_text = []
        for node in G.nodes():
            adjacencies = list(G.neighbors(node))
            node_adjacencies.append(len(adjacencies))
            node_text.append(f'{node}<br># of connections: {len(adjacencies)}')
        
        node_trace.marker.color = node_adjacencies
        node_trace.text = node_text
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title=title,
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text="Network graph showing relationships between entities",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color="#888", size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           height=height
                       ))
        
        return fig