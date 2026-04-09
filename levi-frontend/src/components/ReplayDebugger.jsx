import React, { useState, useEffect } from 'react';
import styled, from 'styled-components';

// Cybernetic Styling based on v14.0 Sovereign rules
const ReplayContainer = styled.div`
  background: rgba(10, 14, 23, 0.95);
  border: 1px solid rgba(0, 255, 204, 0.3);
  border-radius: 8px;
  color: #a0aec0;
  padding: 1.5rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.05);
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const Header = styled.h2`
  color: #00ffcc;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 1.25rem;
  margin: 0;
  border-bottom: 1px solid rgba(0, 255, 204, 0.2);
  padding-bottom: 0.5rem;
`;

const Timeline = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 400px;
  overflow-y: auto;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 255, 204, 0.3);
    border-radius: 3px;
  }
`;

const TraceStep = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(15, 23, 42, 0.6);
  padding: 0.75rem 1rem;
  border-left: 3px solid ${props => props.success ? '#00ffcc' : '#f56565'};
  border-radius: 0 4px 4px 0;
  font-size: 0.875rem;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(30, 41, 59, 0.8);
    transform: translateX(2px);
  }
`;

const StepID = styled.span`
  color: #cbd5e0;
  font-weight: 600;
  min-width: 80px;
`;

const AgentLabel = styled.span`
  color: #38b2ac;
  font-size: 0.75rem;
  background: rgba(56, 178, 172, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid rgba(56, 178, 172, 0.3);
`;

const Latency = styled.span`
  color: #a0aec0;
  font-size: 0.75rem;
  margin-left: auto;
`;

const Button = styled.button`
  background: transparent;
  color: #00ffcc;
  border: 1px solid #00ffcc;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  text-transform: uppercase;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(0, 255, 204, 0.1);
    box-shadow: 0 0 10px rgba(0, 255, 204, 0.2);
  }
  
  &:disabled {
    border-color: #4a5568;
    color: #4a5568;
    cursor: not-allowed;
    background: transparent;
    box-shadow: none;
  }
`;

const InputGroup = styled.div`
  display: flex;
  gap: 0.5rem;
`;

const Input = styled.input`
  flex: 1;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 255, 204, 0.3);
  color: #e2e8f0;
  padding: 0.5rem;
  border-radius: 4px;
  font-family: inherit;
  
  &:focus {
    outline: none;
    border-color: #00ffcc;
  }
`;

export const ReplayDebugger = () => {
  const [traceId, setTraceId] = useState('');
  const [traceData, setTraceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTrace = async () => {
    if (!traceId) return;
    setLoading(true);
    setError(null);
    try {
      // In production, this would call the actual API
      const response = await fetch(`/api/v1/traces/${traceId}`);
      if (!response.ok) throw new Error('Trace not found in MCM storage');
      const data = await response.json();
      setTraceData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ReplayContainer>
      <Header>Sovereign Replay Engine</Header>
      <InputGroup>
        <Input 
          placeholder="Enter deterministic TRACE_ID..."
          value={traceId}
          onChange={e => setTraceId(e.target.value)}
        />
        <Button onClick={fetchTrace} disabled={loading || !traceId}>
          {loading ? 'Reconciling...' : 'Load Trace'}
        </Button>
      </InputGroup>
      
      {error && <div style={{color: '#f56565', fontSize: '0.875rem'}}>{error}</div>}
      
      {traceData && traceData.steps && (
        <Timeline>
          {traceData.steps.map((step, idx) => (
            <TraceStep key={idx} success={step.success ?? true}>
              <StepID>{step.data?.node_id || step.step}</StepID>
              {step.data?.agent && <AgentLabel>{step.data.agent}</AgentLabel>}
              <div style={{color: '#e2e8f0'}}>{step.data?.message || 'Executing node logic...'}</div>
              {step.data?.latency_ms && <Latency>{step.data.latency_ms}ms</Latency>}
            </TraceStep>
          ))}
        </Timeline>
      )}
    </ReplayContainer>
  );
};

export default ReplayDebugger;
