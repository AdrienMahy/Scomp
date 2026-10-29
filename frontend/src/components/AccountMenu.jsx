import { useEffect, useRef, useState } from 'react'
import { ChevronDown, LogOut } from 'lucide-react'

function initials(displayName) {
  return displayName.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?'
}

export default function AccountMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const triggerRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const handlePointerDown = event => {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }
    const handleKeyDown = event => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const displayName = user.display_name || user.username || 'Utilisateur'
  const role = user.is_admin ? 'Administrateur' : [user.tactical_access && 'TacticalData', user.statsport_access && 'STATSport'].filter(Boolean).join(' · ') || 'Compte utilisateur'
  const avatarLabel = `Ouvrir le menu de ${displayName}`

  return <div className="account-menu" ref={containerRef}><button ref={triggerRef} className="account-trigger" type="button" aria-label={avatarLabel} aria-expanded={open} aria-haspopup="menu" aria-controls="account-menu" onClick={() => setOpen(value => !value)}><span className="account-avatar" aria-hidden="true">{initials(displayName)}</span><span className="account-identity"><strong>{displayName}</strong><small>{role}</small></span><ChevronDown className="account-chevron" size={16} aria-hidden="true" /></button>{open && <div className="account-dropdown" id="account-menu" role="menu" aria-label="Menu du compte"><div className="account-dropdown-identity"><span className="account-avatar" aria-hidden="true">{initials(displayName)}</span><div><strong>{displayName}</strong><small>{role}</small></div></div><div className="account-menu-separator" /><button type="button" role="menuitem" onClick={() => { setOpen(false); onLogout() }}><LogOut size={16} aria-hidden="true" /> Déconnexion</button></div>}</div>
}
