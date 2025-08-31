import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header/';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import AcoesRecomendadas from './pages/AcoesRecomendadas/Index';
import Historico from './pages/Historico';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Header />
        <div className="conteudo">
          <Sidebar />
          <main className="principal">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/acoes" element={<AcoesRecomendadas />} />
              <Route path="/historico" element={<Historico />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
