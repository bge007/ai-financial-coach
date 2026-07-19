import { useEffect } from "react";
import { createPortal } from "react-dom";

export default function GlassModal({
  open,
  onClose,
  titleId,
  children,
  className = "",
  size = "md",
}) {
  useEffect(() => {
    if (!open) return undefined;

    function onKey(e) {
      if (e.key === "Escape") onClose();
    }

    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="glass-modal-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        className={`glass-modal-card glass-modal-${size} ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
