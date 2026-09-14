import React, { useState } from 'react';
import { triageService } from '../api/triage';
import type { TriageDetail } from '../types';
import { Stethoscope, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

export const TriageMock: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TriageDetail | null>(null);
  const [error, setError] = useState('');

  const handleRunMock = async (scenario: 'routine' | 'attention' | 'urgent') => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await triageService.runMockTriage({ scenario });
      setResult(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run mock triage');
    } finally {
      setLoading(false);
    }
  };

  const getTriageColor = (level: string) => {
    if (level === 'URGENT') return 'badge-danger';
    if (level === 'ATTENTION') return 'badge-warning';
    return 'badge-success';
  };

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold mb-2">Triage Simulator Demo</h1>
        <p className="text-muted">Test the Multi-Agent Clinical Triage Pipeline</p>
      </div>

      <div className="card shadow-sm flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Run Triage Scenario</h3>
          <p className="text-sm text-muted">Select a scenario to simulate a post-call triage pipeline execution.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => handleRunMock('routine')} disabled={loading} className="btn btn-outline border-success text-success hover:bg-success-bg">
            <CheckCircle size={18} /> Routine
          </button>
          <button onClick={() => handleRunMock('attention')} disabled={loading} className="btn btn-outline border-warning text-warning hover:bg-warning-bg">
            <Clock size={18} /> Attention
          </button>
          <button onClick={() => handleRunMock('urgent')} disabled={loading} className="btn btn-outline border-danger text-danger hover:bg-danger-bg">
            <AlertTriangle size={18} /> Urgent
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded bg-danger-bg text-danger border border-danger">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center p-12 text-muted animate-fade-in">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
          <p>Running Multi-Agent Consensus Engine...</p>
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-6 animate-fade-in">
          {/* Summary Card */}
          <div className="card shadow-md">
            <div className="flex justify-between items-start border-b pb-4 mb-4">
              <div>
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Stethoscope className="text-primary" />
                  Final Triage Result
                </h2>
                <div className="text-sm text-muted mt-1">
                  Call ID: {result.call_id} | Protocol: {result.protocol_name}
                </div>
              </div>
              <div className="text-right">
                <span className={`badge ${getTriageColor(result.triage_level)} text-lg px-4 py-2`}>
                  {result.triage_level}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-3 bg-bg-primary rounded border">
                <div className="text-xs text-muted uppercase font-bold">Consensus Method</div>
                <div className="font-semibold">{result.consensus_method}</div>
              </div>
              <div className="p-3 bg-bg-primary rounded border">
                <div className="text-xs text-muted uppercase font-bold">Confidence</div>
                <div className="font-semibold">{result.consensus_level}</div>
              </div>
              <div className="p-3 bg-bg-primary rounded border">
                <div className="text-xs text-muted uppercase font-bold">Disagreement</div>
                <div className="font-semibold">{result.disagreement_detected ? 'Yes' : 'No'}</div>
              </div>
              <div className="p-3 bg-bg-primary rounded border">
                <div className="text-xs text-muted uppercase font-bold">EHR Action</div>
                <div className="font-semibold">{result.ehr_action_status}</div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2 text-sm text-muted uppercase">Reasoning Summary</h3>
              <p className="text-sm p-4 bg-bg-tertiary rounded-lg border leading-relaxed">
                {result.reasoning_summary}
              </p>
            </div>
            
            <div className="mt-4">
              <h3 className="font-semibold mb-2 text-sm text-muted uppercase">Recommended Action</h3>
              <p className="text-sm p-4 bg-primary-light text-primary-hover rounded-lg border border-primary leading-relaxed font-medium">
                {result.recommended_action}
              </p>
            </div>
          </div>

          {/* Agents View */}
          <h3 className="text-lg font-bold mt-4">Independent Agent Assessments</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {result.agent_assessments?.map((agent: any, idx: number) => (
              <div key={idx} className="card shadow-sm flex flex-col h-full">
                <div className="flex justify-between items-center border-b pb-3 mb-3">
                  <h4 className="font-semibold text-primary">{agent.agent_type}</h4>
                  <span className={`badge ${getTriageColor(agent.proposed_triage_level)}`}>
                    {agent.proposed_triage_level}
                  </span>
                </div>
                <div className="flex-1 text-sm text-secondary overflow-y-auto" style={{ maxHeight: '200px' }}>
                  {agent.reasoning}
                </div>
              </div>
            ))}
          </div>
          
          {/* Findings & Red Flags */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div className="card shadow-sm">
              <h3 className="text-lg font-bold border-b pb-3 mb-3 text-danger flex items-center gap-2">
                <AlertTriangle size={20} /> Red Flags
              </h3>
              {result.red_flags?.length > 0 ? (
                <ul className="space-y-2">
                  {result.red_flags.map((flag: any, i: number) => (
                    <li key={i} className="text-sm p-2 bg-danger-bg text-danger-text rounded">
                      • {flag}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted italic">No red flags detected.</p>
              )}
            </div>
            
            <div className="card shadow-sm">
              <h3 className="text-lg font-bold border-b pb-3 mb-3 text-success flex items-center gap-2">
                <CheckCircle size={20} /> Clinical Findings
              </h3>
              {result.findings?.length > 0 ? (
                <ul className="space-y-2">
                  {result.findings.map((finding: any, i: number) => (
                    <li key={i} className="text-sm p-2 bg-success-bg text-success-text rounded">
                      • {finding}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted italic">No clinical findings extracted.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
