from datetime import datetime, timedelta
from config import CORES
from database import get_kpis_data, get_graficos_data

def generate_kpis(codigo_rca=None):
    """Gera dados dos KPIs para o dashboard"""
    data = get_kpis_data(codigo_rca)
    
    kpis = [
        {
            'titulo': 'Pedidos Pendentes',
            'valor': data.get('pedidos_pendentes', 0),
            'icone': 'fas fa-clock',
            'cor': CORES['alerta'],
            'descricao': 'Aguardando agendamento'
        },
        {
            'titulo': 'Agendamentos Confirmados',
            'valor': data.get('agendamentos_confirmados', 0),
            'icone': 'fas fa-calendar-check',
            'cor': CORES['sucesso'],
            'descricao': 'Prontos para entrega'
        },
        {
            'titulo': 'RCAs Ativos',
            'valor': data.get('usuarios_ativos', 0),
            'icone': 'fas fa-users',
            'cor': CORES['primaria'],
            'descricao': 'Usuários cadastrados'
        },
        {
            'titulo': 'Entregas Hoje',
            'valor': data.get('entregas_hoje', 0),
            'icone': 'fas fa-truck',
            'cor': CORES['critico'],
            'descricao': 'Finalizadas hoje'
        }
    ]
    
    return kpis

