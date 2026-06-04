// src/components/MarketMonitor.tsx
import React, { useState, useEffect } from 'react';
import './MarketMonitor.css';

interface CryptoFuture {
  nomeParCripto: string;
  valorAtual: number;
  qtdQuedas: number;
  valorDecrescimo: number;
  valorFuturo: number;
  percentAcerto: number;
}

interface CryptoSpot extends CryptoFuture {}

interface BolsaTrade {
  nomeAtivo: string;
  valorAtual: number;
  qtdQuedas: number;
  valorDecrescimo: number;
  valorFuturo: number;
  percentAcerto: number;
}

interface BolsaBuyAndHold {
  ativo: string;
  valorAtual: number;
  dy: number;
  pl: number;
  pvpa: number;
  roe: number;
  margemLiquida: number;
  dividaEbitda: number;
  liquidezCorrente: number;
  percentFiltrosAceitos: number;
}

interface GrahamAtivo {
  ativo: string;
  valorJusto: number;
  percentValorizacao5Anos: number;
}

type ViewType = 'cripto-futuros' | 'cripto-spot' | 'bolsa-trade' | 'bolsa-buyandhold';

const MarketMonitor: React.FC = () => {
  const [selectedView, setSelectedView] = useState<ViewType>('bolsa-buyandhold');
  const [cryptoFuturos, setCryptoFuturos] = useState<CryptoFuture[]>([]);
  const [cryptoSpot, setCryptoSpot] = useState<CryptoSpot[]>([]);
  const [bolsaTrade, setBolsaTrade] = useState<BolsaTrade[]>([]);
  const [bolsaBuyAndHold, setBolsaBuyAndHold] = useState<BolsaBuyAndHold[]>([]);
  const [grahamTop10, setGrahamTop10] = useState<GrahamAtivo[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Função para buscar dados do backend (ajuste a URL conforme seu backend)
  const fetchData = async (view: ViewType) => {
    setLoading(true);
    setError(null);
    try {
      // Exemplos de endpoints - ajuste conforme sua API no backend
      let url = '';
      
      switch (view) {
        case 'cripto-futuros':
          url = 'http://localhost:3001/api/cripto/futuros';
          break;
        case 'cripto-spot':
          url = 'http://localhost:3001/api/cripto/spot';
          break;
        case 'bolsa-trade':
          url = 'http://localhost:3001/api/bolsa/trade';
          break;
        case 'bolsa-buyandhold':
          url = 'http://localhost:3001/api/bolsa/buyandhold';
          break;
      }

      const response = await fetch(url);
      if (!response.ok) throw new Error('Erro ao buscar dados');

      const data = await response.json();

      if (view === 'cripto-futuros') setCryptoFuturos(data);
      if (view === 'cripto-spot') setCryptoSpot(data);
      if (view === 'bolsa-trade') setBolsaTrade(data);
      if (view === 'bolsa-buyandhold') {
        setBolsaBuyAndHold(data.filtros || []);
        setGrahamTop10(data.grahamTop10 || []);
      }
    } catch (err) {
      setError('Erro ao carregar dados. Verifique se o backend está rodando.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedView);
  }, [selectedView]);

  const renderTable = () => {
    if (loading) return <div className="loading">Carregando dados...</div>;
    if (error) return <div className="error">{error}</div>;

    switch (selectedView) {
      case 'cripto-futuros':
      case 'cripto-spot':
        const dataCrypto = selectedView === 'cripto-futuros' ? cryptoFuturos : cryptoSpot;
        return (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nome Par Cripto (USDT)</th>
                <th>Valor Atual</th>
                <th>Qtd Quedas 5%</th>
                <th>Valor Decréscimo (5%)</th>
                <th>Valor Futuro (15%)</th>
                <th>% Acerto</th>
              </tr>
            </thead>
            <tbody>
              {dataCrypto.map((item, index) => (
                <tr key={index}>
                  <td>{item.nomeParCripto}</td>
                  <td>R$ {item.valorAtual.toFixed(4)}</td>
                  <td>{item.qtdQuedas}</td>
                  <td>R$ {item.valorDecrescimo.toFixed(4)}</td>
                  <td>R$ {item.valorFuturo.toFixed(4)}</td>
                  <td>{item.percentAcerto.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case 'bolsa-trade':
        return (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nome Ativo</th>
                <th>Valor Atual</th>
                <th>Qtd Quedas</th>
                <th>Valor Decréscimo (5%)</th>
                <th>Valor Futuro (15%)</th>
                <th>% Acerto</th>
              </tr>
            </thead>
            <tbody>
              {bolsaTrade.map((item, index) => (
                <tr key={index}>
                  <td>{item.nomeAtivo}</td>
                  <td>R$ {item.valorAtual.toFixed(2)}</td>
                  <td>{item.qtdQuedas}</td>
                  <td>R$ {item.valorDecrescimo.toFixed(2)}</td>
                  <td>R$ {item.valorFuturo.toFixed(2)}</td>
                  <td>{item.percentAcerto.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case 'bolsa-buyandhold':
        return (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th>Valor Atual</th>
                  <th>DY</th>
                  <th>P/L</th>
                  <th>P/VPA</th>
                  <th>ROE</th>
                  <th>Margem Líquida</th>
                  <th>Dívida/EBITDA</th>
                  <th>Liquidez Corrente</th>
                  <th>% Filtros Aceitos</th>
                </tr>
              </thead>
              <tbody>
                {bolsaBuyAndHold
                  .sort((a, b) => b.percentFiltrosAceitos - a.percentFiltrosAceitos)
                  .map((item, index) => (
                    <tr key={index}>
                      <td>{item.ativo}</td>
                      <td>R$ {item.valorAtual.toFixed(2)}</td>
                      <td>{item.dy.toFixed(2)}%</td>
                      <td>{item.pl.toFixed(2)}</td>
                      <td>{item.pvpa.toFixed(2)}</td>
                      <td>{item.roe.toFixed(2)}%</td>
                      <td>{item.margemLiquida.toFixed(2)}%</td>
                      <td>{item.dividaEbitda.toFixed(2)}</td>
                      <td>{item.liquidezCorrente.toFixed(2)}</td>
                      <td>{item.percentFiltrosAceitos.toFixed(1)}%</td>
                    </tr>
                  ))}
              </tbody>
            </table>

            {/* Tabela Graham - Top 10 */}
            <h3>Top 10 Ativos Mais Vantajosos (Graham)</h3>
            <table className="data-table graham-table">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th>Valor Justo</th>
                  <th>% Valorização 5 Anos</th>
                </tr>
              </thead>
              <tbody>
                {grahamTop10.map((item, index) => (
                  <tr key={index}>
                    <td>{item.ativo}</td>
                    <td>R$ {item.valorJusto.toFixed(2)}</td>
                    <td>{item.percentValorizacao5Anos.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="market-monitor">
      <header>
        <h1>📈 Monitoramento Estatístico - Bolsa & Cripto</h1>
        <p>Baseado no repositório: monitoramento_estatistico_bolsa_cripto</p>
      </header>

      <div className="selector">
        <button 
          className={selectedView === 'cripto-futuros' ? 'active' : ''} 
          onClick={() => setSelectedView('cripto-futuros')}
        >
          Cripto (Futuros)
        </button>
        <button 
          className={selectedView === 'cripto-spot' ? 'active' : ''} 
          onClick={() => setSelectedView('cripto-spot')}
        >
          Cripto (Spot)
        </button>
        <button 
          className={selectedView === 'bolsa-trade' ? 'active' : ''} 
          onClick={() => setSelectedView('bolsa-trade')}
        >
          Bolsa (Trade)
        </button>
        <button 
          className={selectedView === 'bolsa-buyandhold' ? 'active' : ''} 
          onClick={() => setSelectedView('bolsa-buyandhold')}
        >
          Bolsa (Buy & Hold)
        </button>
      </div>

      <div className="content">
        {renderTable()}
      </div>
    </div>
  );
};

export default MarketMonitor;