import dash
from dash import dcc, html
import plotly.graph_objects as go
import requests
import pandas as pd
from dash.dependencies import Input, Output

# Iniciar o app Dash
app = dash.Dash(__name__)

# Função para buscar dados da criptomoeda
def get_crypto_data(crypto_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart?vs_currency=usd&days={days}"
    response = requests.get(url)
    data = response.json()
    prices = data['prices']
    timestamps = [pd.to_datetime(item[0], unit='ms') for item in prices]
    price_values = [item[1] for item in prices]
    return timestamps, price_values

# Layout do app com estilo refinado
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#2c3e50', 'padding': '30px'},
    children=[
        html.Div(
            style={'textAlign': 'center', 'color': '#ecf0f1'},
            children=[
                html.H1("Dashboard de Criptomoedas", style={'fontSize': '36px', 'fontWeight': 'bold'}),
                html.P("Visualize o preço das criptomoedas em tempo real", style={'fontSize': '18px'}),
            ]
        ),
        
        # Dropdown para escolher criptomoeda
        html.Div(
            style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px', 'marginBottom': '20px'},
            children=[
                dcc.Dropdown(
                    id='crypto-dropdown',
                    options=[
                        {'label': 'Bitcoin', 'value': 'bitcoin'},
                        {'label': 'Ethereum', 'value': 'ethereum'},
                        {'label': 'Litecoin', 'value': 'litecoin'}
                    ],
                    value='bitcoin',  # Valor inicial
                    style={'width': '300px', 'color': '#2c3e50', 'backgroundColor': '#ecf0f1'}
                ),
                dcc.Dropdown(
                    id='days-dropdown',
                    options=[
                        {'label': '7 Dias', 'value': 7},
                        {'label': '30 Dias', 'value': 30},
                        {'label': '90 Dias', 'value': 90}
                    ],
                    value=30,  # Valor inicial
                    style={'width': '300px', 'color': '#2c3e50', 'backgroundColor': '#ecf0f1'}
                ),
            ]
        ),
        
        # Gráfico de preços
        dcc.Graph(id='crypto-graph'),
        
        # Rodapé
        html.Div(
            style={'textAlign': 'center', 'color': '#ecf0f1', 'marginTop': '50px'},
            children=[
                html.P("Desenvolvido por Seu Nome", style={'fontSize': '14px'}),
            ]
        )
    ]
)

# Função para atualizar o gráfico
@app.callback(
    Output('crypto-graph', 'figure'),
    [Input('crypto-dropdown', 'value'),
     Input('days-dropdown', 'value')]
)
def update_graph(crypto_id, days):
    # Buscar dados para a criptomoeda selecionada e o intervalo de dias
    timestamps, price_values = get_crypto_data(crypto_id, days)
    
    # Criar o gráfico com design mais refinado
    fig = go.Figure()

    # Adicionar a linha do gráfico
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=price_values,
        mode='lines',
        name=crypto_id.capitalize(),
        line=dict(color='#3498db', width=3),
    ))

    # Atualizar layout do gráfico com mais detalhes
    fig.update_layout(
        title=f"Preço do {crypto_id.capitalize()} nos últimos {days} dias",
        title_font=dict(family="Arial, sans-serif", size=24, color="#ecf0f1"),
        xaxis_title="Data",
        xaxis_title_font=dict(family="Arial, sans-serif", size=16, color="#ecf0f1"),
        yaxis_title="Preço (USD)",
        yaxis_title_font=dict(family="Arial, sans-serif", size=16, color="#ecf0f1"),
        template="plotly_dark",  # Template visual mais clean
        plot_bgcolor="#34495e",  # Fundo do gráfico
        paper_bgcolor="#2c3e50",  # Cor de fundo da página
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig

# Rodar o servidor
if __name__ == '__main__':
    app.run_server(debug=True)
