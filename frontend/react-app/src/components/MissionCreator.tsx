import React, { useState } from 'react';
import { useNeuralContext } from '../contexts/NeuralContext';
import { Send, Zap } from 'lucide-react';

export const MissionCreator: React.FC = () => {
    const [objective, setObjective] = useState('');
    const { dispatchMission } = useNeuralContext();
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!objective.trim() || loading) return;

        setLoading(true);
        await dispatchMission(objective);
        setObjective('');
        setLoading(false);
    };

    return (
        <form onSubmit={handleSubmit} className="mission-creator">
            <div className="input-wrapper">
                <input 
                    type="text" 
                    value={objective} 
                    onChange={(e) => setObjective(e.target.value)}
                    placeholder="Define a new mission for LEVI-AI..."
                    disabled={loading}
                />
                <button type="submit" disabled={loading || !objective.trim()}>
                    {loading ? <Zap className="animate-pulse" /> : <Send />}
                </button>
            </div>
            <style>{`
                .mission-creator {
                    margin-bottom: 2rem;
                    width: 100%;
                }
                .input-wrapper {
                    display: flex;
                    gap: 1rem;
                    background: var(--bg-panel);
                    padding: 0.5rem;
                    border-radius: 12px;
                    border: 1px solid var(--border);
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                }
                .input-wrapper input {
                    flex: 1;
                    background: transparent;
                    border: none;
                    color: white;
                    padding: 0.75rem 1rem;
                    outline: none;
                    font-family: inherit;
                }
                .input-wrapper button {
                    background: var(--primary);
                    color: var(--bg-dark);
                    border: none;
                    border-radius: 8px;
                    width: 44px;
                    height: 44px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .input-wrapper button:hover:not(:disabled) {
                    transform: scale(1.05);
                    box-shadow: 0 0 15px var(--primary);
                }
                .input-wrapper button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
            `}</style>
        </form>
    );
};
