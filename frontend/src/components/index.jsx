export function Card({ children, title, subtitle }) {
  return (
    <div className="card">
      {title && <h3 className="text-lg font-bold mb-2">{title}</h3>}
      {subtitle && <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">{subtitle}</p>}
      {children}
    </div>
  )
}

export function Button({ children, onClick, variant = 'primary', disabled = false }) {
  const variants = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${variants[variant]} disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {children}
    </button>
  )
}

export function Badge({ children, variant = 'success' }) {
  const variants = {
    success: 'badge-success',
    error: 'badge-error',
    warning: 'badge-warning',
  }
  return <span className={variants[variant]}>{children}</span>
}

export function Select({ label, options, value, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      {label && <label className="text-sm font-semibold">{label}</label>}
      <select
        value={value}
        onChange={onChange}
        className="input-base"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function Loading() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-500 border-t-accent-red"></div>
      <span className="ml-3">Loading...</span>
    </div>
  )
}

export function ErrorAlert({ message }) {
  return (
    <div className="bg-accent-red/20 border border-accent-red text-accent-red-700 dark:text-accent-red px-4 py-3 rounded">
      ❌ {message}
    </div>
  )
}

export function SuccessAlert({ message }) {
  return (
    <div className="bg-primary-500/20 border border-primary-500 text-primary-700 dark:text-primary-400 px-4 py-3 rounded">
      ✅ {message}
    </div>
  )
}