def generate_pedidos_chart(codigo_rca=None):
    """Gera dados para o gráfico de pedidos por dia (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    pedidos_data = data.get('pedidos_por_dia', [])
    
    # Se não há dados, gera dados de exemplo para os últimos 30 dias
    if not pedidos_data:
        pedidos_data = []
        for i in range(29, -1, -1):
            date = datetime.now() - timedelta(days=i)
            pedidos_data.append({
                'data': date.strftime('%Y-%m-%d'),
                'quantidade': 0
            })
    
    # Prepara dados para Plotly.js
    labels = []
    valores = []
    
    for item in pedidos_data:
        # Converte data para formato mais legível
        try:
            date_obj = datetime.strptime(item['data'], '%Y-%m-%d')
            label = date_obj.strftime('%d/%m')
        except:
            label = item['data']
        
        labels.append(label)
        valores.append(item['quantidade'])
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [{
            'x': labels,
            'y': valores,
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Pedidos por Dia',
            'line': {
                'color': CORES['primaria'],
                'width': 4,
                'shape': 'spline',
                'smoothing': 1.3
            },
            'marker': {
                'color': CORES['surface'],
                'size': 12,
                'line': {
                    'color': CORES['primaria'],
                    'width': 3
                },
                'symbol': 'circle'
            },
            'fill': 'tonexty',
            'fillcolor': f"rgba({int(CORES['primaria'][1:3], 16)}, {int(CORES['primaria'][3:5], 16)}, {int(CORES['primaria'][5:7], 16)}, 0.1)",
            'hovertemplate': '<b>%{x}</b><br>Pedidos: %{y}<extra></extra>',
            'hoverlabel': {
                'bgcolor': CORES['surface'],
                'bordercolor': CORES['primaria'],
                'font': {'color': CORES['neutro_escuro'], 'size': 14}
            }
        }],
        'layout': {
            'title': {
                'text': '📈 Tendência de Pedidos (Últimos 30 Dias)',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'xaxis': {
                'title': {
                    'text': 'Período',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'showgrid': False,
                'showline': True,
                'linecolor': CORES['neutro_claro'],
                'linewidth': 1,
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'zeroline': False
            },
            'yaxis': {
                'title': {
                    'text': 'Quantidade de Pedidos',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'showgrid': True,
                'gridcolor': 'rgba(148, 163, 184, 0.2)',
                'gridwidth': 1,
                'showline': False,
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'zeroline': False
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 60, 'r': 40, 't': 80, 'b': 60},
            'showlegend': False,
            'hovermode': 'x unified',
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'}
        }
    }
    
    return chart_data

def generate_status_chart(codigo_rca=None):
    """Gera dados para o gráfico de status das entregas (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    status_data = data.get('status_entregas', [])
    
    # Se não há dados, gera dados de exemplo
    if not status_data:
        status_data = [
            {'status': 'Entregue', 'quantidade': 0},
            {'status': 'Em Trânsito', 'quantidade': 0},
            {'status': 'Pendente', 'quantidade': 0}
        ]
    
    # Mapeia cores para cada status
    status_colors = {
        'Entregue': CORES['sucesso'],
        'Em Trânsito': CORES['alerta'],
        'Pendente': CORES['critico'],
        'ENTREGUE': CORES['sucesso'],
        'EM TRÂNSITO': CORES['alerta'],
        'PENDENTE': CORES['critico']
    }
    
    labels = []
    valores = []
    cores = []
    
    for item in status_data:
        status = item['status'] or 'Pendente'
        labels.append(status)
        valores.append(item['quantidade'])
        cores.append(status_colors.get(status, CORES['neutro']))
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [{
            'labels': labels,
            'values': valores,
            'type': 'pie',
            'hole': 0.5,
            'marker': {
                'colors': cores,
                'line': {
                    'color': CORES['surface'],
                    'width': 3
                }
            },
            'textinfo': 'label+percent',
            'textposition': 'outside',
            'textfont': {
                'size': 14,
                'color': CORES['neutro_escuro'],
                'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
            },
            'hovertemplate': '<b>%{label}</b><br>Quantidade: %{value}<br>Percentual: %{percent}<extra></extra>',
            'hoverlabel': {
                'bgcolor': CORES['surface'],
                'bordercolor': CORES['neutro_claro'],
                'font': {'color': CORES['neutro_escuro'], 'size': 14, 'family': 'Inter'}
            },
            'pull': [0.05, 0, 0],  # Destaca o primeiro slice
            'rotation': 90
        }],
        'layout': {
            'title': {
                'text': '🎯 Status das Entregas',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'showlegend': True,
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.15,
                'xanchor': 'center',
                'x': 0.5,
                'font': {
                    'size': 13,
                    'color': CORES['neutro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'bgcolor': 'rgba(255, 255, 255, 0.8)',
                'bordercolor': CORES['neutro_claro'],
                'borderwidth': 1
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 40, 'r': 40, 't': 80, 'b': 100},
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'annotations': [{
                'text': f'<b>{sum(valores)}</b><br><span style="font-size:12px; color:{CORES["neutro"]}">Total</span>',
                'x': 0.5,
                'y': 0.5,
                'font': {
                    'size': 18,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter'
                },
                'showarrow': False
            }]
        }
    }
    
    return chart_data

def generate_performance_chart():
    """Gera dados para gráfico de performance mensal (Plotly.js)"""
    # Dados de exemplo para performance mensal
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
    pedidos = [45, 52, 38, 67, 59, 73]
    entregas = [42, 48, 35, 63, 56, 70]
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [
            {
                'x': meses,
                'y': pedidos,
                'type': 'bar',
                'name': '📦 Pedidos',
                'marker': {
                    'color': [f'rgba({int(CORES["primaria"][1:3], 16)}, {int(CORES["primaria"][3:5], 16)}, {int(CORES["primaria"][5:7], 16)}, 0.8)' for _ in meses],
                    'line': {
                        'color': CORES['primaria'],
                        'width': 2
                    }
                },
                'hovertemplate': '<b>%{x}</b><br>Pedidos: %{y}<extra></extra>',
                'hoverlabel': {
                    'bgcolor': CORES['surface'],
                    'bordercolor': CORES['primaria'],
                    'font': {'color': CORES['neutro_escuro'], 'size': 14, 'family': 'Inter'}
                }
            },
            {
                'x': meses,
                'y': entregas,
                'type': 'bar',
                'name': '🚚 Entregas',
                'marker': {
                    'color': [f'rgba({int(CORES["sucesso"][1:3], 16)}, {int(CORES["sucesso"][3:5], 16)}, {int(CORES["sucesso"][5:7], 16)}, 0.8)' for _ in meses],
                    'line': {
                        'color': CORES['sucesso'],
                        'width': 2
                    }
                },
                'hovertemplate': '<b>%{x}</b><br>Entregas: %{y}<extra></extra>',
                'hoverlabel': {
                    'bgcolor': CORES['surface'],
                    'bordercolor': CORES['sucesso'],
                    'font': {'color': CORES['neutro_escuro'], 'size': 14, 'family': 'Inter'}
                }
            }
        ],
        'layout': {
            'title': {
                'text': '📊 Performance Mensal',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'xaxis': {
                'title': {
                    'text': 'Período',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'showgrid': False,
                'showline': True,
                'linecolor': CORES['neutro_claro'],
                'linewidth': 1,
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'zeroline': False
            },
            'yaxis': {
                'title': {
                    'text': 'Quantidade',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'showgrid': True,
                'gridcolor': 'rgba(148, 163, 184, 0.2)',
                'gridwidth': 1,
                'showline': False,
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'zeroline': False
            },
            'barmode': 'group',
            'bargap': 0.3,
            'bargroupgap': 0.1,
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 60, 'r': 40, 't': 80, 'b': 60},
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': 1.02,
                'xanchor': 'center',
                'x': 0.5,
                'font': {
                    'size': 13,
                    'color': CORES['neutro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'bgcolor': 'rgba(255, 255, 255, 0.8)',
                'bordercolor': CORES['neutro_claro'],
                'borderwidth': 1
            },
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'hovermode': 'x unified'
        }
    }
    
    return chart_data

def generate_rca_chart(codigo_rca=None):
    """Gera dados para o gráfico de agendamentos por RCA (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    rca_data = data.get('agendamentos_por_rca', [])
    
    # Se não há dados, retorna gráfico vazio
    if not rca_data:
        rca_data = [{'rca': 'Sem dados', 'quantidade': 0}]
    
    # Limita aos top 10 RCAs
    rca_data = rca_data[:10]
    
    labels = [item['rca'] for item in rca_data]
    valores = [item['quantidade'] for item in rca_data]
    
    # Gera cores gradientes para as barras
    cores = []
    for i, _ in enumerate(valores):
        intensity = 1 - (i * 0.1)  # Diminui a intensidade gradualmente
        r = int(76 * intensity)  # Componente R da cor primária
        g = int(175 * intensity)  # Componente G da cor primária
        b = int(80 * intensity)  # Componente B da cor primária
        cores.append(f'rgba({r}, {g}, {b}, 0.8)')
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [{
            'x': labels,
            'y': valores,
            'type': 'bar',
            'name': 'Agendamentos por RCA',
            'marker': {
                'color': cores,
                'line': {
                    'color': CORES['primaria'],
                    'width': 2
                },
                'opacity': 0.8
            },
            'hovertemplate': '<b>%{x}</b><br>Agendamentos: %{y}<extra></extra>',
            'hoverlabel': {
                'bgcolor': CORES['surface'],
                'bordercolor': CORES['primaria'],
                'font': {'color': CORES['neutro_escuro'], 'size': 14, 'family': 'Inter'}
            }
        }],
        'layout': {
            'title': {
                'text': '👥 Top 10 RCAs - Agendamentos (30 dias)',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'xaxis': {
                'title': {
                    'text': 'RCA',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickangle': -45,
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'gridcolor': CORES['neutro_claro'],
                'gridwidth': 1
            },
            'yaxis': {
                'title': {
                    'text': 'Quantidade de Agendamentos',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'gridcolor': CORES['neutro_claro'],
                'gridwidth': 1
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 60, 'r': 40, 't': 80, 'b': 120},
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'showlegend': False
        }
    }
    
    return chart_data

def generate_horarios_chart(codigo_rca=None):
    """Gera dados para o gráfico de distribuição de horários (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    horarios_data = data.get('horarios_entrega', [])
    
    # Se não há dados, gera dados de exemplo
    if not horarios_data:
        horarios_data = [
            {'periodo': 'Manhã (6h-12h)', 'quantidade': 0},
            {'periodo': 'Tarde (12h-18h)', 'quantidade': 0},
            {'periodo': 'Noite (18h-24h)', 'quantidade': 0},
            {'periodo': 'Madrugada (0h-6h)', 'quantidade': 0}
        ]
    
    # Mapeia cores para cada período
    periodo_colors = {
        'Manhã (6h-12h)': '#FFD700',  # Dourado
        'Tarde (12h-18h)': '#FF8C00',  # Laranja
        'Noite (18h-24h)': '#4169E1',  # Azul
        'Madrugada (0h-6h)': '#2F4F4F'  # Cinza escuro
    }
    
    labels = [item['periodo'] for item in horarios_data]
    valores = [item['quantidade'] for item in horarios_data]
    cores = [periodo_colors.get(item['periodo'], CORES['neutro']) for item in horarios_data]
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [{
            'labels': labels,
            'values': valores,
            'type': 'pie',
            'hole': 0.4,
            'marker': {
                'colors': cores,
                'line': {
                    'color': CORES['surface'],
                    'width': 3
                }
            },
            'textinfo': 'label+percent',
            'textposition': 'outside',
            'textfont': {
                'size': 13,
                'color': CORES['neutro_escuro'],
                'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
            },
            'hovertemplate': '<b>%{label}</b><br>Entregas: %{value}<br>Percentual: %{percent}<extra></extra>',
            'hoverlabel': {
                'bgcolor': CORES['surface'],
                'bordercolor': CORES['neutro_claro'],
                'font': {'color': CORES['neutro_escuro'], 'size': 14, 'family': 'Inter'}
            }
        }],
        'layout': {
            'title': {
                'text': '🕐 Distribuição de Horários de Entrega',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'showlegend': True,
            'legend': {
                'orientation': 'v',
                'yanchor': 'middle',
                'y': 0.5,
                'xanchor': 'left',
                'x': 1.05,
                'font': {
                    'size': 12,
                    'color': CORES['neutro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                }
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 40, 'r': 150, 't': 80, 'b': 40},
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'annotations': [{
                'text': f'<b>{sum(valores)}</b><br><span style="font-size:12px; color:{CORES["neutro"]}">Total</span>',
                'x': 0.5,
                'y': 0.5,
                'font': {
                    'size': 16,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter'
                },
                'showarrow': False
            }]
        }
    }
    
    return chart_data

def generate_tendencia_chart(codigo_rca=None):
    """Gera dados para o gráfico de tendência mensal (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    tendencia_data = data.get('tendencia_mensal', [])
    
    # Se não há dados, gera dados de exemplo
    if not tendencia_data:
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        hoje = datetime.now()
        tendencia_data = []
        for i in range(6):
            mes = hoje - relativedelta(months=5-i)
            tendencia_data.append({
                'mes_label': mes.strftime('%b/%Y'),
                'total_pedidos': 0,
                'agendados': 0,
                'entregues': 0
            })
    
    labels = [item['mes_label'] for item in tendencia_data]
    total_pedidos = [item['total_pedidos'] for item in tendencia_data]
    agendados = [item['agendados'] for item in tendencia_data]
    entregues = [item['entregues'] for item in tendencia_data]
    
    # Formato Plotly.js Premium
    chart_data = {
        'data': [
            {
                'x': labels,
                'y': total_pedidos,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '📦 Total Pedidos',
                'line': {
                    'color': CORES['primaria'],
                    'width': 3,
                    'shape': 'spline'
                },
                'marker': {
                    'color': CORES['primaria'],
                    'size': 8,
                    'line': {'color': CORES['surface'], 'width': 2}
                }
            },
            {
                'x': labels,
                'y': agendados,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '📅 Agendados',
                'line': {
                    'color': CORES['alerta'],
                    'width': 3,
                    'shape': 'spline'
                },
                'marker': {
                    'color': CORES['alerta'],
                    'size': 8,
                    'line': {'color': CORES['surface'], 'width': 2}
                }
            },
            {
                'x': labels,
                'y': entregues,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '✅ Entregues',
                'line': {
                    'color': CORES['sucesso'],
                    'width': 3,
                    'shape': 'spline'
                },
                'marker': {
                    'color': CORES['sucesso'],
                    'size': 8,
                    'line': {'color': CORES['surface'], 'width': 2}
                }
            }
        ],
        'layout': {
            'title': {
                'text': '📈 Tendência Mensal - Últimos 6 Meses',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'xaxis': {
                'title': {
                    'text': 'Período',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'gridcolor': CORES['neutro_claro'],
                'gridwidth': 1
            },
            'yaxis': {
                'title': {
                    'text': 'Quantidade',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'gridcolor': CORES['neutro_claro'],
                'gridwidth': 1
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 60, 'r': 40, 't': 80, 'b': 60},
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'}
            },
            'hovermode': 'x unified'
        }
    }
    
    return chart_data

def generate_performance_semanal_chart(codigo_rca=None):
    """Gera dados para o gráfico de performance semanal (Plotly.js)"""
    data = get_graficos_data(codigo_rca)
    performance_data = data.get('performance_semanal', [])
    
    # Se não há dados, gera dados de exemplo
    if not performance_data:
        performance_data = [
            {'semana': 'Semana 1', 'total_pedidos': 0, 'agendados': 0, 'taxa_agendamento': 0},
            {'semana': 'Semana 2', 'total_pedidos': 0, 'agendados': 0, 'taxa_agendamento': 0},
            {'semana': 'Semana 3', 'total_pedidos': 0, 'agendados': 0, 'taxa_agendamento': 0},
            {'semana': 'Semana 4', 'total_pedidos': 0, 'agendados': 0, 'taxa_agendamento': 0}
        ]
    
    labels = [item['semana'] for item in performance_data]
    total_pedidos = [item['total_pedidos'] for item in performance_data]
    agendados = [item['agendados'] for item in performance_data]
    taxa_agendamento = [item['taxa_agendamento'] for item in performance_data]
    
    # Formato Plotly.js Premium com eixo Y secundário
    chart_data = {
        'data': [
            {
                'x': labels,
                'y': total_pedidos,
                'type': 'bar',
                'name': '📦 Total Pedidos',
                'marker': {
                    'color': f'rgba({int(CORES["primaria"][1:3], 16)}, {int(CORES["primaria"][3:5], 16)}, {int(CORES["primaria"][5:7], 16)}, 0.7)',
                    'line': {'color': CORES['primaria'], 'width': 2}
                },
                'yaxis': 'y'
            },
            {
                'x': labels,
                'y': agendados,
                'type': 'bar',
                'name': '📅 Agendados',
                'marker': {
                    'color': f'rgba({int(CORES["sucesso"][1:3], 16)}, {int(CORES["sucesso"][3:5], 16)}, {int(CORES["sucesso"][5:7], 16)}, 0.7)',
                    'line': {'color': CORES['sucesso'], 'width': 2}
                },
                'yaxis': 'y'
            },
            {
                'x': labels,
                'y': taxa_agendamento,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '📊 Taxa Agendamento (%)',
                'line': {
                    'color': CORES['critico'],
                    'width': 4
                },
                'marker': {
                    'color': CORES['critico'],
                    'size': 10,
                    'line': {'color': CORES['surface'], 'width': 2}
                },
                'yaxis': 'y2'
            }
        ],
        'layout': {
            'title': {
                'text': '📊 Performance Semanal - Últimas 4 Semanas',
                'font': {
                    'size': 20,
                    'color': CORES['neutro_escuro'],
                    'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
                },
                'x': 0.5,
                'xanchor': 'center',
                'pad': {'t': 20}
            },
            'xaxis': {
                'title': {
                    'text': 'Período',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'}
            },
            'yaxis': {
                'title': {
                    'text': 'Quantidade de Pedidos',
                    'font': {'size': 14, 'color': CORES['neutro'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'},
                'gridcolor': CORES['neutro_claro'],
                'gridwidth': 1,
                'side': 'left'
            },
            'yaxis2': {
                'title': {
                    'text': 'Taxa de Agendamento (%)',
                    'font': {'size': 14, 'color': CORES['critico'], 'family': 'Inter'}
                },
                'tickfont': {'size': 12, 'color': CORES['critico'], 'family': 'Inter'},
                'overlaying': 'y',
                'side': 'right',
                'range': [0, 100]
            },
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'margin': {'l': 60, 'r': 80, 't': 80, 'b': 60},
            'font': {'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'},
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 12, 'color': CORES['neutro'], 'family': 'Inter'}
            },
            'barmode': 'group'
        }
    }
    
    return chart_data

def generate_all_charts(codigo_rca=None):
    """Gera todos os gráficos para o dashboard"""
    return {
        'kpis': generate_kpis(codigo_rca),
        'pedidos_chart': generate_pedidos_chart(codigo_rca),
        'status_chart': generate_status_chart(codigo_rca),
        'performance_chart': generate_performance_chart(),
        'rca_chart': generate_rca_chart(codigo_rca),
        'horarios_chart': generate_horarios_chart(codigo_rca),
        'tendencia_chart': generate_tendencia_chart(codigo_rca),
        'performance_semanal_chart': generate_performance_semanal_chart(codigo_rca)
    }

def get_chart_colors():
    """Retorna as cores disponíveis para gráficos"""
    return CORES

def format_chart_data(data, chart_type='line'):
    """Formata dados genéricos para diferentes tipos de gráfico"""
    if chart_type == 'line':
        return {
            'type': 'line',
            'data': data,
            'options': {
                'responsive': True,
                'maintainAspectRatio': False
            }
        }
    elif chart_type == 'bar':
        return {
            'type': 'bar',
            'data': data,
            'options': {
                'responsive': True,
                'maintainAspectRatio': False
            }
        }
    elif chart_type == 'doughnut':
        return {
            'type': 'doughnut',
            'data': data,
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'cutout': '60%'
            }
        }
    
    return data