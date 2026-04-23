type Props = {
  total: number;
  applied: number;
  companySite: number;
  directApply: number;
};

export function Metrics({ total, applied, companySite, directApply }: Props) {
  const items = [
    { label: "Jobs captured", value: total },
    { label: "Applied yes", value: applied },
    { label: "Apply on company site", value: companySite },
    { label: "Direct apply jobs", value: directApply },
  ];

  return (
    <section className="metrics">
      {items.map((item) => (
        <article className="metric-card" key={item.label}>
          <div className="value">{item.value}</div>
          <div className="label">{item.label}</div>
        </article>
      ))}
    </section>
  );
}
