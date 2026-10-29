import Icon from "./Icon.jsx";

export function BrandMark({ className = "h-9 w-9" }) {
  return (
    <span aria-hidden="true" className={`grid shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary-hi to-primary-lo text-on-primary shadow-glow ${className}`}>
      <Icon name="ball" className="h-[58%] w-[58%]" />
    </span>
  );
}

export function Wordmark({ className = "text-xl" }) {
  return (
    <span className={`font-extrabold tracking-tight ${className}`}>
      Foot<span className="text-accent">IQ</span>
    </span>
  );
}
