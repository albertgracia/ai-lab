export function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.28em] text-cyan-300/80">{eyebrow}</p>
        <h2 className="mt-1 text-2xl font-bold tracking-[-0.04em] text-white sm:text-3xl">{title}</h2>
      </div>
      {description && <p className="max-w-xl text-sm leading-6 text-zinc-500">{description}</p>}
    </div>
  );
}
