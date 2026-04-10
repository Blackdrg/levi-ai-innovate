import styled from 'styled-components';

// Cybernetic Styling based on v14.0 Sovereign rules
// ... rest of styled components remain the same ...

const ReplayNodeButton = styled.button`
  background: rgba(0, 255, 204, 0.1);
  border: 1px solid rgba(0, 255, 204, 0.4);
  color: #00ffcc;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 0.5rem;
  
  &:hover {
    background: rgba(0, 255, 204, 0.2);
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

  const replayNode = async (nodeId, inputs) => {
    // 🛡️ v14.1.0: Deterministic Replay Injection
    try {
      const response = await fetch('/api/v8/debug/replay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json.stringify({ node_id: nodeId, inputs, trace_id: traceId })
      });
      alert(`Replay initiated for ${nodeId}. Check console for pulse results.`);
    } catch (err) {
      console.error("Replay failure:", err);
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
              <div style={{color: '#e2e8f0', flex: 1}}>{step.data?.message || 'Executing node logic...'}</div>
              <ReplayNodeButton onClick={() => replayNode(step.data?.node_id || step.step, step.data?.inputs)}>
                REPLAY
              </ReplayNodeButton>
              {step.data?.latency_ms && <Latency>{step.data.latency_ms}ms</Latency>}
            </TraceStep>
          ))}
        </Timeline>
      )}
    </ReplayContainer>
  );
};

export default ReplayDebugger;
