import { useNavigate } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = () => {
  const navigate = useNavigate();

  return (
    <div className="sidebar">
      <button className="botao-sidebar" onClick={() => navigate('/')}>Dashboard</button>
      <button className="botao-sidebar" onClick={() => navigate('/acoes')}>Ações Recomendadas</button>
      <button className="botao-sidebar" onClick={() => navigate('/historico')}>Histórico</button>
    </div>
  );
};

export default Sidebar;

