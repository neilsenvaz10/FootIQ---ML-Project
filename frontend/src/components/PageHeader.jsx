export default function PageHeader({ title, children }) {
  return (
    <div className="mb-5 pt-1">
      <h1 className="text-[1.75rem] font-extrabold leading-tight tracking-tight sm:text-3xl">{title}</h1>
      {children && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-mute">{children}</p>}
    </div>
  );
}
