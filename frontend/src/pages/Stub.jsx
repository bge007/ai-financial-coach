export default function Stub({ label, phase }) {
  return (
    <div className="stub">
      <h2>{label}</h2>
      <p>
        Coming in <strong>Phase {phase}</strong>. This section will light up as
        the build progresses — see <code>docs/ROADMAP.md</code>.
      </p>
    </div>
  );
}
