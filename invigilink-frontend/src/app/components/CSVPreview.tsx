"use client";

type Props = {
  rows: Record<string, string>[];
  title?: string;
};

export default function CSVPreview({ rows, title }: Props) {
  if (!rows.length) return null;
  const cols = Object.keys(rows[0] ?? {});
  return (
    <div className="card">
      {title && <div className="card-header">{title}</div>}
      <div className="card-body">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {rows.slice(0, 200).map((r, i) => (
                <tr key={i}>
                  {cols.map((c) => <td key={c}>{r[c]}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-[var(--subtext)]">
          Showing up to 200 rows for preview.
        </p>
      </div>
    </div>
  );
}
