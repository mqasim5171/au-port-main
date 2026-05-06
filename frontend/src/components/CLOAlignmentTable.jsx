import React from "react";

export default function CLOAlignmentTable({ data }) {
  if (!data || !data.pairs) return null;

  return (
    <div className="card">
      <h3>Explainable CLO Alignment</h3>

      <table className="table">
        <thead>
          <tr>
            <th>CLO</th>
            <th>Best Assessment</th>
            <th>Similarity</th>
          </tr>
        </thead>
        <tbody>
          {data.pairs.map((p, i) => (
            <tr key={i}>
              <td>{p.clo}</td>
              <td>{p.assessment}</td>
              <td>
                <span
                  style={{
                    color:
                      p.similarity >= 0.75
                        ? "green"
                        : p.similarity >= 0.6
                        ? "orange"
                        : "red",
                  }}
                >
                  {(p.similarity * 100).toFixed(1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="muted">
        Average Top Similarity: {(data.avg_top * 100).toFixed(1)}%
      </p>
    </div>
  );
}
